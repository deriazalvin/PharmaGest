from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from config.view_utils import audit, paginate
from .forms import FournisseurForm
from .models import Fournisseur


@login_required
@permission_required("fournisseurs.view_fournisseur", raise_exception=True)
def list_fournisseur(request):
    q = request.GET.get("q", "").strip()
    fournisseurs = Fournisseur.objects.order_by("nom")
    if q:
        fournisseurs = fournisseurs.filter(
            Q(nom__icontains=q) | Q(telephone__icontains=q)
        )
    page = paginate(request, fournisseurs)
    rows = [
        (f.nom, f.telephone or "—", f.mail or "—",
         "Actif" if f.status else "Inactif", f.pk)
        for f in page
    ]
    return render(request, "shared/list.html", {
        "title": "Fournisseurs",
        "subtitle": "Partenaires et historique d'approvisionnement",
        "headers": ("Raison sociale", "Téléphone", "E-mail", "Statut", ""),
        "rows": rows,
        "page_obj": page,
        "search": q,
        "create_url": "fournisseurs:ajouter_fournisseur",
        "create_label": "Nouveau fournisseur",
        "detail_url": "fournisseurs:detail_fournisseur",
        "edit_url": "fournisseurs:modifier_fournisseur",
        "delete_url": "fournisseurs:supprimer_fournisseur",
    })


@login_required
@permission_required("fournisseurs.add_fournisseur", raise_exception=True)
def ajouter_fournisseur(request):
    form = FournisseurForm(request.POST or None)
    if form.is_valid():
        fournisseur = form.save()
        audit(request, "Création", fournisseur)
        messages.success(request, "Le fournisseur a été ajouté.")
        return redirect("fournisseurs:liste")
    return render(request, "shared/form.html", {
        "title": "Ajouter un fournisseur",
        "form": form,
        "cancel_url": "fournisseurs:liste",
    })


@login_required
@permission_required("fournisseurs.view_fournisseur", raise_exception=True)
def detail_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    return render(request, "fournisseurs/detail.html", {
        "fournisseur": fournisseur,
        "commandes": fournisseur.commandes.order_by("-cree_le")[:30],
    })


@login_required
@permission_required("fournisseurs.change_fournisseur", raise_exception=True)
def modifier_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    form = FournisseurForm(request.POST or None, instance=fournisseur)
    if form.is_valid():
        fournisseur = form.save()
        audit(request, "Modification", fournisseur)
        messages.success(request, "La fiche fournisseur a été mise à jour.")
        return redirect("fournisseurs:liste")
    return render(request, "shared/form.html", {
        "title": "Modifier le fournisseur",
        "form": form,
        "cancel_url": "fournisseurs:liste",
    })


@login_required
@permission_required("fournisseurs.delete_fournisseur", raise_exception=True)
def supprimer_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method == "POST":
        try:
            audit(request, "Suppression", fournisseur)
            fournisseur.delete()
            messages.success(request, "Le fournisseur a été supprimé.")
        except ProtectedError:
            fournisseur.status = False
            fournisseur.save(update_fields=("status",))
            audit(request, "Désactivation", fournisseur, "Historique d'achat conservé.")
            messages.warning(
                request, "Fournisseur désactivé pour préserver l'historique des achats."
            )
        return redirect("fournisseurs:liste")
    return render(request, "shared/confirm_delete.html", {
        "title": "Supprimer le fournisseur",
        "object": fournisseur,
        "cancel_url": "fournisseurs:liste",
    })

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Case, F, IntegerField, Q, Sum, When
from django.db.models.functions import Coalesce
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from config.view_utils import audit, paginate
from categories.models import Categorie
from .models import Medicament
from .forms import MedicamentForm


@login_required
@permission_required("medicaments.view_medicament", raise_exception=True)
def list_medicament(request):
    q = request.GET.get("q", "").strip()
    sort = request.GET.get("tri", "nom")
    allowed_sorts = {"nom", "prix_vente", "date_creation", "categorie__nom"}
    if sort not in allowed_sorts:
        sort = "nom"
    medicaments = (
        Medicament.objects.select_related("categorie")
        .annotate(
            stock_vendable_calc=Coalesce(
                Sum(
                    Case(
                        When(
                            lots__bloque=False,
                            lots__date_peremption__gt=timezone.localdate(),
                            then=F("lots__quantite_disponible"),
                        ),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),
                0,
            )
        )
        .order_by("nom")
    )
    categorie = request.GET.get("categorie")
    if q:
        medicaments = medicaments.filter(
            Q(nom__icontains=q)
            | Q(denomination_generique__icontains=q)
            | Q(code_barre__icontains=q)
        )
    if categorie and categorie.isdigit():
        medicaments = medicaments.filter(categorie_id=categorie)
    medicaments = medicaments.order_by(sort)
    page = paginate(request, medicaments)
    rows = [
        (
            medicament.nom,
            medicament.categorie.nom,
            medicament.forme,
            medicament.stock_vendable_calc,
            f"{medicament.prix_vente:.2f} Ar",
            "Actif" if medicament.status else "Archivé",
            medicament.pk,
        )
        for medicament in page
    ]
    return render(request, "shared/list.html", {
        "title": "Médicaments",
        "subtitle": "Catalogue, prix et disponibilité en temps réel.",
        "headers": ("Médicament", "Catégorie", "Forme", "Stock", "Prix de vente", "Statut", ""),
        "rows": rows,
        "page_obj": page,
        "search": q,
        "categories": Categorie.objects.filter(status=True).order_by("nom"),
        "selected_category": categorie,
        "selected_sort": sort,
        "sort_options": (
            ("nom", "Nom"),
            ("prix_vente", "Prix de vente"),
            ("date_creation", "Date de création"),
            ("categorie__nom", "Catégorie"),
        ),
        "create_url": "medicaments:ajouter_medicament",
        "create_label": "Nouveau médicament",
        "detail_url": "medicaments:detail_medicament",
        "edit_url": "medicaments:modifier_medicament",
        "delete_url": "medicaments:supprimer_medicament",
    })


@login_required
@permission_required("medicaments.add_medicament", raise_exception=True)
def ajouter_medicament(request):
    form = MedicamentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        medicament = form.save()
        audit(request, "Création", medicament)
        messages.success(request, "Le médicament a été ajouté.")
        return redirect("medicaments:liste_medicaments")
    return render(request, "shared/form.html", {
        "title": "Ajouter un médicament",
        "form": form,
        "cancel_url": "medicaments:liste_medicaments",
        "enctype": "multipart/form-data",
    })


@login_required
@permission_required("medicaments.view_medicament", raise_exception=True)
def detail_medicament(request, pk):
    medicament = get_object_or_404(
        Medicament.objects.select_related("categorie"), pk=pk
    )
    return render(request, "medicaments/detail.html", {
        "medicament": medicament,
        "lots": medicament.lots.order_by("date_peremption"),
    })


@login_required
@permission_required("medicaments.change_medicament", raise_exception=True)
def modifier_medicament(request, pk):
    medicament = get_object_or_404(Medicament, pk=pk)
    form = MedicamentForm(
        request.POST or None, request.FILES or None, instance=medicament
    )
    if form.is_valid():
        medicament = form.save()
        audit(request, "Modification", medicament)
        messages.success(request, "Le médicament a été modifié.")
        return redirect("medicaments:liste_medicaments")
    return render(request, "shared/form.html", {
        "title": "Modifier le médicament",
        "form": form,
        "cancel_url": "medicaments:liste_medicaments",
        "enctype": "multipart/form-data",
    })


@login_required
@permission_required("medicaments.delete_medicament", raise_exception=True)
def supprimer_medicament(request, pk):
    medicament = get_object_or_404(Medicament, pk=pk)
    if request.method == "POST":
        try:
            audit(request, "Suppression", medicament)
            medicament.delete()
            messages.success(request, "Le médicament a été supprimé.")
        except ProtectedError:
            medicament.status = False
            medicament.save(update_fields=("status",))
            audit(request, "Archivage", medicament, "Historique conservé.")
            messages.warning(
                request, "Médicament archivé car il est lié à des mouvements ou ventes."
            )
        return redirect("medicaments:liste_medicaments")
    return render(request, "shared/confirm_delete.html", {
        "title": "Supprimer le médicament",
        "object": medicament,
        "cancel_url": "medicaments:liste_medicaments",
    })
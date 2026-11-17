from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from config.view_utils import audit, paginate
from .forms import CategorieForm
from .models import Categorie


@login_required
@permission_required("categories.view_categorie", raise_exception=True)
def list_categorie(request):
    q = request.GET.get("q", "").strip()
    categories = Categorie.objects.order_by("nom")
    if q:
        categories = categories.filter(
            Q(nom__icontains=q) | Q(description__icontains=q)
        )
    page = paginate(request, categories)
    rows = [
        (categorie.nom, categorie.description or "—",
         categorie.medicaments.count(), "Actif" if categorie.status else "Inactif",
         categorie.pk)
        for categorie in page
    ]
    return render(request, "shared/list.html", {
        "title": "Catégories",
        "subtitle": "Classez les médicaments pour retrouver rapidement les produits.",
        "headers": ("Catégorie", "Description", "Médicaments", "Statut", ""),
        "rows": rows,
        "page_obj": page,
        "search": q,
        "create_url": "categories:ajouter",
        "create_label": "Nouvelle catégorie",
        "edit_url": "categories:modifier",
        "delete_url": "categories:supprimer",
    })


@login_required
@permission_required("categories.add_categorie", raise_exception=True)
def ajouter_categorie(request):
    form = CategorieForm(request.POST or None)
    if form.is_valid():
        categorie = form.save()
        audit(request, "Création", categorie)
        messages.success(request, "La catégorie a été créée.")
        return redirect("categories:liste")
    return render(request, "shared/form.html", {
        "title": "Ajouter une catégorie",
        "form": form,
        "cancel_url": "categories:liste",
    })


@login_required
@permission_required("categories.change_categorie", raise_exception=True)
def modifier_categorie(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    form = CategorieForm(request.POST or None, instance=categorie)
    if form.is_valid():
        categorie = form.save()
        audit(request, "Modification", categorie)
        messages.success(request, "La catégorie a été modifiée.")
        return redirect("categories:liste")
    return render(request, "shared/form.html", {
        "title": "Modifier une catégorie",
        "form": form,
        "cancel_url": "categories:liste",
    })


@login_required
@permission_required("categories.delete_categorie", raise_exception=True)
def supprimer_categorie(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == "POST":
        try:
            audit(request, "Suppression", categorie)
            categorie.delete()
            messages.success(request, "La catégorie a été supprimée.")
        except ProtectedError:
            messages.error(request, "Cette catégorie est utilisée par des médicaments.")
        return redirect("categories:liste")
    return render(request, "shared/confirm_delete.html", {
        "title": "Supprimer la catégorie",
        "object": categorie,
        "cancel_url": "categories:liste",
    })

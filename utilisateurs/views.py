from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404, redirect, render

from config.view_utils import audit
from .forms import UtilisateurCreationForm, UtilisateurModificationForm


User = get_user_model()
ROLE_PERMISSIONS = {
    "Pharmacien responsable": {
        "medicaments", "categories", "stock", "ventes", "achats", "fournisseurs", "clients",
    },
    "Gestionnaire de stock": {"medicaments", "categories", "stock", "achats", "fournisseurs"},
    "Caissier": {"ventes", "clients"},
    "Responsable de gestion": {"medicaments", "categories", "stock", "achats", "fournisseurs", "clients", "ventes", "rapports"},
}


def _administrateur(user):
    return user.is_authenticated and user.is_superuser


def _ensure_default_roles():
    for role, app_labels in ROLE_PERMISSIONS.items():
        group, created = Group.objects.get_or_create(name=role)
        if created:
            permissions = Permission.objects.filter(
                content_type__app_label__in=app_labels
            )
            if role not in {"Pharmacien responsable", "Responsable de gestion"}:
                permissions = permissions.exclude(
                    codename__in={
                        "confirm_paiement",
                        "confirm_remboursement",
                        "annuler_vente",
                    }
                )
            group.permissions.set(permissions)


@login_required
@user_passes_test(_administrateur)
def liste_utilisateurs(request):
    _ensure_default_roles()
    users = User.objects.prefetch_related("groups").order_by("username")
    return render(request, "utilisateurs/liste.html", {
        "utilisateurs": users,
    })


@login_required
@user_passes_test(_administrateur)
def ajouter_utilisateur(request):
    _ensure_default_roles()
    form = UtilisateurCreationForm(request.POST or None)
    if form.is_valid():
        utilisateur = form.save()
        audit(request, "Création utilisateur", utilisateur)
        messages.success(request, "Le compte utilisateur a été créé.")
        return redirect("utilisateurs:liste")
    return render(request, "shared/form.html", {
        "title": "Créer un utilisateur",
        "subtitle": "Le mot de passe est stocké via l'authentification Django.",
        "form": form,
        "cancel_url": "utilisateurs:liste",
    })


@login_required
@user_passes_test(_administrateur)
def modifier_utilisateur(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    _ensure_default_roles()
    form = UtilisateurModificationForm(
        request.POST or None,
        instance=utilisateur,
        initial={"groupes": utilisateur.groups.all()},
    )
    if form.is_valid():
        utilisateur = form.save()
        audit(request, "Modification utilisateur", utilisateur)
        messages.success(request, "Le compte utilisateur a été modifié.")
        return redirect("utilisateurs:liste")
    return render(request, "shared/form.html", {
        "title": f"Modifier {utilisateur.username}",
        "form": form,
        "cancel_url": "utilisateurs:liste",
    })


@login_required
@user_passes_test(_administrateur)
def desactiver_utilisateur(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if utilisateur.pk == request.user.pk:
            messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        elif utilisateur.is_superuser:
            messages.error(request, "Un compte superutilisateur ne peut pas être désactivé ici.")
        else:
            utilisateur.is_active = not utilisateur.is_active
            utilisateur.save(update_fields=("is_active",))
            audit(
                request,
                "Activation utilisateur" if utilisateur.is_active else "Désactivation utilisateur",
                utilisateur,
            )
            messages.success(request, "Statut du compte mis à jour.")
    return redirect("utilisateurs:liste")

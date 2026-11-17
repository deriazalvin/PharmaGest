from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from config.view_utils import audit, paginate
from .forms import ClientForm
from .models import Client


@login_required
@permission_required("clients.view_client", raise_exception=True)
def list_client(request):
    q = request.GET.get("q", "").strip()
    clients = Client.objects.order_by("nom")
    if q:
        clients = clients.filter(Q(nom__icontains=q) | Q(telephone__icontains=q))
    page = paginate(request, clients)
    rows = [
        (client.nom, client.telephone or "—", client.email or "—",
         "Actif" if client.status else "Inactif", client.pk)
        for client in page
    ]
    return render(request, "shared/list.html", {
        "title": "Clients",
        "subtitle": "Fiches clients et historique des ventes",
        "headers": ("Nom", "Téléphone", "E-mail", "Statut", ""),
        "rows": rows,
        "page_obj": page,
        "search": q,
        "create_url": "clients:ajouter_client",
        "create_label": "Nouveau client",
        "detail_url": "clients:detail_client",
        "edit_url": "clients:modifier_client",
        "delete_url": "clients:supprimer_client",
        "namespace": "clients",
    })


@login_required
@permission_required("clients.add_client", raise_exception=True)
def ajouter_client(request):
    form = ClientForm(request.POST or None)
    if form.is_valid():
        client = form.save()
        audit(request, "Création", client)
        messages.success(request, "Le client a été ajouté.")
        return redirect("clients:liste")
    return render(request, "shared/form.html", {
        "title": "Ajouter un client",
        "subtitle": "Les coordonnées demandées restent limitées au nécessaire.",
        "form": form,
        "cancel_url": "clients:liste",
    })


@login_required
@permission_required("clients.view_client", raise_exception=True)
def detail_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    return render(request, "clients/detail.html", {
        "client": client,
        "ventes": client.ventes.order_by("-cree_le")[:20],
    })


@login_required
@permission_required("clients.change_client", raise_exception=True)
def modifier_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(request.POST or None, instance=client)
    if form.is_valid():
        client = form.save()
        audit(request, "Modification", client)
        messages.success(request, "La fiche client a été mise à jour.")
        return redirect("clients:liste")
    return render(request, "shared/form.html", {
        "title": "Modifier le client",
        "form": form,
        "cancel_url": "clients:liste",
    })


@login_required
@permission_required("clients.delete_client", raise_exception=True)
def supprimer_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        if client.ventes.exists():
            client.status = False
            client.save(update_fields=("status",))
            audit(request, "Désactivation", client, "Fiche conservée pour l'historique.")
            messages.warning(request, "Client désactivé afin de préserver l'historique.")
        else:
            audit(request, "Suppression", client)
            client.delete()
            messages.success(request, "Le client a été supprimé.")
        return redirect("clients:liste")
    return render(request, "shared/confirm_delete.html", {
        "title": "Supprimer le client",
        "object": client,
        "cancel_url": "clients:liste",
    })

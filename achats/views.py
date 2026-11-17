from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from config.view_utils import audit, paginate
from stock.models import LotStock, MouvementStock
from .forms import CommandeAchatForm, LigneAchatFormSet, ReceptionAchatForm
from .models import CommandeAchat, LigneReception, ReceptionAchat


@login_required
@permission_required("achats.view_commandeachat", raise_exception=True)
def liste_achats(request):
    q = request.GET.get("q", "").strip()
    commandes = (
        CommandeAchat.objects.select_related("fournisseur")
        .prefetch_related("lignes")
        .order_by("-cree_le")
    )
    if q:
        commandes = commandes.filter(
            Q(reference__icontains=q) | Q(fournisseur__nom__icontains=q)
        )
    page = paginate(request, commandes)
    rows = [
        (c.reference, c.fournisseur.nom, c.cree_le.strftime("%d/%m/%Y"),
         c.get_statut_display(), f"{c.total:,.2f} Ar", c.pk)
        for c in page
    ]
    return render(request, "shared/list.html", {
        "title": "Achats",
        "subtitle": "Commandes, réceptions et historique fournisseur.",
        "headers": ("Référence", "Fournisseur", "Date", "Statut", "Montant", ""),
        "rows": rows,
        "page_obj": page,
        "search": q,
        "create_url": "achats:creer",
        "create_label": "Créer une commande",
        "detail_url": "achats:detail",
    })


@login_required
@permission_required("achats.add_commandeachat", raise_exception=True)
def creer_achat(request):
    form = CommandeAchatForm(request.POST or None)
    formset = LigneAchatFormSet(request.POST or None, instance=None, prefix="lignes")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        if not any(
            line.cleaned_data
            and not line.cleaned_data.get("DELETE")
            and line.cleaned_data.get("medicament")
            for line in formset.forms
        ):
            form.add_error(None, "Ajoutez au moins un médicament à la commande.")
        else:
            with transaction.atomic():
                commande = form.save(commit=False)
                commande.cree_par = request.user
                commande.save()
                formset.instance = commande
                formset.save()
                audit(request, "Création", commande)
                messages.success(
                    request,
                    "La commande est enregistrée en brouillon. Le stock reste inchangé.",
                )
                return redirect("achats:detail", pk=commande.pk)
    return render(request, "achats/form.html", {
        "title": "Créer une commande d'achat",
        "form": form,
        "formset": formset,
        "cancel_url": "achats:liste",
    })


def _render_detail(request, commande, reception_form=None):
    return render(request, "achats/detail.html", {
        "commande": commande,
        "reception_form": reception_form,
    })


@login_required
@permission_required("achats.view_commandeachat", raise_exception=True)
def detail_achat(request, pk):
    commande = get_object_or_404(
        CommandeAchat.objects.select_related("fournisseur", "cree_par"),
        pk=pk,
    )
    reception_form = None
    if commande.statut in (
        CommandeAchat.Statut.COMMANDEE,
        CommandeAchat.Statut.PARTIELLE,
    ):
        reception_form = ReceptionAchatForm(commande)
    return _render_detail(request, commande, reception_form)


@login_required
@permission_required("achats.change_commandeachat", raise_exception=True)
def valider_achat(request, pk):
    if request.method != "POST":
        return redirect("achats:detail", pk=pk)
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if commande.statut != CommandeAchat.Statut.BROUILLON:
        messages.error(request, "Seul un brouillon peut être commandé.")
    elif not commande.lignes.exists():
        messages.error(request, "Impossible de valider une commande vide.")
    else:
        commande.statut = CommandeAchat.Statut.COMMANDEE
        commande.save(update_fields=("statut",))
        audit(request, "Validation de commande", commande)
        messages.success(
            request, "Commande validée. Le stock sera mis à jour à la réception."
        )
    return redirect("achats:detail", pk=pk)


@login_required
@permission_required("achats.add_receptionachat", raise_exception=True)
def receptionner_achat(request, pk):
    if request.method != "POST":
        return redirect("achats:detail", pk=pk)
    try:
        with transaction.atomic():
            commande = get_object_or_404(
                CommandeAchat.objects.select_for_update(), pk=pk
            )
            if commande.statut not in (
                CommandeAchat.Statut.COMMANDEE,
                CommandeAchat.Statut.PARTIELLE,
            ):
                messages.error(request, "Cette commande ne peut pas être réceptionnée.")
                return redirect("achats:detail", pk=pk)
            form = ReceptionAchatForm(commande, request.POST)
            if not form.is_valid():
                return _render_detail(request, commande, form)

            lignes = list(
                commande.lignes.select_for_update().select_related("medicament")
            )
            reception = ReceptionAchat.objects.create(
                commande=commande,
                recue_par=request.user,
            )
            for ligne in lignes:
                quantite = form.cleaned_data.get(f"quantite_{ligne.pk}", 0)
                if not quantite:
                    continue
                if quantite > ligne.quantite_commandee - ligne.quantite_recue:
                    raise ValueError(
                        f"Quantité réceptionnée excessive pour {ligne.medicament}."
                    )
                numero_lot = form.cleaned_data[f"lot_{ligne.pk}"].strip()
                expiration = form.cleaned_data[f"peremption_{ligne.pk}"]
                lot, created = LotStock.objects.get_or_create(
                    medicament=ligne.medicament,
                    numero_lot=numero_lot,
                    defaults={
                        "date_peremption": expiration,
                        "quantite_disponible": 0,
                    },
                )
                if not created and lot.date_peremption != expiration:
                    raise ValueError(
                        "Ce numéro de lot existe déjà avec une autre date de péremption."
                    )
                if lot.bloque or lot.perime:
                    raise ValueError("Le lot est bloqué ou déjà périmé.")
                lot.quantite_disponible += quantite
                lot.save(update_fields=("quantite_disponible",))
                ligne.quantite_recue += quantite
                ligne.save(update_fields=("quantite_recue",))
                LigneReception.objects.create(
                    reception=reception,
                    ligne_achat=ligne,
                    lot=lot,
                    quantite=quantite,
                )
                MouvementStock.objects.create(
                    medicament=ligne.medicament,
                    lot=lot,
                    type=MouvementStock.Type.ENTREE,
                    quantite=quantite,
                    reference=reception.reference,
                    motif=f"Réception de {commande.reference}",
                    auteur=request.user,
                )
            if all(
                ligne.quantite_recue >= ligne.quantite_commandee
                for ligne in commande.lignes.all()
            ):
                commande.statut = CommandeAchat.Statut.RECUE
            else:
                commande.statut = CommandeAchat.Statut.PARTIELLE
            commande.save(update_fields=("statut",))
            audit(request, "Réception", reception, commande.reference)
    except IntegrityError:
        messages.error(request, "La réception n'a pas pu être enregistrée.")
        return redirect("achats:detail", pk=pk)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("achats:detail", pk=pk)
    messages.success(request, "Réception enregistrée et stock mis à jour.")
    return redirect("achats:detail", pk=pk)


@login_required
@permission_required("achats.change_commandeachat", raise_exception=True)
def annuler_achat(request, pk):
    if request.method != "POST":
        return redirect("achats:detail", pk=pk)
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if commande.statut not in (
        CommandeAchat.Statut.BROUILLON,
        CommandeAchat.Statut.COMMANDEE,
    ) or commande.lignes.filter(quantite_recue__gt=0).exists():
        messages.error(request, "Cette commande ne peut pas être annulée.")
    else:
        commande.statut = CommandeAchat.Statut.ANNULEE
        commande.save(update_fields=("statut",))
        audit(request, "Annulation", commande)
        messages.success(request, "Commande annulée.")
    return redirect("achats:detail", pk=pk)

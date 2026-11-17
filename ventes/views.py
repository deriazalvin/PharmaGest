from decimal import Decimal
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from config.view_utils import audit, paginate
from stock.models import LotStock, MouvementStock
from medicaments.models import Medicament
from .forms import (
    AnnulationVenteForm,
    LigneVenteFormSet,
    RetourVenteForm,
    VenteForm,
)
from .models import LigneVente, RetourVente, Vente


@login_required
@permission_required("ventes.view_vente", raise_exception=True)
def liste_ventes(request):
    q = request.GET.get("q", "").strip()
    ventes = (
        Vente.objects.select_related("client", "effectuee_par")
        .prefetch_related("lignes")
        .order_by("-cree_le")
    )
    if q:
        ventes = ventes.filter(
            Q(reference__icontains=q)
            | Q(client__nom__icontains=q)
            | Q(client__telephone__icontains=q)
        )
    page = paginate(request, ventes)
    rows = [
        (
            vente.reference,
            vente.cree_le.strftime("%d/%m/%Y %H:%M"),
            vente.client.nom if vente.client else "Client comptoir",
            f"{vente.total:,.2f} Ar",
            "Annulée" if vente.annulee else (
                "Réglée" if vente.paiement_confirme else "Paiement à vérifier"
            ),
            vente.pk,
        )
        for vente in page
    ]
    return render(request, "shared/list.html", {
        "title": "Ventes",
        "subtitle": "Transactions de caisse, encaissements et retours.",
        "headers": ("Référence", "Date", "Client", "Total", "Paiement", ""),
        "rows": rows,
        "page_obj": page,
        "search": q,
        "create_url": "ventes:nouvelle",
        "create_label": "Nouvelle vente",
        "detail_url": "ventes:detail",
    })


def _render_caisse(request, vente_form=None, lignes_formset=None):
    return render(request, "ventes/caisse.html", {
        "vente_form": vente_form or VenteForm(initial={"cle_idempotence": str(uuid4())}),
        "lignes_formset": lignes_formset or LigneVenteFormSet(prefix="lignes"),
        "catalogue": [
            {"id": item.pk, "prix": str(item.prix_vente)}
            for item in Medicament.objects.filter(status=True)
        ],
    })


@login_required
@permission_required("ventes.add_vente", raise_exception=True)
def nouvelle_vente(request):
    vente_form = VenteForm(
        request.POST or None,
        initial={"cle_idempotence": str(uuid4())},
    )
    lignes_formset = LigneVenteFormSet(
        request.POST or None,
        prefix="lignes",
    )
    if request.method == "POST":
        try:
            posted_token = UUID(request.POST.get("cle_idempotence", ""))
        except ValueError:
            posted_token = None
        if posted_token:
            existing = Vente.objects.filter(cle_idempotence=posted_token).first()
            if existing:
                messages.info(request, "Cette vente avait déjà été enregistrée.")
                return redirect("ventes:detail", pk=existing.pk)

        if vente_form.is_valid() and lignes_formset.is_valid():
            lines = [
                form.cleaned_data
                for form in lignes_formset.forms
                if form.cleaned_data and not form.cleaned_data.get("DELETE")
            ]
            if not lines:
                messages.error(request, "Ajoutez au moins un médicament au panier.")
                return _render_caisse(request, vente_form, lignes_formset)
            try:
                with transaction.atomic():
                    vente = Vente.objects.create(
                        client=vente_form.cleaned_data["client"],
                        effectuee_par=request.user,
                        mode_paiement=vente_form.cleaned_data["mode_paiement"],
                        paiement_confirme=(
                            vente_form.cleaned_data["mode_paiement"]
                            != Vente.ModePaiement.MOBILE
                        ),
                        cle_idempotence=vente_form.cleaned_data["cle_idempotence"],
                    )
                    for line in lines:
                        medicament = line["medicament"]
                        quantite_restante = line["quantite"]
                        if not medicament.status or medicament.prix_vente <= Decimal("0"):
                            raise ValueError(
                                f"{medicament} n'est pas actif ou son prix est invalide."
                            )
                        lots = list(
                            medicament.lots.select_for_update()
                            .filter(
                                bloque=False,
                                date_peremption__gt=timezone.localdate(),
                                quantite_disponible__gt=0,
                            )
                            .order_by("date_peremption", "pk")
                        )
                        disponible = sum(lot.quantite_disponible for lot in lots)
                        if disponible < quantite_restante:
                            raise ValueError(
                                f"Stock disponible insuffisant pour {medicament} "
                                f"({disponible} disponible)."
                            )
                        for lot in lots:
                            sortie = min(lot.quantite_disponible, quantite_restante)
                            if not sortie:
                                continue
                            lot.quantite_disponible -= sortie
                            lot.save(update_fields=("quantite_disponible",))
                            LigneVente.objects.create(
                                vente=vente,
                                medicament=medicament,
                                lot=lot,
                                quantite=sortie,
                                prix_unitaire=medicament.prix_vente,
                            )
                            MouvementStock.objects.create(
                                medicament=medicament,
                                lot=lot,
                                type=MouvementStock.Type.SORTIE,
                                quantite=sortie,
                                reference=vente.reference,
                                motif="Vente caisse FEFO",
                                auteur=request.user,
                            )
                            quantite_restante -= sortie
                    audit(request, "Vente", vente)
            except IntegrityError:
                existing = Vente.objects.filter(
                    cle_idempotence=vente_form.cleaned_data["cle_idempotence"]
                ).first()
                if not existing:
                    raise
                messages.info(request, "Cette vente a déjà été enregistrée.")
                return redirect("ventes:detail", pk=existing.pk)
            except ValueError as error:
                messages.error(request, str(error))
                return _render_caisse(request, vente_form, lignes_formset)

            if not vente.paiement_confirme:
                messages.warning(
                    request,
                    "Vente enregistrée. Le paiement mobile reste à vérifier avant confirmation.",
                )
            else:
                messages.success(request, "Vente enregistrée et stock mis à jour.")
            return redirect("ventes:detail", pk=vente.pk)
    return _render_caisse(request, vente_form, lignes_formset)


@login_required
@permission_required("ventes.view_vente", raise_exception=True)
def detail_vente(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related("client", "effectuee_par"), pk=pk
    )
    return render(request, "ventes/detail.html", {
        "vente": vente,
        "lignes": vente.lignes.select_related("medicament", "lot").all(),
        "retours": RetourVente.objects.filter(
            ligne_vente__vente=vente
        ).select_related("effectue_par"),
        "annulation_form": AnnulationVenteForm(),
    })


@login_required
@permission_required("ventes.add_retourvente", raise_exception=True)
def enregistrer_retour(request, pk, ligne_pk):
    ligne = get_object_or_404(
        LigneVente.objects.select_related("vente", "lot", "medicament"),
        pk=ligne_pk,
        vente_id=pk,
    )
    form = RetourVenteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        deja_retourne = ligne.retours.aggregate(total=Sum("quantite"))["total"] or 0
        if ligne.vente.annulee:
            form.add_error(None, "Une vente annulée ne peut plus recevoir de retours.")
        elif form.cleaned_data["quantite"] + deja_retourne > ligne.quantite:
            form.add_error("quantite", "La quantité dépasse le reste retournable.")
        elif (
            form.cleaned_data["remettre_en_stock"]
            and (ligne.lot.perime or ligne.lot.bloque or not ligne.medicament.status)
        ):
            form.add_error(
                "remettre_en_stock",
                "Ce produit ne peut pas être remis en stock (périmé, bloqué ou archivé).",
            )
        else:
            with transaction.atomic():
                lot = type(ligne.lot).objects.select_for_update().get(pk=ligne.lot_id)
                retour = RetourVente.objects.create(
                    ligne_vente=ligne,
                    quantite=form.cleaned_data["quantite"],
                    motif=form.cleaned_data["motif"],
                    remettre_en_stock=form.cleaned_data["remettre_en_stock"],
                    montant_remboursement=(
                        form.cleaned_data["quantite"] * ligne.prix_unitaire
                    ),
                    effectue_par=request.user,
                )
                if retour.remettre_en_stock:
                    lot.quantite_disponible += retour.quantite
                    lot.save(update_fields=("quantite_disponible",))
                    MouvementStock.objects.create(
                        medicament=ligne.medicament,
                        lot=lot,
                        type=MouvementStock.Type.RETOUR,
                        quantite=retour.quantite,
                        reference=ligne.vente.reference,
                        motif=f"Retour de vente — {retour.motif}",
                        auteur=request.user,
                    )
                audit(request, "Retour de vente", retour, ligne.vente.reference)
                messages.success(request, "Le retour a été enregistré avec sa traçabilité.")
                return redirect("ventes:detail", pk=pk)
    return render(request, "ventes/retour.html", {
        "vente": ligne.vente,
        "ligne": ligne,
        "form": form,
    })


@login_required
@permission_required("ventes.confirm_paiement", raise_exception=True)
def confirmer_paiement(request, pk):
    if request.method != "POST":
        return redirect("ventes:detail", pk=pk)
    vente = get_object_or_404(Vente, pk=pk)
    if vente.annulee:
        messages.error(request, "Une vente annulée ne peut pas être encaissée.")
    elif vente.mode_paiement != Vente.ModePaiement.MOBILE:
        messages.error(request, "Seul un paiement mobile doit être vérifié ici.")
    elif not vente.paiement_confirme:
        vente.paiement_confirme = True
        vente.save(update_fields=("paiement_confirme",))
        audit(request, "Confirmation paiement", vente)
        messages.success(request, "Paiement marqué comme vérifié.")
    return redirect("ventes:detail", pk=pk)


@login_required
@permission_required("ventes.confirm_remboursement", raise_exception=True)
def confirmer_remboursement(request, retour_pk):
    if request.method != "POST":
        return redirect("ventes:liste")
    retour = get_object_or_404(
        RetourVente.objects.select_related("ligne_vente__vente"), pk=retour_pk
    )
    if not retour.remboursement_confirme:
        retour.remboursement_confirme = True
        retour.save(update_fields=("remboursement_confirme",))
        audit(request, "Remboursement confirmé", retour)
        messages.success(
            request,
            f"Remboursement de {retour.montant_remboursement:,.2f} Ar confirmé.",
        )
    return redirect("ventes:detail", pk=retour.ligne_vente.vente_id)


@login_required
@permission_required("ventes.annuler_vente", raise_exception=True)
def annuler_vente(request, pk):
    if request.method != "POST":
        return redirect("ventes:detail", pk=pk)
    form = AnnulationVenteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Le motif d'annulation est obligatoire.")
        return redirect("ventes:detail", pk=pk)
    with transaction.atomic():
        vente = get_object_or_404(
            Vente.objects.select_for_update(), pk=pk
        )
        if vente.annulee:
            messages.info(request, "Cette vente est déjà annulée.")
            return redirect("ventes:detail", pk=pk)
        if RetourVente.objects.filter(ligne_vente__vente=vente).exists():
            messages.error(
                request,
                "Une vente avec des retours enregistrés ne peut pas être annulée.",
            )
            return redirect("ventes:detail", pk=pk)
        lignes = list(
            vente.lignes.select_related("medicament").order_by("lot_id")
        )
        lots = {}
        if lignes:
            lots = {
                lot.pk: lot
                for lot in LotStock.objects.select_for_update().filter(
                    pk__in={ligne.lot_id for ligne in lignes}
                )
            }
        for ligne in lignes:
            lot = lots[ligne.lot_id]
            lot.quantite_disponible += ligne.quantite
            lot.save(update_fields=("quantite_disponible",))
            MouvementStock.objects.create(
                medicament=ligne.medicament,
                lot=lot,
                type=MouvementStock.Type.RETOUR,
                quantite=ligne.quantite,
                reference=vente.reference,
                motif=f"Annulation — {form.cleaned_data['motif']}",
                auteur=request.user,
            )
        vente.annulee = True
        vente.annulee_le = timezone.now()
        vente.annulee_par = request.user
        vente.motif_annulation = form.cleaned_data["motif"]
        vente.save(
            update_fields=("annulee", "annulee_le", "annulee_par", "motif_annulation")
        )
        audit(request, "Annulation de vente", vente, form.cleaned_data["motif"])
    messages.success(request, "Vente annulée et stock réintégré avec traçabilité.")
    return redirect("ventes:detail", pk=pk)

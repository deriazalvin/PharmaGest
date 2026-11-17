from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from config.view_utils import audit, paginate
from .forms import AjustementStockForm, LotStockForm
from .models import LotStock, MouvementStock


@login_required
@permission_required("stock.view_lotstock", raise_exception=True)
def liste_stock(request):
    q = request.GET.get("q", "").strip()
    lots = LotStock.objects.select_related("medicament").order_by(
        "date_peremption", "medicament__nom"
    )
    if q:
        lots = lots.filter(
            Q(medicament__nom__icontains=q) | Q(numero_lot__icontains=q)
        )
    page = paginate(request, lots)
    rows = [
        (
            lot.medicament.nom,
            lot.numero_lot,
            lot.date_peremption.strftime("%d/%m/%Y"),
            lot.quantite_disponible,
            "Bloqué" if lot.bloque else (
                "Périmé" if lot.perime else "Disponible"
            ),
            lot.pk,
        )
        for lot in page
    ]
    mouvements = MouvementStock.objects.select_related(
        "medicament", "lot", "auteur"
    )[:20]
    return render(request, "stock/stock.html", {
        "title": "Stocks & lots",
        "subtitle": "Lots FEFO, péremptions et mouvements de stock.",
        "headers": ("Médicament", "N° de lot", "Péremption", "Quantité", "État", ""),
        "rows": rows,
        "page_obj": page,
        "search": q,
        "create_url": "stock:ajuster",
        "create_label": "Ajuster le stock",
        "lot_url": "stock:ajouter_lot",
        "toggle_url": "stock:bloquer",
        "mouvements": mouvements,
        "today": timezone.localdate(),
    })


@login_required
@permission_required("stock.add_lotstock", raise_exception=True)
def ajouter_lot(request):
    form = LotStockForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            lot = form.save()
            MouvementStock.objects.create(
                medicament=lot.medicament,
                lot=lot,
                type=MouvementStock.Type.ENTREE,
                quantite=lot.quantite_disponible,
                reference=f"LOT-{lot.pk}",
                motif="Stock initial",
                auteur=request.user,
            )
            audit(request, "Création de lot", lot, "Stock initial")
            messages.success(request, "Le lot et son stock initial ont été créés.")
            return redirect("stock:liste")
    return render(request, "shared/form.html", {
        "title": "Nouveau lot",
        "subtitle": "Créez un lot et enregistrez son stock initial.",
        "form": form,
        "cancel_url": "stock:liste",
    })


@login_required
@permission_required("stock.add_mouvementstock", raise_exception=True)
def ajuster_stock(request):
    form = AjustementStockForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            lot = LotStock.objects.select_for_update().get(
                pk=form.cleaned_data["lot"].pk
            )
            variation = form.cleaned_data["variation"]
            if lot.bloque:
                form.add_error("lot", "Un lot bloqué ne peut pas être ajusté.")
            elif lot.quantite_disponible + variation < 0:
                form.add_error(
                    "variation", "L'ajustement ne peut pas rendre le stock négatif."
                )
            else:
                lot.quantite_disponible += variation
                lot.save(update_fields=("quantite_disponible",))
                mouvement = MouvementStock.objects.create(
                    medicament=lot.medicament,
                    lot=lot,
                    type=MouvementStock.Type.AJUSTEMENT,
                    quantite=abs(variation),
                    reference=f"INV-{timezone.localdate():%Y%m%d}",
                    motif=f"{variation:+d} unité(s) — {form.cleaned_data['motif']}",
                    auteur=request.user,
                )
                audit(request, "Ajustement de stock", mouvement, mouvement.motif)
                messages.success(request, "L'inventaire a été ajusté et journalisé.")
                return redirect("stock:liste")
    return render(request, "shared/form.html", {
        "title": "Ajuster le stock",
        "subtitle": "Chaque correction est datée et attribuée à votre compte.",
        "form": form,
        "cancel_url": "stock:liste",
    })


@login_required
@permission_required("stock.change_lotstock", raise_exception=True)
def inventaire_physique(request):
    lots = list(
        LotStock.objects.filter(bloque=False)
        .select_related("medicament")
        .order_by("medicament__nom", "date_peremption", "numero_lot")
    )
    comptes = {lot.pk: lot.quantite_disponible for lot in lots}
    erreurs = []

    if request.method == "POST":
        for lot in lots:
            brut = request.POST.get(f"lot_{lot.pk}", "").strip()
            try:
                valeur = int(brut)
            except (TypeError, ValueError):
                erreurs.append(
                    f"Quantité comptée invalide pour {lot.medicament.nom} "
                    f"(lot {lot.numero_lot})."
                )
                continue
            if valeur < 0:
                erreurs.append(
                    f"La quantité comptée de {lot.medicament.nom} "
                    f"(lot {lot.numero_lot}) ne peut pas être négative."
                )
                continue
            comptes[lot.pk] = valeur

        if not erreurs:
            reference = f"INV-{timezone.localtime():%Y%m%d-%H%M%S}"
            ecarts = 0
            with transaction.atomic():
                for lot in lots:
                    verrouille = LotStock.objects.select_for_update().get(pk=lot.pk)
                    if verrouille.bloque:
                        continue
                    theorique = verrouille.quantite_disponible
                    compte = comptes[lot.pk]
                    difference = compte - theorique
                    if difference == 0:
                        continue
                    verrouille.quantite_disponible = compte
                    verrouille.save(update_fields=("quantite_disponible",))
                    mouvement = MouvementStock.objects.create(
                        medicament=verrouille.medicament,
                        lot=verrouille,
                        type=MouvementStock.Type.AJUSTEMENT,
                        quantite=abs(difference),
                        reference=reference,
                        motif=(
                            f"Inventaire physique : théorique {theorique}, "
                            f"compté {compte} ({difference:+d})"
                        ),
                        auteur=request.user,
                    )
                    audit(
                        request,
                        "Inventaire physique",
                        mouvement,
                        mouvement.motif,
                    )
                    ecarts += 1
            if ecarts:
                messages.success(
                    request,
                    f"Inventaire enregistré : {ecarts} écart(s) ajusté(s) "
                    f"sous la référence {reference}.",
                )
            else:
                messages.info(
                    request, "Inventaire enregistré : aucun écart constaté."
                )
            return redirect("stock:liste")

    for message in erreurs:
        messages.error(request, message)
    lignes = [{"lot": lot, "compte": comptes[lot.pk]} for lot in lots]
    return render(request, "stock/inventaire.html", {
        "lignes": lignes,
        "total_theorique": sum(lot.quantite_disponible for lot in lots),
    })


@login_required
@permission_required("stock.change_lotstock", raise_exception=True)
def basculer_blocage_lot(request, pk):
    if request.method != "POST":
        return redirect("stock:liste")
    lot = get_object_or_404(
        LotStock.objects.select_related("medicament"), pk=pk
    )
    lot.bloque = not lot.bloque
    lot.save(update_fields=("bloque",))
    audit(
        request,
        "Blocage lot" if lot.bloque else "Déblocage lot",
        lot,
        lot.medicament.nom,
    )
    messages.success(
        request,
        f"Lot {lot.numero_lot} {'bloqué' if lot.bloque else 'débloqué'}.",
    )
    return redirect("stock:liste")

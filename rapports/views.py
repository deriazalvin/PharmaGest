from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib import messages
from django.db.models import (
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    IntegerField,
    Sum,
    When,
)
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from achats.models import CommandeAchat, ReceptionAchat
from medicaments.models import Medicament
from stock.models import LotStock
from ventes.models import LigneVente, Vente


def _peut_consulter_tableau(user):
    return (
        user.is_superuser
        or user.has_perm("ventes.view_vente")
        or user.has_perm("achats.view_commandeachat")
    )


@login_required
@user_passes_test(_peut_consulter_tableau)
def tableau_de_bord(request):
    today = timezone.localdate()
    start_default = today - timedelta(days=6)
    raw_start, raw_end = request.GET.get("debut", ""), request.GET.get("fin", "")
    parsed_start, parsed_end = _read_date(raw_start), _read_date(raw_end)
    if raw_start and parsed_start is None:
        messages.error(request, "La date de début n'est pas valide.")
    if raw_end and parsed_end is None:
        messages.error(request, "La date de fin n'est pas valide.")
    start = parsed_start or start_default
    end = parsed_end or today
    if start > end:
        messages.error(request, "La date de début doit précéder la date de fin.")
        start, end = start_default, today
    sales = Vente.objects.filter(cree_le__date__range=(start, end), annulee=False)
    daily = list(
        sales.annotate(jour=TruncDate("cree_le"))
        .values("jour")
        .annotate(
            total=Sum(
                ExpressionWrapper(
                    F("lignes__quantite") * F("lignes__prix_unitaire"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )
        .order_by("jour")
    )
    peak = max((float(row["total"] or 0) for row in daily), default=0) or 1
    trend = [
        {
            "jour": row["jour"].strftime("%d/%m"),
            "total": row["total"] or Decimal("0.00"),
            "hauteur": f"{max(5, float(row['total'] or 0) / peak * 100):.1f}%",
        }
        for row in daily
    ]
    achats_recus = (
        ReceptionAchat.objects.filter(recue_le__date__range=(start, end))
        .aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("lignes__quantite")
                    * F("lignes__ligne_achat__prix_unitaire"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )["total"]
        or Decimal("0.00")
    )
    low_stock = (
        Medicament.objects.filter(status=True)
        .annotate(
            stock_vendable_calc=Coalesce(
                Sum(
                    Case(
                        When(
                            lots__bloque=False,
                            lots__date_peremption__gt=today,
                            then=F("lots__quantite_disponible"),
                        ),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),
                0,
            )
        )
        .filter(stock_vendable_calc__lte=F("seuil"))
        .order_by("stock_vendable_calc", "nom")
    )
    expiry_deadline = today + timedelta(days=90)
    lots_a_surveille = LotStock.objects.filter(
        quantite_disponible__gt=0,
        date_peremption__lte=expiry_deadline,
    ).select_related("medicament").order_by("date_peremption")
    return render(request, "rapports/rapports.html", {
        "medicaments_actifs": Medicament.objects.filter(status=True).count(),
        "ventes_jour": Vente.objects.filter(
            cree_le__date=today, annulee=False
        ).count(),
        "ca_jour": _sum_sales(
            Vente.objects.filter(cree_le__date=today, annulee=False)
        ),
        "encaisse_jour": _sum_sales(
            Vente.objects.filter(
                cree_le__date=today,
                annulee=False,
                paiement_confirme=True,
            )
        ),
        "stocks_faibles": low_stock[:8],
        "nombre_stocks_faibles": low_stock.count(),
        "lots_a_surveille": lots_a_surveille[:8],
        "nombre_peremptions": lots_a_surveille.count(),
        "meilleures_ventes": (
            LigneVente.objects.filter(
                vente__cree_le__date__range=(start, end),
                vente__annulee=False,
            )
            .values("medicament__nom")
            .annotate(quantite=Sum("quantite"))
            .order_by("-quantite")[:5]
        ),
        "achats_recus_periode": achats_recus,
        "achats_recents": CommandeAchat.objects.select_related("fournisseur").order_by(
            "-cree_le"
        )[:5],
        "ventes_par_jour": trend,
        "debut": start,
        "fin": end,
    })


def _read_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _sum_sales(queryset):
    total = Decimal("0.00")
    sales = queryset.prefetch_related("lignes__retours")
    for sale in sales:
        gross = sum((line.total for line in sale.lignes.all()), Decimal("0.00"))
        refunds = sum(
            (
                retour.montant_remboursement
                for line in sale.lignes.all()
                for retour in line.retours.all()
                if retour.remboursement_confirme
            ),
            Decimal("0.00"),
        )
        total += gross - refunds
    return total


def _pdf_response(title, headers, rows, filename, details=()):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=18 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("PHARMAGEST", styles["Title"]),
        Paragraph(escape(title), styles["Heading2"]),
        Paragraph(
            f"Généré le {timezone.localtime():%d/%m/%Y à %H:%M}",
            styles["Normal"],
        ),
        Spacer(1, 8 * mm),
    ]
    elements.extend(Paragraph(escape(detail), styles["Normal"]) for detail in details)
    elements.extend((Spacer(1, 4 * mm), Table([headers, *rows], repeatRows=1)))
    elements[-1].setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#153f38")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dce8e4")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f7f5")]),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    doc.build(elements)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@permission_required("ventes.view_vente", raise_exception=True)
def rapport_ventes_pdf(request):
    ventes = (
        Vente.objects.filter(annulee=False)
        .select_related("client")
        .prefetch_related("lignes")
    )
    rows = [
        [
            vente.reference,
            timezone.localtime(vente.cree_le).strftime("%d/%m/%Y %H:%M"),
            vente.client.nom if vente.client else "Client comptoir",
            vente.get_mode_paiement_display(),
            "Confirmé" if vente.paiement_confirme else "À vérifier",
            f"{vente.total:,.2f} Ar",
        ]
        for vente in ventes.order_by("-cree_le")[:300]
    ]
    return _pdf_response(
        "Rapport des ventes",
        ("Référence", "Date", "Client", "Paiement", "Statut", "Total"),
        rows,
        "rapport-ventes.pdf",
    )


@login_required
@permission_required("stock.view_lotstock", raise_exception=True)
def rapport_peremptions_pdf(request):
    today = timezone.localdate()
    deadline = today + timedelta(days=90)
    lots = (
        LotStock.objects.select_related("medicament")
        .filter(quantite_disponible__gt=0, date_peremption__lte=deadline)
        .order_by("date_peremption", "medicament__nom")
    )
    rows = []
    for lot in lots[:500]:
        jours = (lot.date_peremption - today).days
        rows.append(
            [
                lot.medicament.nom,
                lot.numero_lot,
                lot.date_peremption.strftime("%d/%m/%Y"),
                str(lot.quantite_disponible),
                "Périmé" if jours <= 0 else f"{jours} j",
                "Bloqué" if lot.bloque else "À écouler",
            ]
        )
    return _pdf_response(
        "Produits proches de la péremption",
        ("Médicament", "Lot", "Péremption", "Quantité", "Délai", "État"),
        rows,
        "peremptions.pdf",
        (
            f"Lots encore en stock dont la péremption intervient avant le "
            f"{deadline:%d/%m/%Y}.",
            "Les lots périmés ou bloqués ne sont jamais proposés à la vente.",
        ),
    )


@login_required
@permission_required("stock.view_lotstock", raise_exception=True)
def rapport_stock_pdf(request):
    lots = LotStock.objects.select_related("medicament").order_by(
        "medicament__nom", "date_peremption"
    )
    rows = [
        [
            lot.medicament.nom,
            lot.numero_lot,
            lot.date_peremption.strftime("%d/%m/%Y"),
            str(lot.quantite_disponible),
            "Bloqué" if lot.bloque else ("Périmé" if lot.perime else "Actif"),
        ]
        for lot in lots[:500]
    ]
    return _pdf_response(
        "État des lots en stock",
        ("Médicament", "Lot", "Péremption", "Quantité", "Statut"),
        rows,
        "rapport-stock.pdf",
    )


@login_required
@permission_required("achats.view_commandeachat", raise_exception=True)
def rapport_achats_pdf(request):
    commandes = CommandeAchat.objects.select_related("fournisseur").prefetch_related(
        "lignes"
    )
    rows = [
        [
            commande.reference,
            timezone.localtime(commande.cree_le).strftime("%d/%m/%Y"),
            commande.fournisseur.nom,
            commande.get_statut_display(),
            f"{commande.total:,.2f} Ar",
        ]
        for commande in commandes.order_by("-cree_le")[:300]
    ]
    return _pdf_response(
        "Rapport des achats",
        ("Référence", "Date", "Fournisseur", "Statut", "Total"),
        rows,
        "rapport-achats.pdf",
    )


@login_required
@permission_required("ventes.view_vente", raise_exception=True)
def recu_vente_pdf(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related("client", "effectuee_par").prefetch_related(
            "lignes__medicament", "lignes__lot"
        ),
        pk=pk,
    )
    rows = [
        [
            line.medicament.nom,
            line.lot.numero_lot,
            str(line.quantite),
            f"{line.prix_unitaire:,.2f} Ar",
            f"{line.total:,.2f} Ar",
        ]
        for line in vente.lignes.all()
    ]
    response = _pdf_response(
        f"Reçu de vente {vente.reference}",
        ("Médicament", "Lot", "Quantité", "Prix unitaire", "Sous-total"),
        rows,
        f"recu-{vente.reference}.pdf",
        (
            f"Client : {vente.client.nom if vente.client else 'Client comptoir'}",
            f"Paiement : {vente.get_mode_paiement_display()} — "
            f"{'confirmé' if vente.paiement_confirme else 'en attente de vérification'}",
            (
                f"Annulée le {timezone.localtime(vente.annulee_le):%d/%m/%Y %H:%M} "
                f"par {vente.annulee_par.get_username()} — {vente.motif_annulation}"
                if vente.annulee and vente.annulee_le and vente.annulee_par
                else "Statut : annulée" if vente.annulee else "Statut : validée"
            ),
            f"Total : {vente.total:,.2f} Ar",
        ),
    )
    return response


@login_required
@permission_required("ventes.view_vente", raise_exception=True)
def facture_vente_pdf(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related("client", "effectuee_par").prefetch_related(
            "lignes__medicament", "lignes__lot"
        ),
        pk=pk,
    )
    rows = [
        [
            line.medicament.nom,
            line.lot.numero_lot,
            str(line.quantite),
            f"{line.prix_unitaire:,.2f} Ar",
            f"{line.total:,.2f} Ar",
        ]
        for line in vente.lignes.all()
    ]
    return _pdf_response(
        f"Facture {vente.reference}",
        ("Médicament", "Lot", "Quantité", "Prix unitaire", "Montant"),
        rows,
        f"facture-{vente.reference}.pdf",
        (
            f"Client : {vente.client.nom if vente.client else 'Client comptoir'}",
            f"Date : {timezone.localtime(vente.cree_le):%d/%m/%Y %H:%M}",
            f"Paiement : {vente.get_mode_paiement_display()} — "
            f"{'confirmé' if vente.paiement_confirme else 'à vérifier'}",
            f"Total : {vente.total:,.2f} Ar",
            "Les prix appliqués sont ceux en vigueur au moment de la vente.",
            "Mentions légales et fiscales à compléter selon la réglementation "
            "applicable à Madagascar.",
        ),
    )


@login_required
@permission_required("achats.view_commandeachat", raise_exception=True)
def bon_commande_pdf(request, pk):
    commande = get_object_or_404(
        CommandeAchat.objects.select_related("fournisseur", "cree_par").prefetch_related(
            "lignes__medicament"
        ),
        pk=pk,
    )
    rows = [
        [
            line.medicament.nom,
            str(line.quantite_commandee),
            f"{line.prix_unitaire:,.2f} Ar",
            f"{line.total:,.2f} Ar",
        ]
        for line in commande.lignes.all()
    ]
    return _pdf_response(
        f"Bon de commande {commande.reference} · {commande.fournisseur.nom}",
        ("Médicament", "Quantité", "Prix unitaire", "Total"),
        rows,
        f"commande-{commande.reference}.pdf",
        (
            f"Fournisseur : {commande.fournisseur.nom}",
            f"Date : {timezone.localtime(commande.cree_le):%d/%m/%Y}",
            f"Statut : {commande.get_statut_display()} — total : {commande.total:,.2f} Ar",
        ),
    )


@login_required
@permission_required("achats.view_receptionachat", raise_exception=True)
def bon_reception_pdf(request, pk, reception_pk):
    reception = get_object_or_404(
        ReceptionAchat.objects.select_related(
            "commande__fournisseur", "recue_par"
        ).prefetch_related("lignes__ligne_achat__medicament", "lignes__lot"),
        pk=reception_pk,
        commande_id=pk,
    )
    rows = [
        [
            line.ligne_achat.medicament.nom,
            line.lot.numero_lot,
            line.lot.date_peremption.strftime("%d/%m/%Y"),
            str(line.quantite),
        ]
        for line in reception.lignes.all()
    ]
    return _pdf_response(
        f"Bon de réception {reception.reference} · {reception.commande.fournisseur.nom}",
        ("Médicament", "Lot", "Péremption", "Quantité reçue"),
        rows,
        f"reception-{reception.reference}.pdf",
        (
            f"Fournisseur : {reception.commande.fournisseur.nom}",
            f"Date de réception : {timezone.localtime(reception.recue_le):%d/%m/%Y %H:%M}",
            f"Réceptionné par : {reception.recue_par.get_username()}",
        ),
    )

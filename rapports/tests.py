from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from categories.models import Categorie
from medicaments.models import Medicament
from rapports.views import coordonnees_pharmacie
from stock.models import LotStock
from ventes.models import LigneVente, Vente


class RapportViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="manager", email="manager@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        category = Categorie.objects.create(nom="Hygiène")
        self.medicament = Medicament.objects.create(
            nom="Antiseptique",
            categorie=category,
            forme="Solution",
            dosage="100 ml",
            prix_achat="50.00",
            prix_vente="75.00",
            seuil=4,
        )
        self.lot = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="HY-001",
            date_peremption=date.today() + timedelta(days=30),
            quantite_disponible=2,
        )
        self.vente = Vente.objects.create(
            effectuee_par=self.user,
            mode_paiement=Vente.ModePaiement.ESPECES,
        )
        LigneVente.objects.create(
            vente=self.vente,
            medicament=self.medicament,
            lot=self.lot,
            quantite=1,
            prix_unitaire="75.00",
        )

    def test_dashboard_uses_live_stock_and_sales_values(self):
        response = self.client.get(reverse("rapports:tableau_de_bord"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vue d'ensemble")
        self.assertEqual(response.context["medicaments_actifs"], 1)
        self.assertEqual(response.context["nombre_stocks_faibles"], 1)
        self.assertEqual(response.context["ca_jour"], 75)
        self.assertEqual(response.context["encaisse_jour"], 75)

    def test_receipt_and_stock_reports_return_pdf_documents(self):
        receipt = self.client.get(reverse("rapports:recu_vente", args=(self.vente.pk,)))
        stock = self.client.get(reverse("rapports:stock_pdf"))
        for response in (receipt, stock):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertTrue(response.content.startswith(b"%PDF"))

    def test_expiry_and_invoice_reports_return_pdf_documents(self):
        expiry = self.client.get(reverse("rapports:peremptions_pdf"))
        invoice = self.client.get(
            reverse("rapports:facture_vente", args=(self.vente.pk,))
        )
        for response in (expiry, invoice):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/pdf")
            self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn(
            f"facture-{self.vente.reference}.pdf", invoice["Content-Disposition"]
        )

    @override_settings(
        PHARMACIE_NOM="Pharmacie du Centre",
        PHARMACIE_ADRESSE="Rue 1",
        PHARMACIE_TELEPHONE="034 00 000 00",
        PHARMACIE_EMAIL="",
        PHARMACIE_NIF="123456789",
        PHARMACIE_STAT="987654321",
    )
    def test_pdf_header_uses_the_configured_pharmacy_identity(self):
        lignes = coordonnees_pharmacie()
        self.assertEqual(lignes[0], "Rue 1 · 034 00 000 00")
        self.assertEqual(
            lignes[1], "NIF : 123456789 · STAT : 987654321"
        )
        invoice = self.client.get(
            reverse("rapports:facture_vente", args=(self.vente.pk,))
        )
        self.assertEqual(invoice.status_code, 200)
        self.assertTrue(invoice.content.startswith(b"%PDF"))

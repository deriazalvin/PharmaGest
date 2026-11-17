from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Categorie
from fournisseurs.models import Fournisseur
from medicaments.models import Medicament
from stock.models import LotStock, MouvementStock
from .models import CommandeAchat


class AchatWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        self.category = Categorie.objects.create(nom="Antalgique")
        self.medicament = Medicament.objects.create(
            nom="Paracétamol",
            description="",
            categorie=self.category,
            forme="Comprimé",
            dosage="500 mg",
            prix_achat="8.00",
            prix_vente="12.50",
            seuil=5,
        )
        self.fournisseur = Fournisseur.objects.create(nom="Grossiste santé")

    def _create_order(self):
        response = self.client.post(
            reverse("achats:creer"),
            {
                "fournisseur": self.fournisseur.pk,
                "lignes-TOTAL_FORMS": "1",
                "lignes-INITIAL_FORMS": "0",
                "lignes-MIN_NUM_FORMS": "0",
                "lignes-MAX_NUM_FORMS": "1000",
                "lignes-0-medicament": self.medicament.pk,
                "lignes-0-quantite_commandee": "20",
                "lignes-0-prix_unitaire": "8.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        return CommandeAchat.objects.get()

    def test_order_does_not_change_stock_before_receipt_and_receipt_is_once(self):
        commande = self._create_order()
        self.assertEqual(LotStock.objects.count(), 0)
        self.client.post(reverse("achats:valider", args=(commande.pk,)))
        line = commande.lignes.get()
        payload = {
            f"quantite_{line.pk}": "20",
            f"lot_{line.pk}": "LOT-2026-A",
            f"peremption_{line.pk}": (date.today() + timedelta(days=365)).isoformat(),
        }

        first = self.client.post(
            reverse("achats:receptionner", args=(commande.pk,)), payload
        )
        self.assertEqual(first.status_code, 302)
        lot = LotStock.objects.get()
        self.assertEqual(lot.quantite_disponible, 20)
        self.assertEqual(MouvementStock.objects.count(), 1)

        replay = self.client.post(
            reverse("achats:receptionner", args=(commande.pk,)), payload
        )
        self.assertEqual(replay.status_code, 302)
        lot.refresh_from_db()
        self.assertEqual(lot.quantite_disponible, 20)
        self.assertEqual(MouvementStock.objects.count(), 1)

    def test_empty_purchase_is_rejected_without_creating_order(self):
        response = self.client.post(
            reverse("achats:creer"),
            {
                "fournisseur": self.fournisseur.pk,
                "lignes-TOTAL_FORMS": "1",
                "lignes-INITIAL_FORMS": "0",
                "lignes-MIN_NUM_FORMS": "0",
                "lignes-MAX_NUM_FORMS": "1000",
                "lignes-0-medicament": "",
                "lignes-0-quantite_commandee": "",
                "lignes-0-prix_unitaire": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CommandeAchat.objects.count(), 0)

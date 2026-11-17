from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Categorie
from medicaments.models import Medicament
from utilisateurs.models import JournalAudit
from .forms import AjustementStockForm
from .models import LotStock, MouvementStock


class LotStockModelTests(TestCase):
    def setUp(self):
        self.medicament = Medicament.objects.create(
            nom="Ibuprofène",
            categorie=Categorie.objects.create(nom="Antalgique"),
            forme="Comprimé",
            dosage="400 mg",
            prix_achat="6.00",
            prix_vente="9.00",
        )

    def test_lot_is_sellable_only_when_not_expired_blocked_or_empty(self):
        today = date.today()
        lot = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="IBU-1",
            date_peremption=today + timedelta(days=30),
            quantite_disponible=3,
        )
        self.assertFalse(lot.perime)
        self.assertTrue(lot.est_vendable)

        lot.date_peremption = today
        self.assertTrue(lot.perime)
        self.assertFalse(lot.est_vendable)

        lot.date_peremption = today + timedelta(days=30)
        lot.bloque = True
        self.assertFalse(lot.est_vendable)

        lot.bloque = False
        lot.quantite_disponible = 0
        self.assertFalse(lot.est_vendable)


class StockViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="stock", email="stock@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        self.medicament = Medicament.objects.create(
            nom="Sérum physiologique",
            categorie=Categorie.objects.create(nom="Soins"),
            forme="Solution",
            dosage="500 ml",
            prix_achat="2.00",
            prix_vente="4.00",
        )
        self.lot = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="SER-001",
            date_peremption=date.today() + timedelta(days=200),
            quantite_disponible=10,
        )

    def test_new_lot_records_its_initial_stock_movement(self):
        response = self.client.post(
            reverse("stock:ajouter_lot"),
            {
                "medicament": self.medicament.pk,
                "numero_lot": "SER-002",
                "date_peremption": (date.today() + timedelta(days=365)).isoformat(),
                "quantite_disponible": "25",
            },
        )
        self.assertEqual(response.status_code, 302)
        lot = LotStock.objects.get(numero_lot="SER-002")
        self.assertEqual(lot.quantite_disponible, 25)
        mouvement = MouvementStock.objects.get(lot=lot)
        self.assertEqual(mouvement.type, MouvementStock.Type.ENTREE)
        self.assertEqual(mouvement.quantite, 25)

    def test_adjustment_is_traced_and_cannot_make_stock_negative(self):
        response = self.client.post(
            reverse("stock:ajuster"),
            {
                "lot": self.lot.pk,
                "variation": "-3",
                "motif": "Casse constatée",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite_disponible, 7)
        mouvement = MouvementStock.objects.get(type=MouvementStock.Type.AJUSTEMENT)
        self.assertEqual(mouvement.quantite, 3)
        self.assertIn("-3", mouvement.motif)
        self.assertEqual(
            JournalAudit.objects.filter(action="Ajustement de stock").count(), 1
        )

        response = self.client.post(
            reverse("stock:ajuster"),
            {"lot": self.lot.pk, "variation": "-50", "motif": "Erreur"},
        )
        self.assertEqual(response.status_code, 200)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite_disponible, 7)
        self.assertEqual(
            MouvementStock.objects.filter(type=MouvementStock.Type.AJUSTEMENT).count(), 1
        )

    def test_blocked_lot_is_excluded_from_adjustment_form(self):
        self.lot.bloque = True
        self.lot.save(update_fields=("bloque",))
        form = AjustementStockForm()
        self.assertNotIn(self.lot, form.fields["lot"].queryset)

    def test_lot_blocking_is_togglable_and_audited(self):
        response = self.client.post(reverse("stock:bloquer", args=(self.lot.pk,)))
        self.assertEqual(response.status_code, 302)
        self.lot.refresh_from_db()
        self.assertTrue(self.lot.bloque)
        self.assertTrue(
            JournalAudit.objects.filter(action="Blocage lot").exists()
        )

        self.client.post(reverse("stock:bloquer", args=(self.lot.pk,)))
        self.lot.refresh_from_db()
        self.assertFalse(self.lot.bloque)

    def test_physical_inventory_page_lists_active_lots(self):
        response = self.client.get(reverse("stock:inventaire"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventaire physique")
        self.assertContains(response, self.lot.numero_lot)

    def test_physical_inventory_adjusts_counted_lots_and_traces_gaps(self):
        response = self.client.post(
            reverse("stock:inventaire"),
            {"lot_%s" % self.lot.pk: "7"},
        )
        self.assertEqual(response.status_code, 302)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite_disponible, 7)
        mouvement = MouvementStock.objects.get(
            type=MouvementStock.Type.AJUSTEMENT
        )
        self.assertEqual(mouvement.quantite, 3)
        self.assertIn("théorique 10", mouvement.motif)
        self.assertIn("compté 7", mouvement.motif)
        self.assertTrue(mouvement.reference.startswith("INV-"))
        self.assertTrue(
            JournalAudit.objects.filter(action="Inventaire physique").exists()
        )

    def test_physical_inventory_without_gap_creates_no_movement(self):
        response = self.client.post(
            reverse("stock:inventaire"),
            {"lot_%s" % self.lot.pk: "10"},
        )
        self.assertEqual(response.status_code, 302)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite_disponible, 10)
        self.assertFalse(
            MouvementStock.objects.filter(
                type=MouvementStock.Type.AJUSTEMENT
            ).exists()
        )

    def test_physical_inventory_rejects_invalid_counts_atomically(self):
        other = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="SER-003",
            date_peremption=date.today() + timedelta(days=300),
            quantite_disponible=4,
        )
        response = self.client.post(
            reverse("stock:inventaire"),
            {
                "lot_%s" % self.lot.pk: "8",
                "lot_%s" % other.pk: "-1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.lot.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.lot.quantite_disponible, 10)
        self.assertEqual(other.quantite_disponible, 4)
        self.assertFalse(
            MouvementStock.objects.filter(
                type=MouvementStock.Type.AJUSTEMENT
            ).exists()
        )

    def test_physical_inventory_ignores_blocked_lots(self):
        self.lot.bloque = True
        self.lot.save(update_fields=("bloque",))
        response = self.client.post(
            reverse("stock:inventaire"),
            {"lot_%s" % self.lot.pk: "0"},
        )
        self.assertEqual(response.status_code, 302)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite_disponible, 10)

    def test_expired_or_blocked_lot_is_flagged_in_the_list(self):
        expired = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="SER-PERIME",
            date_peremption=date.today() - timedelta(days=1),
            quantite_disponible=2,
        )
        response = self.client.get(reverse("stock:liste"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Périmé")
        self.assertContains(response, expired.numero_lot)

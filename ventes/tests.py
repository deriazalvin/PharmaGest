from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Categorie
from medicaments.models import Medicament
from stock.models import LotStock, MouvementStock
from .models import RetourVente, Vente


class VenteWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="caisse", email="caisse@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        category = Categorie.objects.create(nom="Vitamines")
        self.medicament = Medicament.objects.create(
            nom="Vitamine C",
            categorie=category,
            forme="Comprimé",
            dosage="1000 mg",
            prix_achat="4.00",
            prix_vente="10.00",
            seuil=2,
        )
        self.closest_lot = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="LOT-1",
            date_peremption=date.today() + timedelta(days=20),
            quantite_disponible=2,
        )
        self.later_lot = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="LOT-2",
            date_peremption=date.today() + timedelta(days=120),
            quantite_disponible=5,
        )

    def _sell(self, quantity, mode="especes", token=None):
        token = token or uuid4()
        response = self.client.post(
            reverse("ventes:nouvelle"),
            {
                "cle_idempotence": str(token),
                "mode_paiement": mode,
                "client": "",
                "lignes-TOTAL_FORMS": "1",
                "lignes-INITIAL_FORMS": "0",
                "lignes-MIN_NUM_FORMS": "0",
                "lignes-MAX_NUM_FORMS": "1000",
                "lignes-0-medicament": self.medicament.pk,
                "lignes-0-quantite": str(quantity),
            },
        )
        return response, token

    def test_sale_allocates_fefo_and_replayed_submission_does_not_deduct_twice(self):
        response, token = self._sell(4)
        self.assertEqual(response.status_code, 302)
        self.closest_lot.refresh_from_db()
        self.later_lot.refresh_from_db()
        self.assertEqual(self.closest_lot.quantite_disponible, 0)
        self.assertEqual(self.later_lot.quantite_disponible, 3)
        self.assertEqual(
            list(Vente.objects.get().lignes.order_by("lot__date_peremption").values_list(
                "lot_id", "quantite"
            )),
            [(self.closest_lot.pk, 2), (self.later_lot.pk, 2)],
        )

        response, _ = self._sell(4, token=token)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vente.objects.count(), 1)
        self.assertEqual(MouvementStock.objects.count(), 2)
        self.later_lot.refresh_from_db()
        self.assertEqual(self.later_lot.quantite_disponible, 3)

    def test_overselling_and_expired_stock_are_rejected(self):
        response, _ = self._sell(8)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Vente.objects.count(), 0)

        self.closest_lot.quantite_disponible = 0
        self.closest_lot.date_peremption = date.today() - timedelta(days=1)
        self.closest_lot.save()
        self.later_lot.quantite_disponible = 0
        self.later_lot.save()
        response, _ = self._sell(1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Vente.objects.count(), 0)

    def test_mobile_payment_remains_unconfirmed_until_verified(self):
        response, _ = self._sell(1, mode="mobile")
        self.assertEqual(response.status_code, 302)
        vente = Vente.objects.get()
        self.assertFalse(vente.paiement_confirme)
        self.client.post(reverse("ventes:confirmer_paiement", args=(vente.pk,)))
        vente.refresh_from_db()
        self.assertTrue(vente.paiement_confirme)

    def test_return_is_traceable_and_restock_is_recorded_once(self):
        response, _ = self._sell(1)
        vente = Vente.objects.get()
        line = vente.lignes.get()
        response = self.client.post(
            reverse("ventes:retour", args=(vente.pk, line.pk)),
            {
                "quantite": "1",
                "motif": "Produit non ouvert",
                "remettre_en_stock": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.closest_lot.refresh_from_db()
        self.assertEqual(self.closest_lot.quantite_disponible, 2)
        retour = RetourVente.objects.get()
        self.assertEqual(retour.montant_remboursement, 10)
        self.assertFalse(retour.remboursement_confirme)
        self.assertEqual(MouvementStock.objects.filter(type="retour").count(), 1)

        rejected = self.client.post(
            reverse("ventes:retour", args=(vente.pk, line.pk)),
            {
                "quantite": "1",
                "motif": "Retour doublon",
                "remettre_en_stock": "on",
            },
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(RetourVente.objects.count(), 1)

    def test_cancellation_restores_stock_once_and_keeps_transaction_history(self):
        response, _ = self._sell(2)
        self.assertEqual(response.status_code, 302)
        vente = Vente.objects.get()
        self.closest_lot.refresh_from_db()
        self.assertEqual(self.closest_lot.quantite_disponible, 0)

        response = self.client.post(
            reverse("ventes:annuler", args=(vente.pk,)),
            {"motif": "Erreur de caisse"},
        )
        self.assertEqual(response.status_code, 302)
        self.closest_lot.refresh_from_db()
        vente.refresh_from_db()
        self.assertEqual(self.closest_lot.quantite_disponible, 2)
        self.assertTrue(vente.annulee)
        self.assertEqual(vente.motif_annulation, "Erreur de caisse")
        self.assertEqual(Vente.objects.count(), 1)
        self.assertEqual(MouvementStock.objects.filter(type="retour").count(), 1)

        response = self.client.post(
            reverse("ventes:annuler", args=(vente.pk,)),
            {"motif": "Nouvel essai"},
        )
        self.assertEqual(response.status_code, 302)
        self.closest_lot.refresh_from_db()
        self.assertEqual(self.closest_lot.quantite_disponible, 2)
        self.assertEqual(MouvementStock.objects.filter(type="retour").count(), 1)

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from achats.models import CommandeAchat
from medicaments.models import Medicament
from stock.models import LotStock, MouvementStock
from ventes.models import Vente


class DonneesDemoTests(TestCase):
    def test_demo_dataset_is_complete_and_replayable(self):
        call_command("charger_donnees_demo", stdout=StringIO())

        self.assertTrue(get_user_model().objects.filter(username="demo").exists())
        self.assertGreaterEqual(Medicament.objects.count(), 8)
        self.assertGreaterEqual(LotStock.objects.count(), 9)
        self.assertEqual(CommandeAchat.objects.count(), 1)
        self.assertEqual(Vente.objects.count(), 1)

        vente = Vente.objects.get()
        self.assertEqual(vente.lignes.count(), 1)
        self.assertTrue(
            MouvementStock.objects.filter(reference=vente.reference).exists()
        )
        quantites = dict(
            LotStock.objects.values_list("numero_lot", "quantite_disponible")
        )

        call_command("charger_donnees_demo", stdout=StringIO())

        self.assertEqual(Medicament.objects.count(), 8)
        self.assertEqual(CommandeAchat.objects.count(), 1)
        self.assertEqual(Vente.objects.count(), 1)
        self.assertEqual(
            dict(LotStock.objects.values_list("numero_lot", "quantite_disponible")),
            quantites,
        )

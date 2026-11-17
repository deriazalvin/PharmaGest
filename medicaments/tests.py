from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Categorie
from stock.models import LotStock
from .models import Medicament


class MedicamentViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        category = Categorie.objects.create(nom="Soins")
        self.medicament = Medicament.objects.create(
            nom="Crème",
            categorie=category,
            forme="Crème",
            dosage="20 g",
            prix_achat="5.00",
            prix_vente="8.00",
        )

    def test_medicament_with_a_stock_lot_is_archived_not_deleted(self):
        LotStock.objects.create(
            medicament=self.medicament,
            numero_lot="CREME-001",
            date_peremption=date.today() + timedelta(days=100),
            quantite_disponible=4,
        )
        response = self.client.post(
            reverse("medicaments:supprimer_medicament", args=(self.medicament.pk,))
        )
        self.assertEqual(response.status_code, 302)
        self.medicament.refresh_from_db()
        self.assertFalse(self.medicament.status)

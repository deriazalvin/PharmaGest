from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Categorie
from medicaments.models import Medicament


class CategorieViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        self.category = Categorie.objects.create(nom="Antibiotiques")

    def test_used_category_cannot_be_deleted(self):
        Medicament.objects.create(
            nom="Amoxicilline",
            categorie=self.category,
            forme="Gélule",
            dosage="500 mg",
            prix_achat="15.00",
            prix_vente="20.00",
        )
        response = self.client.post(
            reverse("categories:supprimer", args=(self.category.pk,))
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Categorie.objects.filter(pk=self.category.pk).exists())
        self.assertTrue(list(response.wsgi_request._messages)[0].message.startswith(
            "Cette catégorie est utilisée"
        ))

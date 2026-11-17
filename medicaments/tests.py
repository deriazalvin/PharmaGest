import tempfile
from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from categories.models import Categorie
from stock.models import LotStock
from .models import Medicament


def _image_upload(name="photo.png", fmt="PNG", content_type="image/png"):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


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


class MedicamentPhotoValidationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="admin", email="admin@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        self.category = Categorie.objects.create(nom="Soins")
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)

    def _payload(self, photo):
        return {
            "nom": "Gel antiseptique",
            "description": "",
            "categorie": self.category.pk,
            "forme": "Gel",
            "dosage": "50 ml",
            "prix_achat": "5.00",
            "prix_vente": "8.00",
            "seuil": "2",
            "status": "on",
            "photo": photo,
        }

    def test_valid_image_is_accepted(self):
        with self.settings(MEDIA_ROOT=self.media.name):
            response = self.client.post(
                reverse("medicaments:ajouter_medicament"),
                self._payload(_image_upload()),
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Medicament.objects.count(), 1)

    def test_file_whose_content_is_not_an_image_is_rejected(self):
        fake = SimpleUploadedFile(
            "photo.png", b"not an image", content_type="image/png"
        )
        with self.settings(MEDIA_ROOT=self.media.name):
            response = self.client.post(
                reverse("medicaments:ajouter_medicament"), self._payload(fake)
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Medicament.objects.count(), 0)
        self.assertTrue(response.context["form"].errors["photo"])

    def test_valid_but_disallowed_image_type_is_rejected(self):
        bmp = _image_upload(
            name="photo.bmp", fmt="BMP", content_type="image/bmp"
        )
        with override_settings(MEDIA_ROOT=self.media.name):
            response = self.client.post(
                reverse("medicaments:ajouter_medicament"), self._payload(bmp)
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Medicament.objects.count(), 0)
        self.assertIn(
            "Format d'image non autorisé",
            response.context["form"].errors["photo"][0],
        )

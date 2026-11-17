from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ventes.models import Vente
from .models import Client


class ClientViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="caisse", email="caisse@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        self.acheteur = Client.objects.create(
            nom="Rasoanaivo", telephone="0340000001", email="rasoanaivo@example.test"
        )

    def test_client_is_created_and_searchable(self):
        response = self.client.post(
            reverse("clients:ajouter_client"),
            {
                "nom": "Rakoto",
                "telephone": "0340000002",
                "email": "rakoto@example.test",
                "status": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        rakoto = Client.objects.get(nom="Rakoto")
        self.assertTrue(rakoto.status)

        response = self.client.get(reverse("clients:liste"), {"q": "0340000002"})
        self.assertContains(response, "Rakoto")
        self.assertNotContains(response, "Rasoanaivo")
        self.assertContains(response, "0340000002")

    def test_client_detail_lists_their_sales(self):
        vente = Vente.objects.create(
            client=self.acheteur,
            effectuee_par=self.user,
            mode_paiement=Vente.ModePaiement.ESPECES,
        )
        response = self.client.get(
            reverse("clients:detail_client", args=(self.acheteur.pk,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, vente.reference)
        self.assertEqual(list(response.context["ventes"]), [vente])

    def test_client_with_sales_is_deactivated_instead_of_deleted(self):
        Vente.objects.create(
            client=self.acheteur,
            effectuee_par=self.user,
            mode_paiement=Vente.ModePaiement.ESPECES,
        )
        response = self.client.post(
            reverse("clients:supprimer_client", args=(self.acheteur.pk,))
        )
        self.assertEqual(response.status_code, 302)
        self.acheteur.refresh_from_db()
        self.assertFalse(self.acheteur.status)

    def test_client_without_sales_is_deleted(self):
        response = self.client.post(
            reverse("clients:supprimer_client", args=(self.acheteur.pk,))
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Client.objects.filter(pk=self.acheteur.pk).exists())

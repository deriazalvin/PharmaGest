from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from achats.models import CommandeAchat, LigneAchat
from categories.models import Categorie
from medicaments.models import Medicament
from utilisateurs.models import JournalAudit
from .models import Fournisseur


class FournisseurViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(
            username="stock", email="stock@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.user)
        self.fournisseur = Fournisseur.objects.create(
            nom="Central Pharma",
            telephone="0200000001",
            mail="contact@central-pharma.test",
            contact_principal="Mme Andria",
        )

    def test_supplier_is_created_with_its_contact_details(self):
        response = self.client.post(
            reverse("fournisseurs:ajouter_fournisseur"),
            {
                "nom": "Labo Océan",
                "adresse": "Antananarivo",
                "telephone": "0200000002",
                "mail": "contact@labo-ocean.test",
                "num_fiscal": "NIF-123",
                "contact_principal": "M. Rabe",
                "status": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        fournisseur = Fournisseur.objects.get(nom="Labo Océan")
        self.assertEqual(fournisseur.num_fiscal, "NIF-123")
        self.assertTrue(fournisseur.status)
        self.assertTrue(JournalAudit.objects.filter(action="Création").exists())

    def test_suppliers_can_be_searched_by_name_or_phone(self):
        Fournisseur.objects.create(nom="Grossiste Nord", telephone="0330000009")

        by_name = self.client.get(reverse("fournisseurs:liste"), {"q": "Central"})
        self.assertContains(by_name, "Central Pharma")
        self.assertNotContains(by_name, "Grossiste Nord")

        by_phone = self.client.get(reverse("fournisseurs:liste"), {"q": "0330000009"})
        self.assertContains(by_phone, "Grossiste Nord")
        self.assertNotContains(by_phone, "Central Pharma")

    def test_supplier_detail_shows_purchase_history_and_amounts(self):
        medicament = Medicament.objects.create(
            nom="Amoxicilline",
            categorie=Categorie.objects.create(nom="Antibiotiques"),
            forme="Gélule",
            dosage="500 mg",
            prix_achat="8.00",
            prix_vente="12.00",
        )
        commande = CommandeAchat.objects.create(
            fournisseur=self.fournisseur, cree_par=self.user
        )
        LigneAchat.objects.create(
            commande=commande,
            medicament=medicament,
            quantite_commandee=20,
            prix_unitaire="8.00",
        )

        response = self.client.get(
            reverse("fournisseurs:detail_fournisseur", args=(self.fournisseur.pk,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, commande.reference)
        self.assertContains(response, "160,00")

    def test_supplier_with_orders_is_deactivated_instead_of_deleted(self):
        CommandeAchat.objects.create(fournisseur=self.fournisseur, cree_par=self.user)

        response = self.client.post(
            reverse("fournisseurs:supprimer_fournisseur", args=(self.fournisseur.pk,))
        )
        self.assertEqual(response.status_code, 302)
        self.fournisseur.refresh_from_db()
        self.assertFalse(self.fournisseur.status)
        self.assertTrue(Fournisseur.objects.filter(pk=self.fournisseur.pk).exists())

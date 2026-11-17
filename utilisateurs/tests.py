import sqlite3
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .models import JournalAudit


User = get_user_model()


class UtilisateurViewsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@example.test", password="secure-pass-123"
        )
        self.client.force_login(self.admin)

    def test_user_management_is_reserved_to_administrators(self):
        caissier = User.objects.create_user(
            username="caissier", password="secure-pass-123"
        )
        self.client.force_login(caissier)
        response = self.client.get(reverse("utilisateurs:liste"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_administrator_creates_a_hashed_account_with_a_role(self):
        self.client.get(reverse("utilisateurs:liste"))
        group = Group.objects.get(name="Caissier")
        response = self.client.post(
            reverse("utilisateurs:ajouter"),
            {
                "username": "caissier2",
                "first_name": "Nina",
                "last_name": "Rakoto",
                "email": "nina@example.test",
                "password1": "secure-pass-123",
                "password2": "secure-pass-123",
                "groupes": [group.pk],
            },
        )
        self.assertEqual(response.status_code, 302)
        utilisateur = User.objects.get(username="caissier2")
        self.assertTrue(utilisateur.check_password("secure-pass-123"))
        self.assertNotEqual(utilisateur.password, "secure-pass-123")
        self.assertIn(group, utilisateur.groups.all())
        self.assertTrue(
            JournalAudit.objects.filter(action="Création utilisateur").exists()
        )

    def test_default_roles_restrict_sensitive_permissions(self):
        self.client.get(reverse("utilisateurs:liste"))

        caissier = Group.objects.get(name="Caissier")
        pharmacien = Group.objects.get(name="Pharmacien responsable")

        self.assertTrue(caissier.permissions.filter(codename="add_vente").exists())
        self.assertFalse(
            caissier.permissions.filter(codename="add_medicament").exists()
        )
        self.assertFalse(
            caissier.permissions.filter(codename="annuler_vente").exists()
        )
        self.assertTrue(
            pharmacien.permissions.filter(codename="annuler_vente").exists()
        )

    def test_account_can_be_deactivated_but_not_your_own_account(self):
        utilisateur = User.objects.create_user(
            username="pharmacien", password="secure-pass-123"
        )

        response = self.client.post(
            reverse("utilisateurs:desactiver", args=(utilisateur.pk,))
        )
        self.assertEqual(response.status_code, 302)
        utilisateur.refresh_from_db()
        self.assertFalse(utilisateur.is_active)
        self.assertTrue(
            JournalAudit.objects.filter(action="Désactivation utilisateur").exists()
        )

        self.client.post(
            reverse("utilisateurs:desactiver", args=(self.admin.pk,))
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)


class SauvegardeTests(TestCase):
    def test_backup_produces_a_readable_sqlite_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "sauvegarde.sqlite3"
            call_command(
                "sauvegarder_bdd", output=str(target), stdout=StringIO()
            )
            self.assertTrue(target.is_file())
            with sqlite3.connect(target) as copy:
                tables = {
                    row[0]
                    for row in copy.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
            self.assertIn("auth_user", tables)

    def test_restore_requires_a_valid_sqlite_file_and_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalide.sqlite3"
            invalid.write_text("ceci n'est pas une base", encoding="utf-8")
            with self.assertRaisesMessage(CommandError, "base SQLite valide"):
                call_command("restaurer_bdd", str(invalid), stdout=StringIO())

            valid = Path(directory) / "valide.sqlite3"
            with sqlite3.connect(valid) as copy:
                copy.execute("CREATE TABLE exemple (id INTEGER PRIMARY KEY)")
            with self.assertRaisesMessage(CommandError, "--confirm"):
                call_command("restaurer_bdd", str(valid), stdout=StringIO())

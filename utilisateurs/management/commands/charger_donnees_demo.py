from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from achats.models import CommandeAchat, LigneAchat
from categories.models import Categorie
from clients.models import Client
from fournisseurs.models import Fournisseur
from medicaments.models import Medicament
from stock.models import LotStock, MouvementStock
from ventes.models import LigneVente, Vente


CATEGORIES = {
    "Antalgiques": "Douleurs légères à modérées.",
    "Antibiotiques": "Traitements anti-infectieux sur prescription.",
    "Vitamines": "Compléments et vitamines.",
    "Soins": "Pansements, antiseptiques et soins courants.",
}

MEDICAMENTS = (
    ("Paracétamol", "Antalgiques", "Comprimé", "500 mg", "8.00", "12.50", 10),
    ("Ibuprofène", "Antalgiques", "Comprimé", "400 mg", "6.00", "9.50", 8),
    ("Amoxicilline", "Antibiotiques", "Gélule", "500 mg", "15.00", "21.00", 6),
    ("Azithromycine", "Antibiotiques", "Comprimé", "250 mg", "22.00", "30.00", 4),
    ("Vitamine C", "Vitamines", "Comprimé", "1000 mg", "4.00", "7.50", 12),
    ("Vitamine D3", "Vitamines", "Gouttes", "10 000 UI/ml", "12.00", "18.00", 5),
    ("Sérum physiologique", "Soins", "Solution", "500 ml", "2.00", "4.00", 15),
    ("Bétadine", "Soins", "Solution", "125 ml", "9.00", "14.00", 6),
)

LOTS = (
    ("Paracétamol", "PARA-2026-A", 240, 60),
    ("Paracétamol", "PARA-2027-A", 700, 120),
    ("Ibuprofène", "IBU-2026-A", 45, 30),
    ("Amoxicilline", "AMOX-2026-A", 300, 40),
    ("Azithromycine", "AZI-2027-A", 500, 18),
    ("Vitamine C", "VITC-2026-A", 180, 80),
    ("Vitamine D3", "VITD-2027-A", 420, 25),
    ("Sérum physiologique", "SER-2026-A", 60, 50),
    ("Bétadine", "BET-2026-A", 25, 12),
)


class Command(BaseCommand):
    help = "Charge un jeu de données fictives cohérent pour la démonstration."

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.localdate()
        User = get_user_model()
        utilisateur, created = User.objects.get_or_create(
            username="demo",
            defaults={"first_name": "Compte", "last_name": "Démonstration"},
        )
        if created:
            utilisateur.set_unusable_password()
            utilisateur.save(update_fields=("password",))

        categories = {
            nom: Categorie.objects.get_or_create(
                nom=nom, defaults={"description": description}
            )[0]
            for nom, description in CATEGORIES.items()
        }

        fournisseurs = [
            Fournisseur.objects.get_or_create(
                nom="Grossiste Santé Océan",
                defaults={
                    "adresse": "Antananarivo",
                    "telephone": "0200000101",
                    "mail": "contact@ocean-sante.test",
                    "contact_principal": "Mme Rasoa",
                },
            )[0],
            Fournisseur.objects.get_or_create(
                nom="Laboratoire Mada Pharma",
                defaults={
                    "adresse": "Antsirabe",
                    "telephone": "0200000102",
                    "mail": "contact@mada-pharma.test",
                    "contact_principal": "M. Randria",
                },
            )[0],
        ]

        clients = [
            Client.objects.get_or_create(
                nom="Rasoanaivo Hery",
                defaults={"telephone": "0340000101", "email": "hery@example.test"},
            )[0],
            Client.objects.get_or_create(
                nom="Andrianina Voary",
                defaults={"telephone": "0330000102", "email": "voary@example.test"},
            )[0],
        ]

        medicaments = {}
        for nom, categorie, forme, dosage, prix_achat, prix_vente, seuil in MEDICAMENTS:
            medicaments[nom] = Medicament.objects.get_or_create(
                nom=nom,
                defaults={
                    "categorie": categories[categorie],
                    "forme": forme,
                    "dosage": dosage,
                    "prix_achat": Decimal(prix_achat),
                    "prix_vente": Decimal(prix_vente),
                    "seuil": seuil,
                    "status": True,
                },
            )[0]

        for nom, numero_lot, jours, quantite in LOTS:
            lot, created = LotStock.objects.get_or_create(
                medicament=medicaments[nom],
                numero_lot=numero_lot,
                defaults={
                    "date_peremption": today + timedelta(days=jours),
                    "quantite_disponible": quantite,
                },
            )
            if created:
                MouvementStock.objects.create(
                    medicament=lot.medicament,
                    lot=lot,
                    type=MouvementStock.Type.ENTREE,
                    quantite=quantite,
                    reference="DEMO",
                    motif="Stock initial du jeu de démonstration",
                    auteur=utilisateur,
                )

        if not CommandeAchat.objects.exists():
            commande = CommandeAchat.objects.create(
                fournisseur=fournisseurs[0],
                cree_par=utilisateur,
                statut=CommandeAchat.Statut.COMMANDEE,
            )
            for nom, quantite in (
                ("Amoxicilline", 50),
                ("Bétadine", 20),
                ("Vitamine C", 100),
            ):
                medicament = medicaments[nom]
                LigneAchat.objects.create(
                    commande=commande,
                    medicament=medicament,
                    quantite_commandee=quantite,
                    prix_unitaire=medicament.prix_achat,
                )

        if not Vente.objects.exists():
            lot = (
                LotStock.objects.filter(
                    quantite_disponible__gt=2,
                    bloque=False,
                    date_peremption__gt=today,
                )
                .order_by("date_peremption")
                .first()
            )
            if lot:
                vente = Vente.objects.create(
                    client=clients[0],
                    effectuee_par=utilisateur,
                    mode_paiement=Vente.ModePaiement.ESPECES,
                )
                quantite = 2
                LigneVente.objects.create(
                    vente=vente,
                    medicament=lot.medicament,
                    lot=lot,
                    quantite=quantite,
                    prix_unitaire=lot.medicament.prix_vente,
                )
                lot.quantite_disponible -= quantite
                lot.save(update_fields=("quantite_disponible",))
                MouvementStock.objects.create(
                    medicament=lot.medicament,
                    lot=lot,
                    type=MouvementStock.Type.SORTIE,
                    quantite=quantite,
                    reference=vente.reference,
                    motif="Vente de démonstration",
                    auteur=utilisateur,
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Données de démonstration disponibles : "
                f"{len(medicaments)} médicaments, "
                f"{LotStock.objects.count()} lots, "
                f"{CommandeAchat.objects.count()} commande(s), "
                f"{Vente.objects.count()} vente(s)."
            )
        )

from decimal import Decimal
import uuid

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

from config.references import make_reference


class Vente(models.Model):
    class ModePaiement(models.TextChoices):
        ESPECES = "especes", "Espèces"
        MOBILE = "mobile", "Mobile money"
        CARTE = "carte", "Carte"
        AUTRE = "autre", "Autre"

    reference = models.CharField(max_length=30, unique=True, blank=True)
    cle_idempotence = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventes",
    )
    effectuee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ventes",
    )
    mode_paiement = models.CharField(max_length=12, choices=ModePaiement.choices)
    paiement_confirme = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    annulee = models.BooleanField(default=False)
    annulee_le = models.DateTimeField(null=True, blank=True)
    annulee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ventes_annulees",
    )
    motif_annulation = models.CharField(max_length=255, blank=True)

    class Meta:
        permissions = [
            ("confirm_paiement", "Peut confirmer un paiement mobile vérifié"),
            ("annuler_vente", "Peut annuler une vente et remettre le stock"),
        ]
        indexes = [
            models.Index(fields=("cree_le", "annulee")),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = make_reference("VTE")
        super().save(*args, **kwargs)

    @property
    def total(self):
        return sum((ligne.total for ligne in self.lignes.all()), Decimal("0.00"))

    def __str__(self):
        return self.reference or f"Vente #{self.pk}"


class LigneVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.PROTECT, related_name="lignes")
    medicament = models.ForeignKey(
        "medicaments.Medicament", on_delete=models.PROTECT, related_name="lignes_vente"
    )
    lot = models.ForeignKey(
        "stock.LotStock", on_delete=models.PROTECT, related_name="lignes_vente"
    )
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prix_unitaire = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        indexes = [
            models.Index(fields=("vente", "medicament")),
        ]

    @property
    def total(self):
        return self.quantite * self.prix_unitaire


class RetourVente(models.Model):
    ligne_vente = models.ForeignKey(
        LigneVente, on_delete=models.PROTECT, related_name="retours"
    )
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    motif = models.CharField(max_length=255)
    remettre_en_stock = models.BooleanField(default=False)
    montant_remboursement = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    remboursement_confirme = models.BooleanField(default=False)
    effectue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="retours_vente",
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("confirm_remboursement", "Peut confirmer un remboursement exécuté"),
        ]
        indexes = [
            models.Index(fields=("cree_le",)),
        ]


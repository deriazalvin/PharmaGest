from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

from config.references import make_reference


class CommandeAchat(models.Model):
    class Statut(models.TextChoices):
        BROUILLON = "brouillon", "Brouillon"
        COMMANDEE = "commandee", "Commandée"
        PARTIELLE = "partielle", "Partiellement réceptionnée"
        RECUE = "recue", "Entièrement réceptionnée"
        ANNULEE = "annulee", "Annulée"

    reference = models.CharField(max_length=30, unique=True, blank=True)
    fournisseur = models.ForeignKey(
        "fournisseurs.Fournisseur",
        on_delete=models.PROTECT,
        related_name="commandes",
    )
    statut = models.CharField(
        max_length=12, choices=Statut.choices, default=Statut.BROUILLON
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="commandes_achat",
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=("statut", "cree_le")),
        ]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = make_reference("ACH")
        super().save(*args, **kwargs)

    @property
    def total(self):
        return sum((ligne.total for ligne in self.lignes.all()), Decimal("0.00"))

    def __str__(self):
        return self.reference or f"Commande #{self.pk}"


class LigneAchat(models.Model):
    commande = models.ForeignKey(
        CommandeAchat, on_delete=models.CASCADE, related_name="lignes"
    )
    medicament = models.ForeignKey(
        "medicaments.Medicament", on_delete=models.PROTECT, related_name="lignes_achat"
    )
    quantite_commandee = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    quantite_recue = models.PositiveIntegerField(default=0)
    prix_unitaire = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("commande", "medicament"), name="unique_medicament_par_achat"
            ),
            models.CheckConstraint(
                condition=models.Q(quantite_recue__lte=models.F("quantite_commandee")),
                name="quantite_recue_lte_commandee",
            ),
        ]

    @property
    def quantite_restante(self):
        return self.quantite_commandee - self.quantite_recue

    @property
    def total(self):
        return self.quantite_commandee * self.prix_unitaire


class ReceptionAchat(models.Model):
    commande = models.ForeignKey(
        CommandeAchat, on_delete=models.PROTECT, related_name="receptions"
    )
    reference = models.CharField(max_length=30, unique=True, blank=True)
    recue_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="receptions_achat",
    )
    recue_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-recue_le", "-pk")

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = make_reference("REC")
        super().save(*args, **kwargs)


class LigneReception(models.Model):
    reception = models.ForeignKey(
        ReceptionAchat, on_delete=models.CASCADE, related_name="lignes"
    )
    ligne_achat = models.ForeignKey(
        LigneAchat, on_delete=models.PROTECT, related_name="receptions"
    )
    lot = models.ForeignKey(
        "stock.LotStock", on_delete=models.PROTECT, related_name="receptions_achat"
    )
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("reception", "ligne_achat", "lot"),
                name="unique_lot_ligne_reception",
            )
        ]

# Create your models here.

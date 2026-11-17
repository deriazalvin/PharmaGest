from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone


class LotStock(models.Model):
    medicament = models.ForeignKey(
        "medicaments.Medicament", on_delete=models.PROTECT, related_name="lots"
    )
    numero_lot = models.CharField(max_length=80)
    date_peremption = models.DateField()
    quantite_disponible = models.PositiveIntegerField(default=0)
    bloque = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("date_peremption", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=("medicament", "numero_lot"),
                name="unique_numero_lot_par_medicament",
            )
        ]
        indexes = [
            models.Index(fields=("date_peremption", "bloque")),
            models.Index(fields=("medicament", "date_peremption")),
        ]

    def __str__(self):
        return f"{self.medicament} — {self.numero_lot}"

    @property
    def perime(self):
        return self.date_peremption <= timezone.localdate()

    @property
    def est_vendable(self):
        return (
            self.quantite_disponible > 0
            and not self.bloque
            and not self.perime
        )


class MouvementStock(models.Model):
    class Type(models.TextChoices):
        ENTREE = "entree", "Entrée"
        SORTIE = "sortie", "Sortie"
        AJUSTEMENT = "ajustement", "Ajustement"
        RETOUR = "retour", "Retour"

    medicament = models.ForeignKey(
        "medicaments.Medicament", on_delete=models.PROTECT, related_name="mouvements"
    )
    lot = models.ForeignKey(
        LotStock, on_delete=models.PROTECT, related_name="mouvements"
    )
    type = models.CharField(max_length=12, choices=Type.choices)
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    reference = models.CharField(max_length=80, blank=True)
    motif = models.CharField(max_length=255, blank=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="mouvements_stock",
    )
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-cree_le", "-pk")
        indexes = [
            models.Index(fields=("cree_le",)),
            models.Index(fields=("type", "cree_le")),
        ]


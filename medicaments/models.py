from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from categories.models import Categorie


class Medicament(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    denomination_generique = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.PROTECT,
        related_name="medicaments",
    )
    forme = models.CharField(max_length=100)
    dosage = models.CharField(max_length=100)
    laboratoire = models.CharField(max_length=100, blank=True)
    code_barre = models.CharField(max_length=100, unique=True, blank=True, null=True)
    photo = models.ImageField(upload_to='medicaments_photos/', blank=True, null=True)
    prix_achat = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    prix_vente = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    seuil = models.PositiveIntegerField(default=0)
    status = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("nom",)
        indexes = [
            models.Index(fields=("nom",)),
            models.Index(fields=("status",)),
        ]

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if self.code_barre is not None:
            self.code_barre = self.code_barre.strip() or None
        super().save(*args, **kwargs)

    @property
    def stock_total(self):
        return sum(lot.quantite_disponible for lot in self.lots.all())

    @property
    def stock_vendable(self):
        today = timezone.localdate()
        return sum(
            lot.quantite_disponible
            for lot in self.lots.all()
            if not lot.bloque
            and lot.date_peremption > today
            and lot.quantite_disponible > 0
        )

    @property
    def quantite_disponible(self):
        return self.stock_vendable
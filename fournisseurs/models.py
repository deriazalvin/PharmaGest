from django.db import models


class Fournisseur(models.Model):
    id = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=255, blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    mail = models.EmailField(max_length=100, blank=True)
    num_fiscal = models.CharField(max_length=100, blank=True)
    contact_principal = models.CharField(max_length=100, blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        ordering = ("nom",)
        indexes = [
            models.Index(fields=("nom",)),
            models.Index(fields=("status",)),
        ]

    def __str__(self):
        return self.nom

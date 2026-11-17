from django.db import models


class Client(models.Model):
    nom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    status = models.BooleanField(default=True)

    class Meta:
        ordering = ("nom",)
        indexes = [
            models.Index(fields=("nom",)),
            models.Index(fields=("status",)),
        ]

    def __str__(self):
        return self.nom
from django.db import models
from django.conf import settings


class JournalAudit(models.Model):
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="evenements_audit",
    )
    action = models.CharField(max_length=80)
    objet = models.CharField(max_length=100)
    objet_id = models.CharField(max_length=40, blank=True)
    details = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-cree_le", "-pk")
        indexes = [
            models.Index(fields=("cree_le",)),
            models.Index(fields=("objet", "objet_id")),
        ]

    def __str__(self):
        return f"{self.action} — {self.objet} {self.objet_id}"

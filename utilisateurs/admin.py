from django.contrib import admin
from .models import JournalAudit


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ("action", "objet", "objet_id", "auteur", "cree_le")
    list_filter = ("action", "cree_le")
    search_fields = ("objet", "objet_id", "details", "auteur__username")
    readonly_fields = ("auteur", "action", "objet", "objet_id", "details", "cree_le")

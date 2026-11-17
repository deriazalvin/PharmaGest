from django.contrib import admin
from .models import CommandeAchat, LigneAchat, LigneReception, ReceptionAchat


class LigneAchatInline(admin.TabularInline):
    model = LigneAchat
    extra = 0


@admin.register(CommandeAchat)
class CommandeAchatAdmin(admin.ModelAdmin):
    list_display = ("reference", "fournisseur", "statut", "cree_le", "cree_par")
    list_filter = ("statut", "cree_le")
    search_fields = ("reference", "fournisseur__nom")
    inlines = (LigneAchatInline,)
    readonly_fields = ("reference", "cree_le", "cree_par")


admin.site.register((ReceptionAchat, LigneReception))

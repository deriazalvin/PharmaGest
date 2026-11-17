from django.contrib import admin
from .models import LotStock, MouvementStock


@admin.register(LotStock)
class LotStockAdmin(admin.ModelAdmin):
    list_display = ("medicament", "numero_lot", "date_peremption", "quantite_disponible", "bloque")
    list_filter = ("bloque", "date_peremption")
    search_fields = ("medicament__nom", "numero_lot")


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ("medicament", "lot", "type", "quantite", "reference", "auteur", "cree_le")
    list_filter = ("type", "cree_le")
    search_fields = ("medicament__nom", "reference", "motif")
    readonly_fields = ("cree_le",)

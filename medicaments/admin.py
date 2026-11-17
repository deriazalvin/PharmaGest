from django.contrib import admin
from .models import Medicament


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ("nom", "categorie", "forme", "dosage", "prix_vente", "seuil", "status")
    list_filter = ("categorie", "status")
    search_fields = ("nom", "denomination_generique", "code_barre", "laboratoire")

from django.contrib import admin
from .models import Fournisseur


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "mail", "status")
    list_filter = ("status",)
    search_fields = ("nom", "telephone", "num_fiscal")

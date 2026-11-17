from django.contrib import admin
from .models import LigneVente, RetourVente, Vente


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 0
    readonly_fields = ("medicament", "lot", "quantite", "prix_unitaire")


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ("reference", "client", "mode_paiement", "paiement_confirme", "effectuee_par", "cree_le")
    list_filter = ("mode_paiement", "paiement_confirme", "cree_le")
    search_fields = ("reference", "client__nom", "client__telephone")
    inlines = (LigneVenteInline,)
    readonly_fields = (
        "reference", "cle_idempotence", "client", "effectuee_par",
        "mode_paiement", "paiement_confirme", "cree_le", "annulee",
        "annulee_le", "annulee_par", "motif_annulation",
    )


admin.site.register(RetourVente)

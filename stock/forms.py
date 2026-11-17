from django import forms
from django.utils import timezone

from medicaments.models import Medicament
from .models import LotStock


class LotStockForm(forms.ModelForm):
    quantite_disponible = forms.IntegerField(
        min_value=1,
        label="Quantité initiale",
    )

    class Meta:
        model = LotStock
        fields = ("medicament", "numero_lot", "date_peremption", "quantite_disponible")
        labels = {
            "medicament": "Médicament",
            "numero_lot": "Numéro de lot",
            "date_peremption": "Date de péremption",
        }
        widgets = {
            "date_peremption": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medicament"].queryset = Medicament.objects.filter(
            status=True
        ).order_by("nom")

    def clean_date_peremption(self):
        date_peremption = self.cleaned_data["date_peremption"]
        if date_peremption <= timezone.localdate():
            raise forms.ValidationError(
                "La date de péremption doit être postérieure à aujourd'hui."
            )
        return date_peremption


class AjustementStockForm(forms.Form):
    lot = forms.ModelChoiceField(
        queryset=LotStock.objects.select_related("medicament").filter(bloque=False),
        label="Lot",
    )
    variation = forms.IntegerField(label="Variation de quantité (positive ou négative)")
    motif = forms.CharField(max_length=255, label="Motif")

    def clean_variation(self):
        variation = self.cleaned_data["variation"]
        if variation == 0:
            raise forms.ValidationError("La variation doit être différente de zéro.")
        return variation




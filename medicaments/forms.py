from django import forms
from .models import Medicament


class MedicamentForm(forms.ModelForm):
    class Meta:
        model = Medicament
        fields = [
            'nom',
            'denomination_generique',
            'description',
            'categorie',
            'forme',
            'dosage',
            'laboratoire',
            'code_barre',
            'photo',
            'prix_achat',
            'prix_vente',
            'seuil',
            'status',
        ]
        labels = {
            "nom": "Nom commercial",
            "denomination_generique": "Dénomination générique",
            "categorie": "Catégorie",
            "forme": "Forme pharmaceutique",
            "code_barre": "Code-barres",
            "prix_achat": "Prix d'achat",
            "prix_vente": "Prix de vente",
            "seuil": "Seuil d'alerte",
            "status": "Médicament actif",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def clean_code_barre(self):
        code_barre = (self.cleaned_data.get("code_barre") or "").strip()
        if not code_barre:
            return None
        doublons = Medicament.objects.filter(code_barre__iexact=code_barre)
        if self.instance.pk:
            doublons = doublons.exclude(pk=self.instance.pk)
        if doublons.exists():
            raise forms.ValidationError("Ce code-barres est déjà utilisé.")
        return code_barre

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError("La photo ne peut pas dépasser 5 Mo.")
        return photo
from django import forms
from .models import Categorie

class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = [
            'nom',
            'description',
            'status',
        ]
        labels = {"status": "Catégorie active"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
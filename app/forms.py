from django import forms
from .models import UploadedLAS

class UploadLASForm(forms.ModelForm):
    class Meta:
        model = UploadedLAS
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'accept': '.las'})
        }

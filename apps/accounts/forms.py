from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import BusinessProfile

class ExtendedSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. Informative only.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class BusinessProfileForm(forms.ModelForm):
    class Meta:
        model = BusinessProfile
        fields = ['business_name', 'business_type', 'location', 'description']
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'block w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:ring-2 focus:ring-sky-500 focus:border-transparent transition',
                'placeholder': 'e.g. Ali\'s Coffee Shop'
            }),
            'business_type': forms.Select(attrs={
                'class': 'block w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white focus:ring-2 focus:ring-sky-500 focus:border-transparent transition'
            }),
            'location': forms.TextInput(attrs={
                'class': 'block w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:ring-2 focus:ring-sky-500 focus:border-transparent transition',
                'placeholder': 'e.g. New York, USA'
            }),
            'description': forms.Textarea(attrs={
                'class': 'block w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:ring-2 focus:ring-sky-500 focus:border-transparent transition',
                'placeholder': 'Tell us a bit about what you do...',
                'rows': 3
            }),
        }

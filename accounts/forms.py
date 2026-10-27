from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings
from .models import INTEREST_CHOICES, User


class SignupForm(UserCreationForm):
    """
    Point 1 of the MVP: signup with the 21+ block. Town is a free-text
    field — members can be anywhere in South Africa, not just
    Ekurhuleni. clean_age is the real enforcement — it runs
    server-side no matter what the browser sends.
    """

    class Meta:
        model = User
        fields = ["username", "email", "age", "gender", "town", "photo"]
        widgets = {
            "gender": forms.RadioSelect,
            "town": forms.TextInput(attrs={"placeholder": "e.g. Duduza, Polokwane, Durban..."}),
        }

    def clean_age(self):
        age = self.cleaned_data["age"]
        if age < settings.MINIMUM_AGE:
            raise forms.ValidationError(
                f"You must be {settings.MINIMUM_AGE} or older to join Mzansi Link."
            )
        return age

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_approved = False  # every new sign-up waits for admin approval
        if commit:
            user.save()
            if user.photo:
                user.generate_blurred_photo()
                user.save()
        return user


class ProfileEditForm(forms.Form):
    """Plain Form rather than a ModelForm: interests is a checkbox set
    that maps onto a comma-separated CharField, which a ModelForm can't
    bind to directly, so the view does that translation itself."""

    bio = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 300}),
        max_length=300, required=False,
        help_text="A couple of lines about you — shown on your profile.",
    )
    interests = forms.MultipleChoiceField(
        choices=INTEREST_CHOICES, required=False, widget=forms.CheckboxSelectMultiple,
    )
    photo = forms.ImageField(required=False, help_text="Leave blank to keep your current photo.")

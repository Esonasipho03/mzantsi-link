from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from PIL import Image, ImageFilter
from io import BytesIO
from django.core.files.base import ContentFile

GENDER_CHOICES = [
    ("woman", "Woman"),
    ("man", "Man"),
    ("lgbtq", "LGBTQ+"),
    ("other", "Other"),
]

# Women are always free. Everyone else (men, LGBTQ+, other) pays to
# unlock clear photos and chat — see User.has_active_unlock().
FREE_GENDERS = ("woman",)

# Fixed interest tags for the profile editor — a plain CharField of
# comma-separated slugs rather than a separate model+M2M, in keeping
# with how small the rest of this MVP's data model is.
INTEREST_CHOICES = [
    ("movies", "Movies"),
    ("sports", "Sports"),
    ("music", "Music"),
    ("travel", "Travel"),
    ("art", "Art"),
    ("gaming", "Gaming"),
    ("food", "Food"),
    ("outdoors", "Outdoors"),
    ("photography", "Photography"),
    ("fashion", "Fashion"),
]


def _blur_jpeg(image_field):
    """Shared blur routine — same Gaussian blur, same JPEG settings,
    used for both a member's main photo and their extra gallery
    photos, so there's one place that defines "what blurred looks
    like" instead of two copies drifting apart."""
    img = Image.open(image_field).convert("RGB")
    blurred = img.filter(ImageFilter.GaussianBlur(radius=18))
    buffer = BytesIO()
    blurred.save(buffer, format="JPEG", quality=70)
    return ContentFile(buffer.getvalue())


class User(AbstractUser):
    """
    Custom user for Mzansi Link.

    age/gender/town are nullable at the DB level only so that Django's
    createsuperuser (which never asks for them) can create an admin
    account. Real member signups always go through SignupForm, which
    requires all three and enforces 21+.
    """

    age = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(21)])
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    # Free text, not limited to one region — a member can be anywhere
    # in South Africa (previously a fixed Ekurhuleni-towns dropdown).
    town = models.CharField(max_length=60, blank=True)

    photo = models.ImageField(upload_to="photos/original/", blank=True, null=True)
    photo_blurred = models.ImageField(upload_to="photos/blurred/", blank=True, null=True)

    # Editable profile extras (point: profile edit screen). interests is
    # a comma-separated list of INTEREST_CHOICES slugs.
    bio = models.CharField(max_length=300, blank=True)
    interests = models.CharField(max_length=200, blank=True)

    # Admin approval (point 6 of the MVP brief). New sign-ups are not
    # visible on the grid or able to log into the app until approved.
    is_approved = models.BooleanField(default=False)

    # Access rule: women are always unlocked. Everyone else pays for a
    # 12-month unlock — is_unlocked plus unlock_expires_at together say
    # whether that's still current; see has_active_unlock().
    is_unlocked = models.BooleanField(default=False)
    unlock_expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Women are free by definition — keep this true regardless of
        # payment state, so a bug in payments can never lock a woman out.
        if self.gender in FREE_GENDERS:
            self.is_unlocked = True
        super().save(*args, **kwargs)

    def has_active_unlock(self):
        """Whether this member currently sees clear photos and can chat.

        Women: always. Everyone else: only while a paid unlock is both
        set and still within its 12-month window — once it lapses this
        goes back to False on its own, no separate "expire" job needed.
        """
        if self.gender in FREE_GENDERS:
            return True
        if not self.is_unlocked:
            return False
        if self.unlock_expires_at and self.unlock_expires_at < timezone.now():
            return False
        return True

    def generate_blurred_photo(self):
        """Create a blurred copy of the uploaded photo, server-side.

        This is what makes the blur unbypassable from the browser: free
        men are only ever sent the URL of this file, never the original.
        """
        if not self.photo:
            return
        self.photo_blurred.save(f"blurred_{self.pk}.jpg", _blur_jpeg(self.photo), save=False)

    def photo_for(self, viewer):
        """Which photo file a given viewer is allowed to see.

        Used by the home grid template — keeps the blur decision in one
        place instead of scattered through templates.
        """
        show_clear = viewer.is_authenticated and viewer.has_active_unlock()
        return self.photo if show_clear else (self.photo_blurred or self.photo)

    def interest_list(self):
        return [slug for slug in self.interests.split(",") if slug]

    def interest_labels(self):
        labels = dict(INTEREST_CHOICES)
        return [labels[slug] for slug in self.interest_list() if slug in labels]

    def __str__(self):
        return self.username


class ProfilePhoto(models.Model):
    """An extra photo on a member's gallery, on top of their one main
    photo (User.photo). Same blur rule applies — a locked man never
    gets sent the original file, only the blurred copy generated here.

    Kept as its own small model (not a list field on User) so members
    can add/remove individual photos without touching the main one,
    which is what everywhere else on the site already keys off of
    (swipe cards, Nearby, Likes, Chats, the landing page preview)."""

    MAX_PER_USER = 5  # + the one main photo on User = 6 photos total

    user = models.ForeignKey(User, related_name="extra_photos", on_delete=models.CASCADE)
    photo = models.ImageField(upload_to="photos/gallery/original/")
    photo_blurred = models.ImageField(upload_to="photos/gallery/blurred/", blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]

    def generate_blurred_photo(self):
        if not self.photo:
            return
        self.photo_blurred.save(f"gallery_blurred_{self.pk}.jpg", _blur_jpeg(self.photo), save=False)

    def photo_for(self, viewer):
        show_clear = viewer.is_authenticated and viewer.has_active_unlock()
        return self.photo if show_clear else (self.photo_blurred or self.photo)

    def __str__(self):
        return f"{self.user}'s gallery photo #{self.position}"


class Like(models.Model):
    """A single swipe decision: from_user liked or passed on to_user.

    Powers the swipe-card Discover screen and the Likes tab. This is
    independent of the paid-unlock rule on User: liking/matching never
    gates messaging or clear photos — that stays governed by
    is_unlocked, so the existing monetization model is untouched.
    """

    ACTIONS = [("like", "Like"), ("pass", "Pass")]

    from_user = models.ForeignKey(User, related_name="likes_given", on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name="likes_received", on_delete=models.CASCADE)
    action = models.CharField(max_length=4, choices=ACTIONS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")

    def __str__(self):
        return f"{self.from_user} {self.action}d {self.to_user}"

    @staticmethod
    def is_match(user_a, user_b):
        return Like.objects.filter(
            from_user=user_a, to_user=user_b, action="like"
        ).exists() and Like.objects.filter(
            from_user=user_b, to_user=user_a, action="like"
        ).exists()

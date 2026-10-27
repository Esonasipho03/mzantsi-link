"""
Loads sample accounts, gallery photos, and messages for local testing.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --reset

Every demo account uses the password: demo1234
"""
import random
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw

from accounts.models import User, ProfilePhoto, Like
from chat.models import Message

# Real headshots for some demo accounts (accounts/management/seed_photos/<username>.jpg).
# Any username without a file here gets a generated avatar instead.
SEED_PHOTOS_DIR = Path(__file__).resolve().parent.parent / "seed_photos"

DEMO_PASSWORD = "demo1234"


# (username, age, town, approved, unlocked, bio, interests)
WOMEN = [
    ("thando_w", 27, "Duduza", True, True,
     "Coffee, hiking, and terrible puns. Looking for someone to explore the local weekend markets with.",
     ["outdoors", "music", "food"]),
    ("lindiwe_w", 31, "Springs", True, True,
     "Nurse by day, amateur baker by night. Big fan of Sunday lunches with family.",
     ["food", "movies", "fashion"]),
    ("naledi_w", 25, "Tsakane", True, True,
     "Studying graphic design. Always got a sketchbook on me and a playlist on shuffle.",
     ["art", "music", "photography"]),
    ("zanele_w", 29, "Nigel", True, True,
     "Gym in the morning, Netflix at night. Looking for genuine conversation, not games.",
     ["sports", "movies"]),
    ("ayanda_w", 26, "Brakpan", False, True,
     "New to the app — still figuring out my bio! Into travel and good food though.",
     ["travel", "food"]),
    ("palesa_w", 24, "Boksburg", True, True,
     "Primary school teacher who still does the voices when reading aloud. Weekend hikes near Boksburg Lake.",
     ["outdoors", "art", "music"]),
    ("refilwe_w", 33, "Germiston", True, False,
     "Accountant who switches off with pottery classes. Dog mom to a very opinionated beagle.",
     ["art", "food", "travel"]),
    ("buhle_w", 22, "Katlehong", True, True,
     "Final-year law student. Big on true-crime podcasts and Sunday braais with the squad.",
     ["movies", "food", "sports"]),
    # Note: there's no "not-approved AND locked" woman here — women
    # are always-free/always-unlocked by design (has_active_unlock()
    # ignores is_unlocked for them), so a "locked woman" isn't a real
    # state the app can produce. The pending+locked test accounts
    # below are men instead, where that combination is meaningful.
]

MEN = [
    ("sipho_m", 28, "Duduza", True, True,
     "Loves braai weekends and five-a-side on Sundays. Looking for someone who can hang with the crew.",
     ["sports", "food", "music"]),
    ("bongani_m", 30, "Springs", True, False,
     "Mechanic by trade, car guy for life. Also into gaming when I'm not under a bonnet.",
     ["gaming", "travel"]),
    ("themba_m", 33, "Benoni", True, False,
     "Divorced dad of one, teacher. Looking for something real, not a hookup.",
     ["outdoors", "movies"]),
    ("mandla_m", 24, "Kempton Park", True, True,
     "Software dev, gym rat, occasional hiker. Ask me about my fantasy football team.",
     ["gaming", "travel", "sports"]),
    ("kagiso_m", 27, "Boksburg", False, False,
     "Just joined, waiting on approval. Photographer on weekends.",
     ["photography", "art"]),
    ("thabo_m", 29, "Vosloorus", True, True,
     "Electrician, five-a-side regular, terrible at karaoke but does it anyway. Looking for my plus one.",
     ["sports", "music", "movies"]),
    ("lwazi_m", 26, "Edenvale", True, False,
     "Junior architect who still doodles buildings on napkins. Into rock climbing and good coffee.",
     ["art", "outdoors", "food"]),
    ("katlego_m", 31, "Alberton", True, True,
     "Chef at a local restaurant — I will cook for you, just say the word. Dad-joke enthusiast.",
     ["food", "movies", "music"]),
    # Not-yet-approved AND locked — same reasoning as nomsa_w/amahle_w
    # above (kagiso_m is already pending+locked, these add a couple
    # more so that state isn't resting on a single account).
    ("sibusiso_m", 26, "Brakpan", False, False,
     "Just joined, waiting on approval. Into five-a-side and bad action movies.",
     ["sports", "movies"]),
    ("tumelo_m", 30, "Nigel", False, False,
     "New account, still finding my feet here. Weekend braais and car shows are my thing.",
     ["food", "travel"]),
]

# Flat, friendly bust-style avatars for any account without a bundled
# real headshot — distinct palette + hair silhouette per seed so the
# demo roster still reads as individuals, not interchangeable blobs.
AVATAR_PALETTES = [
    {"bg": "#F6D9C6", "skin": "#8D5A3B", "hair": "#241A14", "top": "#C4577B"},
    {"bg": "#E3EFE6", "skin": "#C68A5D", "hair": "#3B2A20", "top": "#3E7C7B"},
    {"bg": "#F4E3C1", "skin": "#A8703F", "hair": "#1C1210", "top": "#5474B8"},
    {"bg": "#EAD7F0", "skin": "#7A4B2E", "hair": "#120D0A", "top": "#7B5CD6"},
    {"bg": "#FBE0E0", "skin": "#C98C5E", "hair": "#2C1E16", "top": "#E2664F"},
    {"bg": "#DCEFF2", "skin": "#915E38", "hair": "#20160F", "top": "#2E8B8B"},
]

HAIR_STYLES = ["afro", "short", "long", "fade"]


def _draw_hair(draw, style, cx, head_top, head_bottom, head_left, head_right, color):
    if style == "afro":
        draw.ellipse([head_left - 22, head_top - 34, head_right + 22, head_top + 60], fill=color)
    elif style == "long":
        draw.ellipse([head_left - 6, head_top - 14, head_right + 6, head_bottom + 70], fill=color)
    elif style == "fade":
        draw.pieslice([head_left - 2, head_top - 18, head_right + 2, head_top + 90], 180, 360, fill=color)
    else:  # short
        draw.pieslice([head_left - 4, head_top - 20, head_right + 4, head_top + 70], 180, 360, fill=color)


def make_avatar_photo(seed_text: str) -> ContentFile:
    """A simple flat-icon style bust avatar: background, head, hair,
    shoulders — enough to tell demo profiles apart at a glance without
    needing real photography."""
    random.seed(seed_text)
    palette = random.choice(AVATAR_PALETTES)
    hair_style = random.choice(HAIR_STYLES)

    w, h = 400, 500
    img = Image.new("RGB", (w, h), palette["bg"])
    draw = ImageDraw.Draw(img)

    cx, cy = w // 2, 210
    head_r = 92
    head_left, head_right = cx - head_r, cx + head_r
    head_top, head_bottom = cy - head_r, cy + head_r

    # Shoulders/top first so the head overlaps it.
    draw.pieslice([cx - 170, h - 230, cx + 170, h + 170], 180, 360, fill=palette["top"])
    # Hair behind the head.
    _draw_hair(draw, hair_style, cx, head_top, head_bottom, head_left, head_right, palette["hair"])
    # Head.
    draw.ellipse([head_left, head_top, head_right, head_bottom], fill=palette["skin"])
    # Hair fringe in front for afro/fade so it still reads over the face edge.
    if hair_style == "afro":
        draw.pieslice([head_left - 22, head_top - 34, head_right + 22, head_top + 44], 180, 360, fill=palette["hair"])

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return ContentFile(buf.getvalue(), name=f"{seed_text}.jpg")


def make_gallery_photo(seed_text: str, index: int) -> ContentFile:
    """A second/third gallery shot for a demo profile — same avatar
    style but a different seed so it's visibly a different image, not
    a duplicate of the main photo."""
    return make_avatar_photo(f"{seed_text}-gallery-{index}")


def make_demo_photo(username: str) -> ContentFile:
    """Use a real seed headshot for this username if one is bundled, else a generated avatar."""
    real_photo = SEED_PHOTOS_DIR / f"{username}.jpg"
    if real_photo.exists():
        return ContentFile(real_photo.read_bytes(), name=f"{username}.jpg")
    return make_avatar_photo(username)


class Command(BaseCommand):
    help = "Load sample Mzansi Link accounts, gallery photos, and chat messages for local testing."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            d1, _ = User.objects.filter(username__endswith="_w").delete()
            d2, _ = User.objects.filter(username__endswith="_m").delete()
            self.stdout.write(f"Removed {d1 + d2} existing demo accounts.")

        created = []

        for username, age, town, approved, unlocked, bio, interests in WOMEN + MEN:
            if User.objects.filter(username=username).exists():
                self.stdout.write(f"Skipping {username} (already exists).")
                continue

            gender = "woman" if username.endswith("_w") else "man"
            user = User(
                username=username, email=f"{username}@example.com",
                age=age, gender=gender, town=town,
                is_approved=approved, is_unlocked=unlocked,
                bio=bio, interests=",".join(interests),
            )
            user.set_password(DEMO_PASSWORD)
            user.photo.save(f"{username}.jpg", make_demo_photo(username), save=False)
            user.save()
            user.generate_blurred_photo()
            user.save()
            created.append(user)

            # A couple of gallery photos per account so the "More
            # photos" feature has real test data too.
            gallery_count = random.Random(username).randint(2, 4)
            for i in range(gallery_count):
                gp = ProfilePhoto(user=user, position=i)
                gp.photo.save(f"{username}_gallery_{i}.jpg", make_gallery_photo(username, i), save=False)
                gp.save()
                gp.generate_blurred_photo()
                gp.save()

            self.stdout.write(f"Created {username} — {gender}, {age}, {town}, "
                               f"approved={approved}, unlocked={user.is_unlocked}, "
                               f"{gallery_count} gallery photos")

        try:
            sipho = User.objects.get(username="sipho_m")
            thando = User.objects.get(username="thando_w")
            if not Message.objects.filter(sender=sipho, recipient=thando).exists():
                Message.objects.create(sender=sipho, recipient=thando, text="Hi! I saw you're also from Duduza.")
                Message.objects.create(sender=thando, recipient=sipho, text="Hey Sipho! Yes, born and raised.")
                Message.objects.create(sender=sipho, recipient=thando, text="Nice. Any good spots for coffee this weekend?")
                self.stdout.write("Created a sample conversation between sipho_m and thando_w.")
        except User.DoesNotExist:
            pass

        try:
            katlego = User.objects.get(username="katlego_m")
            palesa = User.objects.get(username="palesa_w")
            if not Message.objects.filter(sender=katlego, recipient=palesa).exists():
                Message.objects.create(sender=katlego, recipient=palesa, text="Hey! Saw you teach near Boksburg Lake — small world.")
                Message.objects.create(sender=palesa, recipient=katlego, text="Ha, small world! You're the chef, right?")
                Message.objects.create(sender=katlego, recipient=palesa, text="Guilty. I'll cook you something better than my jokes.")
                self.stdout.write("Created a sample conversation between katlego_m and palesa_w.")
        except User.DoesNotExist:
            pass

        # Likes/Matches tabs need something to show too — a handful of
        # mutual matches plus one-way likes, spread across the bigger
        # roster, so every tab and badge has real data to test against.
        like_pairs = [
            # (from_username, to_username, action)
            ("thando_w", "sipho_m", "like"),   # mutual -> match
            ("sipho_m", "thando_w", "like"),
            ("lindiwe_w", "bongani_m", "like"),  # mutual -> match, bongani is the free man
            ("bongani_m", "lindiwe_w", "like"),
            ("palesa_w", "katlego_m", "like"),  # mutual -> match
            ("katlego_m", "palesa_w", "like"),
            ("buhle_w", "thabo_m", "like"),  # mutual -> match
            ("thabo_m", "buhle_w", "like"),
            ("naledi_w", "sipho_m", "like"),   # one-way -> "Liked you" badge on sipho's profile
            ("zanele_w", "mandla_m", "like"),  # one-way
            ("refilwe_w", "lwazi_m", "like"),  # one-way
            ("mandla_m", "themba_m", "pass"),  # a plain pass, for completeness
        ]
        likes_created = 0
        for from_username, to_username, action in like_pairs:
            try:
                from_user = User.objects.get(username=from_username)
                to_user = User.objects.get(username=to_username)
            except User.DoesNotExist:
                continue
            _, was_created = Like.objects.get_or_create(
                from_user=from_user, to_user=to_user, defaults={"action": action}
            )
            if was_created:
                likes_created += 1
        if likes_created:
            self.stdout.write(f"Seeded {likes_created} like/pass records (incl. 4 mutual matches).")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {len(created)} accounts created. Password for all demo accounts: {DEMO_PASSWORD}\n"
            "Every account has a bio, interests, and 2-4 gallery photos. Try logging in as:\n"
            "  sipho_m   — paid man: clear photos, a sample chat with thando_w, a match with thando_w,\n"
            "              and a 'Liked you' badge from naledi_w on his own profile\n"
            "  bongani_m — free man: blurred photos, a match with lindiwe_w (try the unlock prompts)\n"
            "  katlego_m — paid man: a sample chat + match with palesa_w\n"
            "  ayanda_w — not yet approved (but unlocked, since women always are), for the waiting screen\n"
            "  kagiso_m / sibusiso_m / tumelo_m — not yet approved AND locked (no active unlock),\n"
            "              for testing the pending + paywall states together\n"
            "              (there's no 'locked woman' account — women are always unlocked by design)"
        ))

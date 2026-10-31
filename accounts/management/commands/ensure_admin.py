"""
Create (or repair) the site's admin account from environment variables.

Why this exists: Render's free tier has no Shell, so `createsuperuser`
can't be run by hand. This runs as part of the build instead.

Set these in Render -> Environment (never in git):
    ADMIN_USERNAME   e.g. mohale
    ADMIN_PASSWORD   a strong, unique password
    ADMIN_EMAIL      optional

Behaviour, safe to run on every deploy:
  * No ADMIN_USERNAME/ADMIN_PASSWORD set  -> does nothing, build still passes.
  * Account doesn't exist                 -> created as staff + superuser.
  * Account exists                        -> kept as staff + superuser, and its
    password is left alone (so changing it in /admin/ sticks).
  * Locked out? Set ADMIN_RESET_PASSWORD=1 for one deploy to force the
    password back to ADMIN_PASSWORD, then remove that variable again.
"""
import os

from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = "Create or repair the admin account from ADMIN_* environment variables."

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME", "").strip()
        password = os.getenv("ADMIN_PASSWORD", "")
        email = os.getenv("ADMIN_EMAIL", "").strip()
        reset = os.getenv("ADMIN_RESET_PASSWORD", "") == "1"

        if not username or not password:
            self.stdout.write("ensure_admin: ADMIN_USERNAME / ADMIN_PASSWORD not set, skipping.")
            return

        user, created = User.objects.get_or_create(username=username)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if email:
            user.email = email
        if created or reset:
            user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"ensure_admin: created admin '{username}'."))
        elif reset:
            self.stdout.write(self.style.SUCCESS(f"ensure_admin: reset password for '{username}'."))
        else:
            self.stdout.write(f"ensure_admin: admin '{username}' already exists, left as is.")

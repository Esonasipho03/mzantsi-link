"""
Delete the demo accounts created by seed_demo_data, and nothing else.

Matches the EXACT demo usernames (not "anything ending in _m/_w"), so a
real member who happens to pick a similar name is never touched. Their
likes and chat messages are removed with them (cascade). Safe to run on
every deploy; does nothing once they're gone.

    python manage.py remove_demo_data
"""
from django.core.management.base import BaseCommand

from accounts.models import User
from accounts.management.commands.seed_demo_data import MEN, WOMEN


class Command(BaseCommand):
    help = "Remove the seeded demo accounts (exact usernames only)."

    def handle(self, *args, **options):
        usernames = [row[0] for row in WOMEN + MEN]
        users = User.objects.filter(username__in=usernames, is_staff=False)
        # Delete their stored photo files too, so removed demo accounts
        # don't leave orphaned images behind (matters when photos live in
        # the database).
        for user in users:
            for f in [user.photo, user.photo_blurred]:
                if f:
                    f.delete(save=False)
            for extra in user.extra_photos.all():
                for f in [extra.photo, extra.photo_blurred]:
                    if f:
                        f.delete(save=False)
        deleted, _ = users.delete()
        if deleted:
            self.stdout.write(self.style.SUCCESS(f"remove_demo_data: removed demo accounts and related rows ({deleted} objects)."))
        else:
            self.stdout.write("remove_demo_data: no demo accounts found.")

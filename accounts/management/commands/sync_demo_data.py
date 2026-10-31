"""
One switch for demo accounts on the live site, driven by an env var so
it can be flipped in Render's Environment tab without touching git:

    SEED_DEMO_DATA=1   -> load the demo accounts (seed_demo_data; skips
                          any that already exist, so it's safe every deploy)
    anything else      -> remove them (remove_demo_data)

Demo accounts all share the password in the README, so switch this
off before real members join.
"""
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed or remove demo accounts depending on SEED_DEMO_DATA."

    def handle(self, *args, **options):
        if os.getenv("SEED_DEMO_DATA", "0") == "1":
            self.stdout.write("sync_demo_data: SEED_DEMO_DATA=1, loading demo accounts.")
            call_command("seed_demo_data")
        else:
            self.stdout.write("sync_demo_data: SEED_DEMO_DATA is off, removing demo accounts.")
            call_command("remove_demo_data")

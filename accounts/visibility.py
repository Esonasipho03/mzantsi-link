"""
Who is allowed to see (and message) whom.

The rule, from the client:
  * Men and women see each other.
  * LGBTQ+ members (gender "lgbtq" or "other") see only each other, so
    nobody in that group can start texting straight members.
  * Exception: a woman who is open to friendship (looking_for =
    "friendship") is also visible to LGBTQ+ members, and sees them,
    but only those LGBTQ+ members who said they are interested in
    women or both (interested_in = "women" / "both"). An LGBTQ+ member
    who picked "men" sees only their own group.
  * Staff see everyone (so the admin can preview the site).

It is symmetric by design — if A can see B then B can see A — so a chat
can never be started by someone the other person can't see.

This is the single source of truth. Every place that lists or opens
another member (Discover, swipes, Likes, profile pages, chats) goes
through visible_to(), so the rule is enforced on the server, not just
by hiding things in the page.
"""
from functools import reduce
from operator import or_

from django.db.models import Q

from .models import LGBTQ_GROUP, User


def visible_to(viewer, include_self=False):
    """Approved, non-staff members that `viewer` may see.

    The viewer is left out unless include_self=True (own-profile page),
    so nobody can like or message themselves.
    """
    members = User.objects.filter(is_approved=True, is_staff=False)

    if viewer.is_staff:
        return members  # staff see every approved member (no filtering at all)

    if viewer.gender == "man":
        rules = [Q(gender="woman")]
    elif viewer.gender == "woman":
        rules = [Q(gender="man")]
        if viewer.looking_for == "friendship":
            rules.append(Q(gender__in=LGBTQ_GROUP, interested_in__in=("women", "both")))
    elif viewer.gender in LGBTQ_GROUP:
        rules = [Q(gender__in=LGBTQ_GROUP)]
        if viewer.interested_in in ("women", "both"):
            rules.append(Q(gender="woman", looking_for="friendship"))
    else:
        return members.none()  # no gender on file: see nobody

    if include_self:
        rules.append(Q(pk=viewer.pk))
    visible = members.filter(reduce(or_, rules))
    if not include_self:
        visible = visible.exclude(pk=viewer.pk)
    return visible

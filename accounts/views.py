from datetime import timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from django.contrib import messages

from .forms import ProfileEditForm, SignupForm
from .models import Like, ProfilePhoto, User

# Gate for the custom staff dashboard — reuses the normal login + the
# is_staff flag every Django superuser already has, rather than a
# second auth system. Anyone not staff gets bounced to login/home
# instead of a 403, same as login_required's default behaviour.
staff_required = user_passes_test(lambda u: u.is_authenticated and u.is_staff, login_url="login")


def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("post_login_redirect")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


@login_required
def post_login_redirect(request):
    """Sends a freshly logged-in user to the right place: the staff
    dashboard for staff accounts (createsuperuser sets is_approved=False
    by default, so without this check a fresh staff account would be
    stuck on the member waiting screen instead), the grid if a regular
    member has been approved, the waiting screen if not."""
    if request.user.is_staff:
        return redirect("staff_dashboard")
    if request.user.is_approved:
        return redirect("home")
    return redirect("waiting_approval")


@login_required
def waiting_approval_view(request):
    if request.user.is_approved:
        return redirect("home")
    return render(request, "accounts/waiting.html")


def landing_view(request):
    """Public marketing homepage for logged-out visitors.

    Every number and profile shown here is real (pulled from the same
    tables the app itself uses) except two sections that have no data
    behind them at all yet (events/meetups, per-profile match-%% scoring).
    Rather than inventing fake specifics for those (a fake event with a
    made-up date/venue could genuinely mislead someone), they're shown as
    plain "coming soon" teasers with no fabricated details. Preview photos
    stay blurred for anonymous visitors, same rule as an unpaid member.
    """
    members = User.objects.filter(is_staff=False, is_approved=True)
    stats = {
        "total": members.count(),
        "women": members.filter(gender="woman").count(),
        "paying": members.exclude(gender="woman").count(),
    }

    # "Near you tonight" teaser strip — real approved members, most
    # recent first, photo blurred (AnonymousUser is never "unlocked").
    preview_profiles = list(members.order_by("-date_joined")[:6])
    for profile in preview_profiles:
        profile.photo_for_user = profile.photo_for(request.user)

    hero_profile = preview_profiles[0] if preview_profiles else None

    return render(request, "accounts/landing.html", {
        "stats": stats,
        "preview_profiles": preview_profiles,
        "hero_profile": hero_profile,
    })


def home_view(request):
    if not request.user.is_authenticated:
        return landing_view(request)
    if not request.user.is_approved:
        return redirect("waiting_approval")

    # Point 3: approved members only, excluding the viewer — unapproved
    # sign-ups never appear to others.
    profiles = list(User.objects.filter(is_approved=True).exclude(id=request.user.id))

    # Optional filters from the filter sheet (age range + town). Both are
    # real fields on User, so these narrow the actual query — there's no
    # geolocation in the MVP, so a "distance" slider isn't offered here.
    min_age = request.GET.get("min_age")
    max_age = request.GET.get("max_age")
    town_filter = request.GET.get("town")
    if min_age:
        profiles = [p for p in profiles if p.age is None or p.age >= int(min_age)]
    if max_age:
        profiles = [p for p in profiles if p.age is None or p.age <= int(max_age)]
    if town_filter:
        profiles = [p for p in profiles if town_filter.lower() in p.town.lower()]

    # Templates can't call photo_for(viewer) directly (no arguments in
    # template syntax), so resolve each profile's visible photo here.
    for profile in profiles:
        profile.photo_for_user = profile.photo_for(request.user)

    # Scrollable "nearby" strip at the top of the page, Instagram/Facebook
    # style — same-town members first (closest match to "nearby" without
    # real geolocation), then everyone else, photo only.
    nearby_profiles = sorted(profiles, key=lambda p: p.town != request.user.town)

    # The swipe-card stack: anyone the viewer hasn't already swiped on.
    already_swiped_ids = set(
        Like.objects.filter(from_user=request.user).values_list("to_user_id", flat=True)
    )
    stack_profiles = [p for p in profiles if p.id not in already_swiped_ids]
    # Render back-to-front so the first profile ends up on top of the DOM stack.
    stack_profiles.reverse()

    show_unlock_banner = not request.user.has_active_unlock()

    return render(request, "accounts/home.html", {
        "profiles": profiles,
        "nearby_profiles": nearby_profiles,
        "stack_profiles": stack_profiles,
        "show_unlock_banner": show_unlock_banner,
        "selected_town": town_filter or "",
        "min_age": min_age or "",
        "max_age": max_age or "",
    })


@login_required
@require_POST
def swipe_view(request, user_id, action):
    """Records a like/pass from the swipe-card screen. AJAX-only (the
    card JS calls this with fetch); returns whether it created a match."""
    if action not in ("like", "pass"):
        return JsonResponse({"error": "invalid action"}, status=400)

    target = get_object_or_404(User, pk=user_id, is_approved=True)
    like, _ = Like.objects.update_or_create(
        from_user=request.user, to_user=target, defaults={"action": action}
    )
    is_match = action == "like" and Like.is_match(request.user, target)

    response = {"ok": True, "match": is_match, "username": target.username}
    if is_match:
        # Enough to render the "you found your match" reveal client-side
        # without a second request — both photos follow the normal blur
        # rule (photo_for), your own photo is always shown to you.
        target_photo = target.photo_for(request.user)
        response.update({
            "target_photo": target_photo.url if target_photo else "",
            "target_age": target.age,
            "my_photo": request.user.photo.url if request.user.photo else "",
            "my_username": request.user.username,
            "my_age": request.user.age,
        })
    return JsonResponse(response)


@login_required
def likes_view(request):
    """Who has liked the viewer — the Likes tab. Visibility of the photo
    still follows the normal blur rule (photo_for), so this doesn't open
    a new way around the paid-unlock gate.

    ?filter=matches narrows the same list down to mutual likes only,
    via the All/Matches toggle at the top of the page — matches are a
    subset of "people who liked you", not a separate dataset."""
    liker_ids = Like.objects.filter(to_user=request.user, action="like").values_list(
        "from_user_id", flat=True
    )
    likers = list(User.objects.filter(id__in=liker_ids, is_approved=True))
    my_likes = set(
        Like.objects.filter(from_user=request.user, action="like").values_list("to_user_id", flat=True)
    )
    for person in likers:
        person.photo_for_user = person.photo_for(request.user)
        person.is_match = person.id in my_likes

    show_matches_only = request.GET.get("filter") == "matches"
    if show_matches_only:
        likers = [person for person in likers if person.is_match]

    can_message = request.user.has_active_unlock()

    return render(request, "accounts/likes.html", {
        "likers": likers,
        "show_matches_only": show_matches_only,
        "my_photo": request.user.photo,
        "can_message": can_message,
    })


@login_required
def profile_detail_view(request, user_id):
    """A member's profile page — what you land on from the grid, the
    nearby strip, Likes or Matches, instead of being dropped straight
    into a chat. Shows the photo (blur rule still applies), bio and
    interests, whether they've already liked the viewer, and lets the
    viewer like/pass right here instead of only from the Discover stack."""
    profile = get_object_or_404(User, pk=user_id, is_approved=True)
    is_own_profile = profile.id == request.user.id

    can_message = request.user.has_active_unlock()

    my_existing_like = None
    they_liked_me = False
    if not is_own_profile:
        existing = Like.objects.filter(from_user=request.user, to_user=profile).first()
        my_existing_like = existing.action if existing else None
        they_liked_me = Like.objects.filter(
            from_user=profile, to_user=request.user, action="like"
        ).exists()

    gallery_photos = [
        extra.photo_for(request.user) for extra in profile.extra_photos.all()
    ]

    return render(request, "accounts/profile_detail.html", {
        "profile": profile,
        "photo": profile.photo_for(request.user),
        "can_message": can_message,
        "is_own_profile": is_own_profile,
        "my_existing_like": my_existing_like,
        "they_liked_me": they_liked_me,
        "gallery_photos": gallery_photos,
        "gallery_slots_left": max(0, ProfilePhoto.MAX_PER_USER - len(gallery_photos)) if is_own_profile else 0,
    })


@login_required
def my_profile_view(request):
    """The logged-in member's own profile — the "Profile" tab in the
    nav. Read-only here; editing happens on its own screen."""
    return render(request, "accounts/my_profile.html", {
        "profile": request.user,
        "gallery_photos": request.user.extra_photos.all(),
        "gallery_slots_left": max(0, ProfilePhoto.MAX_PER_USER - request.user.extra_photos.count()),
    })


@login_required
def profile_edit_view(request):
    user = request.user
    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES)
        if form.is_valid():
            user.bio = form.cleaned_data["bio"]
            user.interests = ",".join(form.cleaned_data["interests"])
            new_photo = form.cleaned_data.get("photo")
            if new_photo:
                user.photo = new_photo
            user.save()
            if new_photo:
                user.generate_blurred_photo()
                user.save()
            return redirect("my_profile")
    else:
        form = ProfileEditForm(initial={"bio": user.bio, "interests": user.interest_list()})

    return render(request, "accounts/profile_edit.html", {
        "form": form,
        "profile": user,
        "gallery_photos": user.extra_photos.all(),
        "gallery_slots_left": max(0, ProfilePhoto.MAX_PER_USER - user.extra_photos.count()),
        "gallery_max": ProfilePhoto.MAX_PER_USER,
    })


@login_required
@require_POST
def gallery_photo_upload_view(request):
    """Add one or more extra gallery photos — a separate, single-
    purpose endpoint (its own multi-file <input>, not part of
    ProfileEditForm, since Django's ImageField can't bind to several
    files at once) so uploading photos doesn't depend on the bio/
    interests form validating too."""
    user = request.user
    existing_count = user.extra_photos.count()
    remaining_slots = max(0, ProfilePhoto.MAX_PER_USER - existing_count)
    new_files = request.FILES.getlist("gallery_photos")

    if not new_files:
        messages.error(request, "Choose at least one photo to add.")
    elif not remaining_slots:
        messages.warning(request, "You've already got the maximum number of extra photos — remove one to add another.")
    else:
        if len(new_files) > remaining_slots:
            messages.warning(
                request,
                f"You can have {ProfilePhoto.MAX_PER_USER} extra photos at most — "
                f"added the first {remaining_slots} and skipped the rest.",
            )
        next_position = existing_count
        for photo_file in new_files[:remaining_slots]:
            gallery_photo = ProfilePhoto.objects.create(
                user=user, photo=photo_file, position=next_position
            )
            gallery_photo.generate_blurred_photo()
            gallery_photo.save()
            next_position += 1

    return redirect("profile_edit")


@login_required
@require_POST
def gallery_photo_delete_view(request, photo_id):
    """Remove one of your own extra gallery photos. Ownership is
    enforced by the get_object_or_404 filter — a user can never pass
    another member's photo id here."""
    photo = get_object_or_404(ProfilePhoto, pk=photo_id, user=request.user)
    photo.delete()
    return redirect("profile_edit")


@login_required
def settings_view(request):
    return render(request, "accounts/settings.html", {"profile": request.user})


@staff_required
def staff_dashboard_view(request):
    """A styled stand-in for Django admin's approval screen (point 6 of
    the MVP), for whoever's moderating day-to-day without needing to
    learn /admin/. Same is_staff gate as Django admin — it's a second
    view of the same data, not a second permission system."""
    # Staff/superuser accounts aren't members — createsuperuser also
    # leaves is_approved False, so without this they'd show up in the
    # moderation queue next to real sign-ups.
    non_staff = User.objects.filter(is_staff=False)
    pending = non_staff.filter(is_approved=False).order_by("date_joined")
    members = non_staff.filter(is_approved=True).order_by("-date_joined")

    # "Paying" covers everyone except women (men, LGBTQ+, other) — they
    # all follow the same pay-to-unlock rule, so they're counted together
    # rather than as separate "men" stats that LGBTQ+/other wouldn't fit.
    approved = non_staff.filter(is_approved=True)
    paying_members = approved.exclude(gender="woman")
    unlocked_paying = sum(1 for m in paying_members if m.has_active_unlock())

    stats = {
        "total": non_staff.count(),
        "pending": pending.count(),
        "approved": members.count(),
        "women": approved.filter(gender="woman").count(),
        "paying": paying_members.count(),
        "unlocked_paying": unlocked_paying,
    }

    return render(request, "accounts/staff_dashboard.html", {
        "pending": pending,
        "members": members,
        "stats": stats,
    })


@staff_required
@require_POST
def staff_approve_view(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    target.is_approved = True
    target.save()
    return redirect("staff_dashboard")


@staff_required
@require_POST
def staff_reject_view(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    target.is_approved = False
    target.save()
    return redirect("staff_dashboard")


@staff_required
@require_POST
def staff_toggle_unlock_view(request, user_id):
    """Manual override for the admin dashboard. Granting an unlock here
    follows the same 12-month rule as a real payment, so it doesn't
    quietly become a permanent freebie; locking clears the expiry too."""
    target = get_object_or_404(User, pk=user_id)
    if target.gender != "woman":  # women are always unlocked — nothing to toggle
        # Toggle off the *effective* state (has_active_unlock), not the
        # raw is_unlocked flag — otherwise an expired-but-still-True
        # record would show as "Lock" when the member is really locked.
        currently_active = target.has_active_unlock()
        target.is_unlocked = not currently_active
        target.unlock_expires_at = timezone.now() + timedelta(days=365) if not currently_active else None
        target.save()
    return redirect("staff_dashboard")

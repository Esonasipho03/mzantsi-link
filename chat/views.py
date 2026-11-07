from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import User
from accounts.visibility import visible_to
from .models import Message
from .forms import MessageForm
from .templatetags.chat_extras import day_label


def unread_total(me):
    """Unread messages sent to `me` by people `me` can still see."""
    return Message.objects.filter(
        recipient=me, read_at__isnull=True, sender__in=visible_to(me)
    ).count()


def _mark_read(me, other):
    Message.objects.filter(recipient=me, sender=other, read_at__isnull=True).update(read_at=timezone.now())


def _conversations_for(me):
    """Everyone `me` has exchanged at least one message with, most
    recent conversation first, each paired with its last message.
    Shared by the inbox and the conversation page, so the same list
    can sit as a sidebar next to an open chat on wider screens."""
    partner_ids = Message.objects.filter(Q(sender=me) | Q(recipient=me)).values_list(
        "sender_id", "recipient_id"
    )
    other_ids = {uid for pair in partner_ids for uid in pair if uid != me.id}

    conversations = []
    for other in visible_to(me).filter(id__in=other_ids):
        last = Message.objects.filter(
            Q(sender=me, recipient=other) | Q(sender=other, recipient=me)
        ).order_by("-created_at").first()
        other.photo_for_user = other.photo_for(me)
        other.unread = Message.objects.filter(sender=other, recipient=me, read_at__isnull=True).count()
        conversations.append((other, last))

    conversations.sort(key=lambda pair: pair[1].created_at, reverse=True)
    return conversations


@login_required
def inbox_view(request):
    """The "Chats" tab in the nav."""
    conversations = _conversations_for(request.user)
    return render(request, "chat/inbox.html", {"conversations": conversations})


def _chat_partner(me, user_id):
    """The person `me` may chat with, or a 404 / 403. One place for the
    access rules so the page, the send box and the live-update poll can
    never disagree."""
    # Only people the viewer is allowed to see can be chatted with.
    other = get_object_or_404(visible_to(me), pk=user_id)
    other.photo_for_user = other.photo_for(me)
    # Chat is a paid feature for everyone except women (men, LGBTQ+,
    # other) — has_active_unlock() also respects the 12-month expiry.
    if not me.has_active_unlock():
        raise PermissionDenied("Unlock for R99 to start chatting.")
    return other


def _message_json(message, me):
    return {
        "id": message.id,
        "mine": message.sender_id == me.id,
        "text": message.text,
        "time": timezone.localtime(message.created_at).strftime("%H:%M"),
        "day": day_label(message.created_at),
    }


def _thread(me, other):
    return Message.objects.filter(
        Q(sender=me, recipient=other) | Q(sender=other, recipient=me)
    )


@login_required
def messages_since_view(request, user_id):
    """Live updates: the open chat page asks every few seconds for
    messages newer than the last one it has, and adds them without a
    reload. Same access rules as the page itself."""
    me = request.user
    other = _chat_partner(me, user_id)
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    new = list(_thread(me, other).filter(id__gt=after).order_by("id"))
    _mark_read(me, other)  # the chat is open on screen, so anything arriving now is read
    return JsonResponse({"messages": [_message_json(m, me) for m in new]})


@login_required
def unread_count_view(request):
    """Polled by every page to keep the Chats badge current."""
    return JsonResponse({"count": unread_total(request.user)})


@login_required
def conversation_view(request, user_id):
    """
    Basic chat. New messages appear on their own: the page polls
    messages_since_view every few seconds (no websockets), and the send
    box posts without reloading. It still works as a plain form POST +
    redirect if JavaScript is off.

    Access rule: a man can only chat once he is unlocked. Point 3 of
    the brief ("chat only if guy is paid") is enforced here.
    """
    me = request.user
    other = _chat_partner(me, user_id)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = me
            message.recipient = other
            message.save()
            if is_ajax:  # sent from the chat page without a reload
                return JsonResponse({"ok": True, "message": _message_json(message, me)})
            return redirect("conversation", user_id=other.id)  # redirect avoids resubmission on refresh
        if is_ajax:
            return JsonResponse({"ok": False}, status=400)
    else:
        form = MessageForm()

    if request.method == "GET":
        _mark_read(me, other)  # opening the conversation reads it

    # Named chat_messages, not messages — "messages" is reserved by
    # Django's built-in flash-messages framework (rendered in
    # base.html), and reusing it here was shadowing that and leaking
    # the raw conversation into the site-wide alert area.
    chat_messages = list(_thread(me, other))

    # Fed to a sidebar list that sits next to the open conversation on
    # wider screens (hidden on mobile, where the chat is full-screen).
    conversations = _conversations_for(me)
    if other.id not in [o.id for o, _ in conversations]:
        # Starting a brand-new conversation (no messages sent yet) —
        # still show them in the sidebar so the list doesn't just
        # vanish while you're mid-chat.
        conversations.insert(0, (other, None))

    return render(request, "chat/conversation.html", {
        "other": other,
        "chat_messages": chat_messages,
        "last_id": chat_messages[-1].id if chat_messages else 0,
        "form": form,
        "conversations": conversations,
    })

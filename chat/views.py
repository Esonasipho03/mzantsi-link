from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Max
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import User
from .models import Message
from .forms import MessageForm


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
    for other in User.objects.filter(id__in=other_ids):
        last = Message.objects.filter(
            Q(sender=me, recipient=other) | Q(sender=other, recipient=me)
        ).order_by("-created_at").first()
        other.photo_for_user = other.photo_for(me)
        conversations.append((other, last))

    conversations.sort(key=lambda pair: pair[1].created_at, reverse=True)
    return conversations


@login_required
def inbox_view(request):
    """The "Chats" tab in the nav."""
    conversations = _conversations_for(request.user)
    return render(request, "chat/inbox.html", {"conversations": conversations})


@login_required
def conversation_view(request, user_id):
    """
    Point 5 of the MVP: basic chat. Plain form POST + redirect — no
    polling, no websockets. Reloading the page is how you see new
    messages, per the brief.

    Access rule: a man can only chat once he is unlocked. Point 3 of
    the brief ("chat only if guy is paid") is enforced here.
    """
    other = get_object_or_404(User, pk=user_id)
    me = request.user
    other.photo_for_user = other.photo_for(me)

    if me.gender == "man" and not me.is_unlocked:
        raise PermissionDenied("Unlock for R99 to start chatting.")

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = me
            message.recipient = other
            message.save()
            return redirect("conversation", user_id=other.id)  # redirect avoids resubmission on refresh
    else:
        form = MessageForm()

    # Named chat_messages, not messages — "messages" is reserved by
    # Django's built-in flash-messages framework (rendered in
    # base.html), and reusing it here was shadowing that and leaking
    # the raw conversation into the site-wide alert area.
    chat_messages = Message.objects.filter(
        Q(sender=me, recipient=other) | Q(sender=other, recipient=me)
    )

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
        "form": form,
        "conversations": conversations,
    })

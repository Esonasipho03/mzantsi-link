from django.urls import path
from .views import (
    signup_view, post_login_redirect, waiting_approval_view, home_view,
    profile_detail_view, my_profile_view, swipe_view, likes_view,
    profile_edit_view, gallery_photo_upload_view, gallery_photo_delete_view, settings_view,
    staff_dashboard_view, staff_approve_view, staff_reject_view, staff_toggle_unlock_view,
)

urlpatterns = [
    path("", home_view, name="home"),
    path("signup/", signup_view, name="signup"),
    path("post-login/", post_login_redirect, name="post_login_redirect"),
    path("waiting/", waiting_approval_view, name="waiting_approval"),
    path("swipe/<int:user_id>/<str:action>/", swipe_view, name="swipe"),
    path("likes/", likes_view, name="likes"),
    path("profile/edit/", profile_edit_view, name="profile_edit"),
    path("profile/edit/gallery/upload/", gallery_photo_upload_view, name="gallery_photo_upload"),
    path("profile/edit/gallery/<int:photo_id>/delete/", gallery_photo_delete_view, name="gallery_photo_delete"),
    path("profile/<int:user_id>/", profile_detail_view, name="profile_detail"),
    path("profile/", my_profile_view, name="my_profile"),
    path("settings/", settings_view, name="settings"),
    path("staff/", staff_dashboard_view, name="staff_dashboard"),
    path("staff/<int:user_id>/approve/", staff_approve_view, name="staff_approve"),
    path("staff/<int:user_id>/reject/", staff_reject_view, name="staff_reject"),
    path("staff/<int:user_id>/toggle-unlock/", staff_toggle_unlock_view, name="staff_toggle_unlock"),
]

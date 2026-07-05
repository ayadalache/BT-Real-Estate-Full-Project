from django.urls import path

from apps.users.views import MyProfilePhotoView, MyProfileView

app_name = "users"

urlpatterns = [
    path("me/", MyProfileView.as_view(), name="my-profile"),
    path("me/photo/", MyProfilePhotoView.as_view(), name="my-profile-photo"),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.listings.views import ListingImageDeleteView, ListingImageUploadView, ListingViewSet

app_name = "listings"

router = DefaultRouter()
router.register("", ListingViewSet, basename="listing")

urlpatterns = [
    path(
        "<uuid:public_id>/images/",
        ListingImageUploadView.as_view(),
        name="listing-image-upload",
    ),
    path(
        "<uuid:public_id>/images/<int:image_id>/",
        ListingImageDeleteView.as_view(),
        name="listing-image-delete",
    ),
    path("", include(router.urls)),
]

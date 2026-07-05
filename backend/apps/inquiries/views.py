from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from apps.inquiries import services
from apps.inquiries.models import Inquiry
from apps.inquiries.permissions import IsListingRealtorOrAdmin
from apps.inquiries.serializers import (
    DashboardInquirySerializer,
    InquiryCreateSerializer,
    InquirySerializer,
    InquiryStatusUpdateSerializer,
)
from core.permissions import IsStaffOrAdmin
from core.responses import success_response


class InquiryCreateView(APIView):
    """
    POST /api/v1/inquiries/ - public "Make An Inquiry" submission.
    Open to both guests and authenticated users; when authenticated, the
    inquiry is automatically linked to the submitter's account so it shows
    up on their dashboard.
    """

    permission_classes = [AllowAny]  # still auto-links user if a valid token is present
    throttle_scope = "inquiry"
    serializer_class = InquiryCreateSerializer

    def post(self, request):
        serializer = InquiryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        user = request.user if request.user and request.user.is_authenticated else None
        inquiry = services.create_inquiry(
            listing=validated["listing"],
            name=validated["name"],
            email=validated["email"],
            phone=validated.get("phone", ""),
            message=validated["message"],
            user=user,
        )
        return success_response(
            InquirySerializer(inquiry, context={"request": request}).data,
            message="Your inquiry has been sent to the listing's realtor.",
            status_code=201,
        )


class InquiryInboxView(ListAPIView):
    """
    GET /api/v1/inquiries/ - realtor/Admin inbox: inquiries received on the
    requesting realtor's own listings (or all listings, for Admins).
    """

    serializer_class = InquirySerializer
    permission_classes = [IsStaffOrAdmin]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Inquiry.objects.none()
        return services.get_realtor_inbox(self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(serializer.data)


class InquiryDetailView(RetrieveUpdateAPIView):
    """
    GET  /api/v1/inquiries/{id}/ - view a single inquiry (owning realtor/Admin)
    PATCH /api/v1/inquiries/{id}/ - update its status (owning realtor/Admin)
    """

    queryset = Inquiry.objects.select_related("listing", "user")
    permission_classes = [IsStaffOrAdmin, IsListingRealtorOrAdmin]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return InquiryStatusUpdateSerializer
        return InquirySerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return success_response(InquirySerializer(instance, context={"request": request}).data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = services.update_inquiry_status(inquiry=instance, status=serializer.validated_data["status"])
        return success_response(
            InquirySerializer(updated, context={"request": request}).data,
            message="Inquiry status updated.",
        )


class DashboardView(ListAPIView):
    """GET /api/v1/inquiries/dashboard/ - "listings you've inquired about" (dashboard.html)."""

    serializer_class = DashboardInquirySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Inquiry.objects.none()
        return services.get_dashboard_inquiries(self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(serializer.data)

from django.urls import path

from apps.inquiries.views import DashboardView, InquiryCreateView, InquiryDetailView, InquiryInboxView

app_name = "inquiries"

urlpatterns = [
    path("", InquiryCreateView.as_view(), name="inquiry-create"),
    path("inbox/", InquiryInboxView.as_view(), name="inquiry-inbox"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("<int:pk>/", InquiryDetailView.as_view(), name="inquiry-detail"),
]

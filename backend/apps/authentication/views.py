from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.authentication import services
from apps.authentication.serializers import (
    ChangePasswordSerializer,
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    VerifyEmailSerializer,
)
from apps.users.serializers import UserProfileSerializer
from core.responses import error_response, success_response


class RegisterView(APIView):
    """POST /api/v1/auth/register/ - create account, send verification email."""

    permission_classes = [AllowAny]
    throttle_scope = "register"
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data
        validated.pop("password2")

        user = services.register_user(**validated)
        return success_response(
            {"user": UserProfileSerializer(user).data},
            message="Registration successful. Please check your email to verify your account.",
            status_code=201,
        )


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ - obtain JWT access/refresh tokens."""

    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return success_response(serializer.validated_data, message="Login successful.")


class RefreshView(TokenRefreshView):
    """POST /api/v1/auth/refresh/ - exchange a refresh token for a new access token."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            return error_response("Refresh token is invalid or expired.", status_code=401)
        return success_response(serializer.validated_data, message="Token refreshed.")


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ - blacklist the provided refresh token."""

    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            raise ValidationError({"refresh": "Invalid or already-invalidated token."})
        return success_response(message="Logged out successfully.")


class VerifyEmailView(APIView):
    """POST /api/v1/auth/verify-email/ - confirm a signed email-verification token."""

    permission_classes = [AllowAny]
    serializer_class = VerifyEmailSerializer

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.verify_email(serializer.validated_data["token"])
        except services.TokenExpiredOrInvalid as exc:
            return error_response(str(exc), status_code=400)
        return success_response(
            {"user": UserProfileSerializer(user).data}, message="Email verified successfully."
        )


class ResendVerificationView(APIView):
    """POST /api/v1/auth/resend-verification/ - re-send the verification email."""

    permission_classes = [AllowAny]
    throttle_scope = "register"
    serializer_class = ResendVerificationSerializer

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.users.models import User

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        if user:
            services.resend_verification_email(user)
        # Same response regardless of whether the email exists - prevents enumeration.
        return success_response(message="If that account exists, a verification email has been sent.")


class PasswordResetRequestView(APIView):
    """POST /api/v1/auth/password-reset/ - request a password reset email."""

    permission_classes = [AllowAny]
    throttle_scope = "password_reset"
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return success_response(message="If that account exists, a password reset email has been sent.")


class PasswordResetConfirmView(APIView):
    """POST /api/v1/auth/password-reset/confirm/ - set a new password using a reset token."""

    permission_classes = [AllowAny]
    throttle_scope = "password_reset"
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.confirm_password_reset(
                serializer.validated_data["token"], serializer.validated_data["new_password"]
            )
        except services.TokenExpiredOrInvalid as exc:
            return error_response(str(exc), status_code=400)
        return success_response(message="Password has been reset successfully. You may now log in.")


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/ - authenticated user changes their own password."""

    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        services.change_password(request.user, serializer.validated_data["new_password"])
        return success_response(message="Password changed successfully.")


class MeView(APIView):
    """GET /api/v1/auth/me/ - convenience endpoint returning the current authenticated user."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get(self, request):
        return success_response(UserProfileSerializer(request.user).data)

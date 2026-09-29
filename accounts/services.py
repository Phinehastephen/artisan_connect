import logging
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import EmailVerificationToken, PasswordResetToken, User
from customers.models import Customer
from artisans.models import Artisan
from artisans.services import recalculate_artisan_price_range

logger = logging.getLogger(__name__)


@transaction.atomic
def create_email_verification_token(user):
    user.email_verification_tokens.filter(used_at__isnull=True).update(
        used_at=timezone.now()
    )

    return EmailVerificationToken.objects.create(user=user)


def send_verification_email(user, token):
    verification_link = (
        f"{settings.BACKEND_BASE_URL}"
        f"/api/v1/accounts/verify-email/{token.token}"
    )

    try:
        send_mail(
            subject="Verify your Artisan Connect email",
            message=(
                "Hi, please verify your email by visiting the link below:\n\n"
                f"{verification_link}\n\n"
                "This link expires in 24 hours."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception:
        # Email verification is non-blocking (see README): a delivery
        # failure here must never surface as a registration/API error for
        # an already-committed user. Resend is available separately.
        logger.exception(
            "Failed to send verification email to %s", user.email
        )


@transaction.atomic
def verify_email(token_str):
    try:
        token = EmailVerificationToken.objects.select_related("user").get(
            token=token_str
        )
    except EmailVerificationToken.DoesNotExist:
        raise ValidationError("Invalid verification link.")

    if not token.is_valid():
        raise ValidationError(
            "This verification link has expired or has already been used."
        )

    user = token.user
    user.email_verified = True
    user.save(update_fields=["email_verified"])

    token.used_at = timezone.now()
    token.save(update_fields=["used_at"])

    return user


def _generate_password_reset_code():
    return f"{secrets.randbelow(10**6):06d}"


def send_password_reset_code_email(user, code):
    try:
        send_mail(
            subject="Your Artisan Connect password reset code",
            message=(
                f"Your password reset code is: {code}\n\n"
                "Enter this code in the app to choose a new password. "
                "It expires in 10 minutes.\n\n"
                "If you didn't request a password reset, you can ignore "
                "this email - your password won't change."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception:
        # Same reasoning as send_verification_email: never leak delivery
        # failures (or account existence) through the API response.
        logger.exception(
            "Failed to send password reset code to %s", user.email
        )


def send_password_changed_email(user):
    try:
        send_mail(
            subject="Your Artisan Connect password was changed",
            message=(
                "The password for your Artisan Connect account was just "
                "changed. If this wasn't you, reset your password "
                "immediately and contact support."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception:
        logger.exception(
            "Failed to send password changed notice to %s", user.email
        )


@transaction.atomic
def request_password_reset(email):
    """
    Always returns None, whether or not the email belongs to an account,
    so the endpoint can't be used to discover registered emails.
    """
    user = User.objects.filter(email__iexact=email, is_active=True).first()

    if user is None:
        return None

    user.password_reset_tokens.filter(used_at__isnull=True).update(
        used_at=timezone.now()
    )

    code = _generate_password_reset_code()
    PasswordResetToken.objects.create(
        user=user,
        code_hash=make_password(code),
    )

    transaction.on_commit(lambda: send_password_reset_code_email(user, code))

    return None


def verify_password_reset_code(email, code):
    """
    Exchanges a correct 6-digit code for a single-use reset_token.

    Not wrapped in @transaction.atomic as a whole on purpose: a failed
    attempt must be persisted before raising, otherwise the rollback would
    undo the attempt counter and allow unlimited guessing.
    """
    invalid = ValidationError("Invalid or expired code.")

    with transaction.atomic():
        reset = (
            PasswordResetToken.objects.select_for_update()
            .select_related("user")
            .filter(
                user__email__iexact=email,
                user__is_active=True,
                used_at__isnull=True,
                verified_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

        if reset is None or not reset.code_is_usable():
            reset = None
        elif not check_password(code, reset.code_hash):
            reset.attempts += 1
            reset.save(update_fields=["attempts"])
            reset = None
        else:
            reset.verified_at = timezone.now()
            reset.reset_token = secrets.token_urlsafe(32)
            reset.save(update_fields=["verified_at", "reset_token"])

    if reset is None:
        raise invalid

    return reset.reset_token


@transaction.atomic
def reset_password(reset_token, new_password):
    try:
        reset = (
            PasswordResetToken.objects.select_for_update()
            .select_related("user")
            .get(reset_token=reset_token)
        )
    except PasswordResetToken.DoesNotExist:
        raise ValidationError("Invalid or expired reset token.")

    if not reset.reset_token_is_usable():
        raise ValidationError("Invalid or expired reset token.")

    user = reset.user
    validate_password(new_password, user=user)

    user.set_password(new_password)
    # Receiving the code proves control of the inbox, same as clicking the
    # verification link.
    user.email_verified = True
    user.save(update_fields=["password", "email_verified"])

    reset.used_at = timezone.now()
    reset.save(update_fields=["used_at"])

    transaction.on_commit(lambda: send_password_changed_email(user))

    return user


@transaction.atomic
def register_customer(validated_data):
    phone_number = validated_data.pop("phone_number")
    password = validated_data.pop("password")

    user = User(
        **validated_data,
        role=User.Role.CUSTOMER,
    )

    user.set_password(password)
    user.save()

    Customer.objects.create(
        user=user,
        phone_number=phone_number,
    )

    token = create_email_verification_token(user)
    transaction.on_commit(lambda: send_verification_email(user, token))

    return user


@transaction.atomic
def register_artisan(validated_data):
    phone_number = validated_data.pop("phone_number")
    password = validated_data.pop("password")
    services = validated_data.pop("services")

    user = User(
        **validated_data,
        role=User.Role.ARTISAN,
    )

    user.set_password(password)
    user.save()

    artisan = Artisan.objects.create(
        user=user,
        phone_number=phone_number,
    )

    artisan.services.set(services)
    recalculate_artisan_price_range(artisan)

    token = create_email_verification_token(user)
    transaction.on_commit(lambda: send_verification_email(user, token))

    return user
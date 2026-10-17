from datetime import timedelta
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Max, Min
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from accounts.models import User
from notifications.models import Notification
from notifications.services import create_notification, notify_admins
from services.models import Service
from .models import Artisan, ServiceChangeRequest, ServiceQualificationEvidence


logger = logging.getLogger(__name__)

MAX_ARTISAN_SERVICES = 3
SERVICE_CHANGE_REQUEST_COOLDOWN = timedelta(days=365)
QUALIFICATION_EVIDENCE_CATEGORIES = tuple(
    ServiceQualificationEvidence.Category.values
)
MIN_QUALIFICATION_EVIDENCE_CATEGORIES = 2
MAX_QUALIFICATION_EVIDENCE_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_QUALIFICATION_EVIDENCE_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".webp",
}
QUALIFICATION_EVIDENCE_SIGNATURES = {
    ".jpg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
    ".png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
    ".webp": lambda content: (
        content.startswith(b"RIFF") and content[8:12] == b"WEBP"
    ),
}


def _run_email_in_background(func, *args):
    from accounts.services import run_in_background

    run_in_background(func, *args)


def _lock(artisan):
    Artisan.objects.select_for_update().filter(pk=artisan.pk).first()
    artisan.refresh_from_db()


@transaction.atomic
def add_service_to_artisan(artisan, service):
    _lock(artisan)

    if artisan.services.filter(id=service.id).exists():
        raise ValidationError(
            "This service is already assigned to the artisan."
        )

    if artisan.services.count() >= MAX_ARTISAN_SERVICES:
        raise ValidationError(
            "An artisan can offer a maximum of 3 services."
        )

    if not service.is_active:
        raise ValidationError(
            "This service is currently unavailable."
        )

    artisan.services.add(service)

    recalculate_artisan_price_range(artisan)

    return artisan


def recalculate_artisan_price_range(artisan):
    # Inactive services can't be booked, so they don't set the range.
    price_range = artisan.services.filter(is_active=True).aggregate(
        starting_price=Min("minimum_price"),
        maximum_price=Max("maximum_price"),
    )

    artisan.starting_price = price_range["starting_price"]
    artisan.maximum_price = price_range["maximum_price"]
    artisan.save(update_fields=["starting_price", "maximum_price"])


def _ensure_pending(artisan):
    if artisan.verification_status != Artisan.VerificationStatus.PENDING:
        raise ValidationError(
            "Only pending artisans can be approved or rejected."
        )


@transaction.atomic
def approve_artisan(artisan):
    # Locked so two admins acting at the same moment can't both decide.
    _lock(artisan)
    _ensure_pending(artisan)

    artisan.verification_status = Artisan.VerificationStatus.VERIFIED
    artisan.save(update_fields=["verification_status"])

    return artisan


@transaction.atomic
def reject_artisan(artisan):
    _lock(artisan)
    _ensure_pending(artisan)

    artisan.verification_status = Artisan.VerificationStatus.REJECTED
    artisan.save(update_fields=["verification_status"])

    return artisan


def _validate_service_selection(service_ids):
    if not service_ids:
        raise ValidationError("Select at least one service.")

    service_ids = list(dict.fromkeys(service_ids))
    if len(service_ids) > MAX_ARTISAN_SERVICES:
        raise ValidationError(
            "An artisan can offer a maximum of 3 services."
        )

    services = list(
        Service.objects.filter(id__in=service_ids, is_active=True)
    )

    if len(services) != len(service_ids):
        raise ValidationError("Only active services can be requested.")

    return services


def _validate_qualification_evidence(qualification_evidence):
    supplied = {
        category: files if isinstance(files, (list, tuple)) else [files]
        for category, files in (qualification_evidence or {}).items()
        if files
    }
    invalid_categories = set(supplied) - set(QUALIFICATION_EVIDENCE_CATEGORIES)
    if invalid_categories:
        raise ValidationError("Unsupported qualification evidence category.")

    if len(supplied) < MIN_QUALIFICATION_EVIDENCE_CATEGORIES:
        raise ValidationError(
            "Provide evidence from at least two of the three qualification categories."
        )

    for files in supplied.values():
        for file in files:
            filename = file.name
            if (
                not filename
                or len(filename) > 255
                or filename != filename.strip()
                or "/" in filename
                or "\\" in filename
                or any(ord(character) < 32 or ord(character) == 127 for character in filename)
                or not filename.rsplit(".", 1)[0]
            ):
                raise ValidationError("Evidence filename is invalid.")

            extension = filename.rsplit(
                ".", 1)[-1].lower() if "." in filename else ""
            extension = f".{extension}"
            if extension not in ALLOWED_QUALIFICATION_EVIDENCE_EXTENSIONS:
                raise ValidationError(
                    "Evidence files must be PDF, JPG, JPEG, PNG, or WEBP."
                )
            if file.size > MAX_QUALIFICATION_EVIDENCE_FILE_SIZE:
                raise ValidationError(
                    "Each evidence file must be 10 MB or smaller.")

            file.seek(0)
            content_header = file.read(1024)
            file.seek(0)
            if extension == ".pdf":
                valid_signature = b"%PDF-" in content_header
            else:
                valid_signature = QUALIFICATION_EVIDENCE_SIGNATURES[extension](
                    content_header
                )
            if not valid_signature:
                raise ValidationError(
                    f"The file content does not match its {extension} filename."
                )

    return [
        (category, file)
        for category, files in supplied.items()
        for file in files
    ]


@transaction.atomic
def create_service_change_request(
    *, artisan, service_ids, reason, qualification_evidence
):
    _lock(artisan)

    if artisan.verification_status != Artisan.VerificationStatus.VERIFIED:
        raise ValidationError(
            "Only verified artisans can request a service change."
        )

    if not reason or not str(reason).strip():
        raise ValidationError(
            "A reason is required for the service change request.")

    if ServiceChangeRequest.objects.filter(
        artisan=artisan,
        status=ServiceChangeRequest.Status.PENDING,
    ).exists():
        raise ValidationError(
            "You already have a pending service change request."
        )

    recent_approved = ServiceChangeRequest.objects.filter(
        artisan=artisan,
        status=ServiceChangeRequest.Status.APPROVED,
        reviewed_at__gte=timezone.now() - SERVICE_CHANGE_REQUEST_COOLDOWN,
    ).exists()

    if recent_approved:
        raise ValidationError(
            "A service change request can only be submitted once every 12 months."
        )

    services = _validate_service_selection(service_ids)
    current_service_ids = set(
        artisan.services.values_list("id", flat=True)
    )
    requested_service_ids = {service.id for service in services}
    if not current_service_ids:
        raise ValidationError(
            "A service change request requires at least one currently assigned service."
        )
    if not current_service_ids - requested_service_ids:
        raise ValidationError(
            "A service change must replace at least one currently offered service."
        )
    if not requested_service_ids - current_service_ids:
        raise ValidationError(
            "A service change must include at least one new service."
        )
    evidence_files = _validate_qualification_evidence(qualification_evidence)

    request = ServiceChangeRequest.objects.create(
        artisan=artisan,
        reason=str(reason).strip(),
        status=ServiceChangeRequest.Status.PENDING,
    )
    request.services.set(services)
    for category, file in evidence_files:
        ServiceQualificationEvidence.objects.create(
            service_change_request=request,
            category=category,
            file=file,
        )
    artisan_name = artisan.business_name or artisan.user.full_name
    requested_services = ", ".join(service.name for service in services)
    notify_admins(
        notification_type=Notification.Type.SERVICE_CHANGE_REQUESTED,
        title=f"Service change request #{request.pk} needs review",
        message=(
            f"{artisan_name} requested these services: {requested_services}. "
            f"Reason: {request.reason}"
        )[:500],
        target_path="/api/v1/artisans/service-change-requests",
    )
    request_id = request.pk
    transaction.on_commit(
        lambda: _run_email_in_background(
            send_service_change_request_admin_notification, request_id
        )
    )

    return request


@transaction.atomic
def approve_service_change_request(service_change_request):
    if service_change_request.status != ServiceChangeRequest.Status.PENDING:
        raise ValidationError(
            "Only pending service change requests can be approved."
        )

    if service_change_request.services.filter(is_active=True).count() == 0:
        raise ValidationError(
            "This request does not contain any active services.")

    service_ids = list(
        service_change_request.services.filter(
            is_active=True).values_list("id", flat=True)
    )
    _validate_service_selection(service_ids)

    artisan = service_change_request.artisan
    artisan.services.set(service_ids)
    recalculate_artisan_price_range(artisan)

    service_change_request.status = ServiceChangeRequest.Status.APPROVED
    service_change_request.reviewed_at = timezone.now()
    service_change_request.save(update_fields=["status", "reviewed_at"])
    create_notification(
        recipient=artisan.user,
        notification_type=Notification.Type.SERVICE_CHANGE_APPROVED,
        title="Service change request approved",
        message=f"Your service change request #{service_change_request.pk} was approved.",
        target_path="/api/v1/artisans/service-change-requests",
    )
    request_id = service_change_request.pk
    transaction.on_commit(
        lambda: _run_email_in_background(
            send_service_change_request_decision_notification, request_id
        )
    )

    return service_change_request


@transaction.atomic
def reject_service_change_request(service_change_request):
    if service_change_request.status != ServiceChangeRequest.Status.PENDING:
        raise ValidationError(
            "Only pending service change requests can be rejected."
        )

    service_change_request.status = ServiceChangeRequest.Status.REJECTED
    service_change_request.reviewed_at = timezone.now()
    service_change_request.save(update_fields=["status", "reviewed_at"])
    create_notification(
        recipient=service_change_request.artisan.user,
        notification_type=Notification.Type.SERVICE_CHANGE_REJECTED,
        title="Service change request rejected",
        message=f"Your service change request #{service_change_request.pk} was rejected.",
        target_path="/api/v1/artisans/service-change-requests",
    )
    request_id = service_change_request.pk
    transaction.on_commit(
        lambda: _run_email_in_background(
            send_service_change_request_decision_notification, request_id
        )
    )

    return service_change_request


def send_service_change_request_admin_notification(request_id):
    try:
        service_change_request = ServiceChangeRequest.objects.select_related(
            "artisan__user"
        ).prefetch_related(
            "services", "qualification_evidence"
        ).get(pk=request_id)
        recipients = list(
            User.objects.filter(role=User.Role.ADMIN, is_active=True)
            .exclude(email="")
            .values_list("email", flat=True)
        )
        if not recipients:
            logger.warning(
                "Service change request %s was submitted but there are no admins to notify",
                request_id,
            )
            return

        artisan = service_change_request.artisan
        artisan_name = artisan.business_name or artisan.user.full_name
        service_names = ", ".join(
            service.name for service in service_change_request.services.all()
        )
        evidence_categories = ", ".join(sorted({
            evidence.get_category_display()
            for evidence in service_change_request.qualification_evidence.all()
        }))
        send_mail(
            subject=f"Service change request #{request_id} needs review",
            message=(
                f"{artisan_name} submitted a service change request.\n\n"
                f"Requested services: {service_names}\n"
                f"Reason: {service_change_request.reason}\n\n"
                f"Qualification evidence: {evidence_categories}\n\n"
                "Review it at GET /api/v1/artisans/service-change-requests. "
                "The response includes protected evidence download links."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
        )
    except Exception:
        logger.exception(
            "Failed to send admin notification for service change request %s",
            request_id,
        )


def send_service_change_request_decision_notification(request_id):
    try:
        service_change_request = ServiceChangeRequest.objects.select_related(
            "artisan__user"
        ).get(pk=request_id)
        artisan_user = service_change_request.artisan.user
        if not artisan_user.email:
            logger.warning(
                "Artisan for service change request %s has no email address",
                request_id,
            )
            return

        decision = service_change_request.status.lower()
        send_mail(
            subject=f"Your service change request was {decision}",
            message=(
                f"Hi {artisan_user.full_name},\n\n"
                f"Your service change request #{request_id} was {decision}."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[artisan_user.email],
        )
    except Exception:
        logger.exception(
            "Failed to send decision notification for service change request %s",
            request_id,
        )


@transaction.atomic
def update_artisan_profile(artisan, **fields):

    if artisan.verification_status != Artisan.VerificationStatus.VERIFIED:
        raise ValidationError(
            "Only verified artisans can modify their profile."
        )

    user = artisan.user
    now = timezone.now()

    # Apps often send the whole form; an unchanged value mustn't start (or
    # trip) a 6-month cooldown.
    current = {
        "full_name": user.full_name,
        "profile_picture": user.profile_picture,
        "business_name": artisan.business_name,
    }
    fields = {
        name: value
        for name, value in fields.items()
        if not (name in current and (value or None) == (current[name] or None))
    }

    # Full name
    if "full_name" in fields:
        if (
            user.full_name_updated_at is not None
            and now < user.full_name_updated_at + relativedelta(months=6)
        ):
            raise ValidationError(
                "Full name can only be changed once every 6 months."
            )

        user.full_name = fields["full_name"]
        user.full_name_updated_at = now

    # Profile picture
    if "profile_picture" in fields:
        if (
            user.profile_picture_updated_at is not None
            and now < user.profile_picture_updated_at + relativedelta(months=6)
        ):
            raise ValidationError(
                "Profile picture can only be changed once every 6 months."
            )

        user.profile_picture = fields["profile_picture"]
        user.profile_picture_updated_at = now

    # Business name
    if "business_name" in fields:
        if (
            artisan.business_name_updated_at is not None
            and now < artisan.business_name_updated_at + relativedelta(months=6)
        ):
            raise ValidationError(
                "Business name can only be changed once every 6 months."
            )

        artisan.business_name = fields["business_name"]
        artisan.business_name_updated_at = now

    # Operational fields
    if "phone_number" in fields:
        artisan.phone_number = fields["phone_number"]

    if "default_location" in fields:
        artisan.default_location = fields["default_location"]

    if "latitude" in fields:
        artisan.latitude = fields["latitude"]

    if "longitude" in fields:
        artisan.longitude = fields["longitude"]

    # Save User changes
    user_fields_to_update = []

    if "full_name" in fields:
        user_fields_to_update.extend([
            "full_name",
            "full_name_updated_at",
        ])

    if "profile_picture" in fields:
        user_fields_to_update.extend([
            "profile_picture",
            "profile_picture_updated_at",
        ])

    if user_fields_to_update:
        user.save(update_fields=user_fields_to_update)

    # Save Artisan changes
    artisan_fields_to_update = []

    if "business_name" in fields:
        artisan_fields_to_update.extend([
            "business_name",
            "business_name_updated_at",
        ])

    if "phone_number" in fields:
        artisan_fields_to_update.append("phone_number")

    if "default_location" in fields:
        artisan_fields_to_update.append("default_location")

    if "latitude" in fields:
        artisan_fields_to_update.append("latitude")

    if "longitude" in fields:
        artisan_fields_to_update.append("longitude")

    if artisan_fields_to_update:
        artisan.save(update_fields=artisan_fields_to_update)

    return artisan

from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from artisans.models import Artisan
from customers.models import Customer
from services.models import Service

import re

from .models import (
    EmailVerificationToken,
    PASSWORD_RESET_MAX_ATTEMPTS,
    PasswordResetToken,
    User,
)
from .services import (
    create_email_verification_token,
    register_customer,
    register_artisan,
    request_password_reset,
    reset_password,
    send_verification_email,
    verify_email,
    verify_password_reset_code,
)
from .permissions import IsCustomer, IsArtisan, IsAdmin
from rest_framework.test import APIRequestFactory


class AccountsBusinessLogicTests(TestCase):

    def setUp(self):
        self.services = []

        for number in range(1, 4):
            service = Service.objects.create(
                name=f"Service {number}",
                description=f"Test service {number}",
                minimum_price=1000,
                maximum_price=5000,
                is_active=True,
            )

            self.services.append(service)

    def test_register_customer_creates_user_and_profile(self):
        user = register_customer(
            {
                "username": "customer1",
                "email": "customer@example.com",
                "full_name": "Test Customer",
                "password": "testpassword123",
                "phone_number": "08000000000",
            }
        )

        self.assertEqual(
            user.role,
            User.Role.CUSTOMER,
        )

        self.assertTrue(
            user.check_password("testpassword123"),
        )

        customer = Customer.objects.get(user=user)

        self.assertEqual(
            customer.phone_number,
            "08000000000",
        )

    def test_register_artisan_creates_user_and_profile_with_services(self):
        user = register_artisan(
            {
                "username": "artisan1",
                "email": "artisan@example.com",
                "full_name": "Test Artisan",
                "password": "testpassword123",
                "phone_number": "08000000000",
                "services": self.services[:2],
            }
        )

        self.assertEqual(
            user.role,
            User.Role.ARTISAN,
        )

        self.assertTrue(
            user.check_password("testpassword123"),
        )

        artisan = Artisan.objects.get(user=user)

        self.assertEqual(
            artisan.phone_number,
            "08000000000",
        )

        self.assertEqual(
            artisan.services.count(),
            2,
        )

    def test_registered_artisan_starts_as_pending_verification(self):
        user = register_artisan(
            {
                "username": "artisan2",
                "email": "artisan2@example.com",
                "full_name": "Test Artisan",
                "password": "testpassword123",
                "phone_number": "08000000000",
                "services": self.services[:1],
            }
        )

        artisan = Artisan.objects.get(user=user)

        self.assertEqual(
            artisan.verification_status,
            Artisan.VerificationStatus.PENDING,
        )


class EmailVerificationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="customer1",
            email="customer@example.com",
            password="testpassword123",
        )

    def test_registration_creates_an_unused_token_and_sends_email(self):
        with self.captureOnCommitCallbacks(execute=True):
            user = register_customer(
                {
                    "username": "customer2",
                    "email": "customer2@example.com",
                    "full_name": "Test Customer",
                    "password": "testpassword123",
                    "phone_number": "08000000000",
                }
            )

        self.assertFalse(user.email_verified)

        token = EmailVerificationToken.objects.get(user=user)
        self.assertTrue(token.is_valid())

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(token.token, mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [user.email])

    def test_valid_token_verifies_email(self):
        token = create_email_verification_token(self.user)

        verified_user = verify_email(token.token)

        self.assertTrue(verified_user.email_verified)

        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

    def test_invalid_token_raises(self):
        with self.assertRaises(ValidationError):
            verify_email("not-a-real-token")

    def test_already_used_token_cannot_be_reused(self):
        token = create_email_verification_token(self.user)
        verify_email(token.token)

        with self.assertRaises(ValidationError):
            verify_email(token.token)

    def test_expired_token_raises(self):
        token = create_email_verification_token(self.user)
        token.expires_at = timezone.now() - timedelta(minutes=1)
        token.save(update_fields=["expires_at"])

        with self.assertRaises(ValidationError):
            verify_email(token.token)

    def test_requesting_a_new_token_invalidates_the_previous_one(self):
        first_token = create_email_verification_token(self.user)
        second_token = create_email_verification_token(self.user)

        first_token.refresh_from_db()
        self.assertIsNotNone(first_token.used_at)
        self.assertTrue(second_token.is_valid())

    def test_send_verification_email_failure_does_not_raise(self):
        token = create_email_verification_token(self.user)

        with patch(
            "accounts.services.send_mail",
            side_effect=Exception("SMTP down"),
        ):
            send_verification_email(self.user, token)  # should not raise



@override_settings(SEND_EMAIL_IN_BACKGROUND=False)
class PasswordResetTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="OldPassword123!",
        )

    def _request_code(self, email="reset@example.com"):
        with self.captureOnCommitCallbacks(execute=True):
            request_password_reset(email)

        return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)

    def _wrong_code(self, code):
        return f"{(int(code) + 1) % 10**6:06d}"

    def test_request_emails_a_six_digit_code(self):
        code = self._request_code()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(len(code), 6)

        reset = PasswordResetToken.objects.get(user=self.user)
        self.assertNotEqual(reset.code_hash, code)  # stored hashed

    def test_request_is_case_insensitive_on_email(self):
        self._request_code(email="RESET@Example.com")

        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_request_for_unknown_email_is_silent(self):
        with self.captureOnCommitCallbacks(execute=True):
            result = request_password_reset("nobody@example.com")

        self.assertIsNone(result)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(PasswordResetToken.objects.exists())

    def test_full_flow_resets_password(self):
        code = self._request_code()
        reset_token = verify_password_reset_code(self.user.email, code)

        with self.captureOnCommitCallbacks(execute=True):
            reset_password(reset_token, "BrandNewPass456!")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPass456!"))
        self.assertTrue(self.user.email_verified)
        self.assertIn("password was changed", mail.outbox[-1].subject)

    def test_reset_revokes_existing_refresh_tokens(self):
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.tokens import RefreshToken

        old_refresh = RefreshToken.for_user(self.user)

        code = self._request_code()
        reset_token = verify_password_reset_code(self.user.email, code)
        reset_password(reset_token, "BrandNewPass456!")

        with self.assertRaises(TokenError):
            RefreshToken(str(old_refresh)).check_blacklist()

    def test_wrong_code_raises_and_counts_attempt(self):
        code = self._request_code()

        with self.assertRaises(ValidationError):
            verify_password_reset_code(self.user.email, self._wrong_code(code))

        reset = PasswordResetToken.objects.get(user=self.user)
        self.assertEqual(reset.attempts, 1)

    def test_code_locks_after_max_attempts(self):
        code = self._request_code()

        for _ in range(PASSWORD_RESET_MAX_ATTEMPTS):
            with self.assertRaises(ValidationError):
                verify_password_reset_code(
                    self.user.email, self._wrong_code(code)
                )

        # Even the correct code no longer works.
        with self.assertRaises(ValidationError):
            verify_password_reset_code(self.user.email, code)

    def test_expired_code_raises(self):
        code = self._request_code()
        PasswordResetToken.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )

        with self.assertRaises(ValidationError):
            verify_password_reset_code(self.user.email, code)

    def test_new_request_invalidates_previous_code(self):
        first_code = self._request_code()
        second_code = self._request_code()

        if first_code != second_code:
            with self.assertRaises(ValidationError):
                verify_password_reset_code(self.user.email, first_code)

        self.assertTrue(
            verify_password_reset_code(self.user.email, second_code)
        )

    def test_code_cannot_be_verified_twice(self):
        code = self._request_code()
        verify_password_reset_code(self.user.email, code)

        with self.assertRaises(ValidationError):
            verify_password_reset_code(self.user.email, code)

    def test_reset_token_is_single_use(self):
        code = self._request_code()
        reset_token = verify_password_reset_code(self.user.email, code)
        reset_password(reset_token, "BrandNewPass456!")

        with self.assertRaises(ValidationError):
            reset_password(reset_token, "AnotherPass789!")

    def test_expired_reset_token_raises(self):
        code = self._request_code()
        reset_token = verify_password_reset_code(self.user.email, code)
        PasswordResetToken.objects.filter(user=self.user).update(
            verified_at=timezone.now() - timedelta(hours=1)
        )

        with self.assertRaises(ValidationError):
            reset_password(reset_token, "BrandNewPass456!")

    def test_weak_new_password_is_rejected(self):
        code = self._request_code()
        reset_token = verify_password_reset_code(self.user.email, code)

        with self.assertRaises(ValidationError):
            reset_password(reset_token, "12345678")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPassword123!"))

        # A rejected password doesn't burn the token.
        reset_password(reset_token, "BrandNewPass456!")


class RolePermissionTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

        self.customer = User.objects.create_user(
            username="testcustomer",
            email="customer@test.com",
            password="TestPassword123!",
            full_name="Test Customer",
            role=User.Role.CUSTOMER,
        )

        self.artisan = User.objects.create_user(
            username="testartisan",
            email="artisan@test.com",
            password="TestPassword123!",
            full_name="Test Artisan",
            role=User.Role.ARTISAN,
        )

        self.admin = User.objects.create_user(
            username="testadmin",
            email="admin@test.com",
            password="TestPassword123!",
            full_name="Test Admin",
            role=User.Role.ADMIN,
        )

        Customer.objects.create(user=self.customer)
        Artisan.objects.create(user=self.artisan, phone_number="08000000000")

    def test_role_without_profile_is_denied(self):
        orphan = User.objects.create_user(
            username="noprofile",
            email="noprofile@test.com",
            password="TestPassword123!",
            role=User.Role.CUSTOMER,
        )
        request = self.factory.get("/")
        request.user = orphan

        self.assertFalse(IsCustomer().has_permission(request, None))

    def test_customer_permission(self):
        request = self.factory.get("/")
        request.user = self.customer

        permission = IsCustomer()

        self.assertTrue(
            permission.has_permission(request, None)
        )

    def test_artisan_permission(self):
        request = self.factory.get("/")
        request.user = self.artisan

        permission = IsArtisan()

        self.assertTrue(
            permission.has_permission(request, None)
        )

    def test_admin_permission(self):
        request = self.factory.get("/")
        request.user = self.admin

        permission = IsAdmin()

        self.assertTrue(
            permission.has_permission(request, None)
        )

    def test_customer_cannot_use_artisan_permission(self):
        request = self.factory.get("/")
        request.user = self.customer

        permission = IsArtisan()

        self.assertFalse(
            permission.has_permission(request, None)
        )

    def test_artisan_cannot_use_admin_permission(self):
        request = self.factory.get("/")
        request.user = self.artisan

        permission = IsAdmin()

        self.assertFalse(
            permission.has_permission(request, None)
        )

    def test_admin_cannot_use_customer_permission(self):
        request = self.factory.get("/")
        request.user = self.admin

        permission = IsCustomer()

        self.assertFalse(
            permission.has_permission(request, None)
        )


class AccountIntegrityTests(TestCase):

    def test_createsuperuser_gets_admin_role(self):
        admin = User.objects.create_superuser(
            username="boss",
            email="boss@example.com",
            password="testpassword123",
        )

        self.assertEqual(admin.role, User.Role.ADMIN)

    def test_email_is_stored_lowercase_from_any_path(self):
        user = User.objects.create_user(
            username="mixedcase",
            email="  Mixed.Case@Example.COM ",
            password="testpassword123",
        )

        self.assertEqual(user.email, "mixed.case@example.com")

    def test_registration_rejects_password_like_username(self):
        from .serializers import CustomerRegisterSerializer

        serializer = CustomerRegisterSerializer(data={
            "username": "stephen123x",
            "email": "stephen@example.com",
            "full_name": "Stephen",
            "password": "stephen123x",
            "phone_number": "08000000000",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_registration_rejects_inactive_service(self):
        from .serializers import ArtisanRegisterSerializer

        inactive = Service.objects.create(
            name="Old Service",
            description="No longer offered",
            minimum_price=1000,
            maximum_price=2000,
            is_active=False,
        )
        serializer = ArtisanRegisterSerializer(data={
            "username": "newartisan",
            "email": "newartisan@example.com",
            "full_name": "New Artisan",
            "password": "StrongPass123!",
            "phone_number": "08000000000",
            "services": [inactive.id],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("services", serializer.errors)

    def test_deactivated_user_cannot_finish_password_reset(self):
        user = User.objects.create_user(
            username="leaver",
            email="leaver@example.com",
            password="OldPassword123!",
        )
        with self.settings(SEND_EMAIL_IN_BACKGROUND=False):
            with self.captureOnCommitCallbacks(execute=True):
                request_password_reset(user.email)
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)
        reset_token = verify_password_reset_code(user.email, code)

        user.is_active = False
        user.save(update_fields=["is_active"])

        with self.assertRaises(ValidationError):
            reset_password(reset_token, "BrandNewPass456!")


class UsernameAndAdminTests(TestCase):

    def test_registration_rejects_username_differing_only_in_case(self):
        from .serializers import CustomerRegisterSerializer

        User.objects.create_user(
            username="TakenName",
            email="taken@example.com",
            password="testpassword123",
        )
        serializer = CustomerRegisterSerializer(data={
            "username": "takenname",
            "email": "other@example.com",
            "full_name": "Someone Else",
            "password": "StrongPass123!",
            "phone_number": "08000000000",
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)

    def test_model_validation_rejects_email_differing_only_in_case(self):
        User.objects.create_user(
            username="first",
            email="taken@example.com",
            password="testpassword123",
        )
        duplicate = User(username="second", email="TAKEN@Example.com")
        duplicate.set_password("testpassword123")

        with self.assertRaises(ValidationError) as caught:
            duplicate.full_clean()
        self.assertIn("email", caught.exception.message_dict)

    def test_admin_add_form_only_creates_admins(self):
        from django.contrib.admin.sites import site
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.user = User.objects.create_superuser(
            username="boss", email="boss@example.com", password="testpassword123"
        )
        form = site._registry[User].get_form(request, obj=None)

        self.assertEqual(
            [value for value, _ in form.base_fields["role"].choices],
            [User.Role.ADMIN],
        )
        self.assertIn("full_name", form.base_fields)
        self.assertIn("email_verified", form.base_fields)

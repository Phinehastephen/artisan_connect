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

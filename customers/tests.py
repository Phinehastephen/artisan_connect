from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from .models import Customer
from .serializers import CustomerProfileUpdateSerializer
from .services import update_customer_profile


class CustomerProfileUpdateTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="customer1",
            email="customer1@example.com",
            password="testpassword123",
            full_name="Old Name",
        )
        self.customer = Customer.objects.create(
            user=self.user,
            phone_number="08011111111",
        )

        User.objects.create_user(
            username="TakenName",
            email="taken@example.com",
            password="testpassword123",
        )

    def test_customer_can_update_profile_fields(self):
        update_customer_profile(
            self.customer,
            {
                "username": "newname",
                "full_name": "New Name",
                "profile_picture": "pics/me.png",
                "default_location": "Yaba, Lagos",
            },
        )

        self.user.refresh_from_db()
        self.customer.refresh_from_db()
        self.assertEqual(self.user.username, "newname")
        self.assertEqual(self.user.full_name, "New Name")
        self.assertEqual(self.user.profile_picture, "pics/me.png")
        self.assertEqual(self.customer.default_location, "Yaba, Lagos")

    def test_no_cooldown_for_customers(self):
        update_customer_profile(self.customer, {"full_name": "First Change"})
        update_customer_profile(self.customer, {"full_name": "Second Change"})

        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Second Change")

    def test_username_must_be_unique_ignoring_case(self):
        with self.assertRaises(ValidationError):
            update_customer_profile(self.customer, {"username": "takenname"})

    def test_keeping_own_username_is_allowed(self):
        update_customer_profile(self.customer, {"username": "Customer1"})

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "Customer1")

    def test_phone_and_email_cannot_be_changed(self):
        serializer = CustomerProfileUpdateSerializer(
            data={"phone_number": "0809", "email": "new@example.com"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("phone_number", serializer.errors)
        self.assertIn("email", serializer.errors)

    def test_empty_update_is_rejected(self):
        serializer = CustomerProfileUpdateSerializer(data={})

        self.assertFalse(serializer.is_valid())

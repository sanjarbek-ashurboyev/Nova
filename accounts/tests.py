from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.phone import mask_phone, normalize_phone

User = get_user_model()


class PhoneHelpersTest(TestCase):
    def test_normalize_adds_country_code_to_nine_digits(self):
        self.assertEqual(normalize_phone('901234567'), '+998901234567')

    def test_normalize_strips_formatting(self):
        self.assertEqual(normalize_phone('+998 90 123 45 67'), '+998901234567')

    def test_normalize_rejects_wrong_length(self):
        with self.assertRaises(ValidationError):
            normalize_phone('12345')

    def test_normalize_rejects_foreign_country_code(self):
        with self.assertRaises(ValidationError):
            normalize_phone('+1 202 555 0111')

    def test_mask_hides_the_middle_digits(self):
        self.assertEqual(mask_phone('+998901234567'), '+998 90 *** ** 67')

    def test_mask_returns_empty_for_invalid_input(self):
        self.assertEqual(mask_phone('nonsense'), '')
        self.assertEqual(mask_phone(None), '')


class UserModelTest(TestCase):
    def test_create_user_hashes_the_password(self):
        user = User.objects.create_user(phone='+998901234567', password='secret-pw')
        self.assertNotEqual(user.password, 'secret-pw')
        self.assertTrue(user.check_password('secret-pw'))

    def test_create_user_requires_a_phone(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(phone='', password='secret-pw')

    def test_api_key_is_generated_once_and_kept_stable(self):
        user = User.objects.create_user(phone='+998901234567', password='secret-pw')
        self.assertEqual(len(user.api_key), 32)

        original = user.api_key
        user.first_name = 'Renamed'
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.api_key, original)

    def test_api_keys_are_unique_across_users(self):
        first = User.objects.create_user(phone='+998901234567', password='pw')
        second = User.objects.create_user(phone='+998907654321', password='pw')
        self.assertNotEqual(first.api_key, second.api_key)

    def test_superuser_gets_staff_and_superuser_flags(self):
        admin = User.objects.create_superuser(phone='+998900000000', password='pw')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_display_name_falls_back_to_masked_phone(self):
        user = User.objects.create_user(phone='+998901234567', password='pw')
        self.assertEqual(user.display_name, '+998 90 *** ** 67')

        user.first_name, user.last_name = 'Shohruh', 'Anvarov'
        self.assertEqual(user.display_name, 'Shohruh Anvarov')

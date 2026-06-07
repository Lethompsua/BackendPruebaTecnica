from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from cryptography.fernet import Fernet
from users.models import User
from .models import PaymentMethod
from .encryption import encrypt, decrypt, hash_identifier, luhn_check

TEST_KEY = Fernet.generate_key().decode()


@override_settings(ENCRYPTION_KEY=TEST_KEY)
class EncryptionTests(TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        original = '4111111111111111'
        encrypted = encrypt(original)
        self.assertNotEqual(encrypted, original)
        self.assertEqual(decrypt(encrypted), original)

    def test_hash_is_deterministic(self):
        self.assertEqual(hash_identifier('abc'), hash_identifier('abc'))

    def test_hash_differs_for_different_values(self):
        self.assertNotEqual(hash_identifier('abc'), hash_identifier('def'))

    def test_luhn_valid_card(self):
        self.assertTrue(luhn_check('4111111111111111'))   # Visa test number
        self.assertTrue(luhn_check('5500005555555559'))   # Mastercard test

    def test_luhn_invalid_card(self):
        self.assertFalse(luhn_check('1234567890123456'))


@override_settings(ENCRYPTION_KEY=TEST_KEY)
class PaymentMethodCRUDTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='owner@example.com', first_name='Owner',
            last_name='User', password='SecurePass123!'
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

        self.other_user = User.objects.create_user(
            email='other@example.com', first_name='Other',
            last_name='User', password='SecurePass123!'
        )

        self.base_url = '/api/v1/payment-methods/'
        self.valid_card = {
            'type': 'CARD',
            'alias': 'Mi Visa',
            'institution': 'Banamex',
            'currency': 'MXN',
            'identifier': '4111111111111111',
        }
        self.valid_clabe = {
            'type': 'CLABE',
            'alias': 'Mi cuenta BBVA',
            'institution': 'BBVA',
            'currency': 'MXN',
            'identifier': '012180001112345678',
        }

    def test_create_card_success(self):
        response = self.client.post(self.base_url, self.valid_card, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('identifier_masked', response.data)
        self.assertEqual(response.data['identifier_masked'], '****1111')
        self.assertNotIn('identifier', response.data)

    def test_create_clabe_success(self):
        response = self.client.post(self.base_url, self.valid_clabe, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['identifier_masked'], '****5678')

    def test_create_duplicate_rejected(self):
        self.client.post(self.base_url, self.valid_card, format='json')
        response = self.client.post(self.base_url, self.valid_card, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_luhn(self):
        data = {**self.valid_card, 'identifier': '4111111111111112'}
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_clabe_length(self):
        data = {**self.valid_clabe, 'identifier': '12345'}
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_own_methods(self):
        self.client.post(self.base_url, self.valid_card, format='json')
        # Create one for other user directly
        PaymentMethod.objects.create(
            user=self.other_user,
            type='CARD', alias='Other card', institution='HSBC',
            currency='MXN', identifier_encrypted=encrypt('5555555555554444'),
            identifier_last4='4444', identifier_hash=hash_identifier('5555555555554444'),
        )
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_detail_not_found_for_other_user(self):
        pm = PaymentMethod.objects.create(
            user=self.other_user,
            type='CARD', alias='Other card', institution='HSBC',
            currency='MXN', identifier_encrypted=encrypt('5555555555554444'),
            identifier_last4='4444', identifier_hash=hash_identifier('5555555555554444'),
        )
        response = self.client.get(f'{self.base_url}{pm.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_delete(self):
        res = self.client.post(self.base_url, self.valid_card, format='json')
        pm_id = res.data['id']
        response = self.client.delete(f'{self.base_url}{pm_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Record still exists in DB but is hidden
        pm = PaymentMethod.objects.get(id=pm_id)
        self.assertTrue(pm.is_deleted)
        self.assertIsNotNone(pm.deleted_at)

    def test_deleted_method_not_in_list(self):
        res = self.client.post(self.base_url, self.valid_card, format='json')
        pm_id = res.data['id']
        self.client.delete(f'{self.base_url}{pm_id}/')
        list_response = self.client.get(self.base_url)
        self.assertEqual(list_response.data['count'], 0)

    def test_deactivate(self):
        res = self.client.post(self.base_url, self.valid_card, format='json')
        pm_id = res.data['id']
        response = self.client.patch(f'{self.base_url}{pm_id}/deactivate/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'INACTIVE')

    def test_update_alias(self):
        res = self.client.post(self.base_url, self.valid_card, format='json')
        pm_id = res.data['id']
        response = self.client.patch(f'{self.base_url}{pm_id}/', {'alias': 'Nueva Visa'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['alias'], 'Nueva Visa')

    def test_requires_authentication(self):
        unauthenticated_client = APIClient()
        response = unauthenticated_client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_filter_by_type(self):
        self.client.post(self.base_url, self.valid_card, format='json')
        self.client.post(self.base_url, self.valid_clabe, format='json')
        response = self.client.get(self.base_url, {'type': 'CARD'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['type'], 'CARD')

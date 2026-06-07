from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from cryptography.fernet import Fernet
from .models import User

TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class UserRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/v1/auth/register/'
        self.valid_data = {
            'email': 'test@example.com',
            'first_name': 'Ana',
            'last_name': 'García',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }

    def test_register_success(self):
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], 'test@example.com')

    def test_register_duplicate_email(self):
        User.objects.create_user(
            email='test@example.com', first_name='Ana',
            last_name='García', password='Pass123!'
        )
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        data = {**self.valid_data, 'password_confirm': 'different'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password(self):
        data = {**self.valid_data, 'password': '123', 'password_confirm': '123'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        response = self.client.post(self.url, {'email': 'test@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class UserAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com', first_name='Juan',
            last_name='López', password='SecurePass123!'
        )

    def test_login_success(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'user@example.com',
            'password': 'SecurePass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)

    def test_login_invalid_credentials(self):
        response = self.client.post('/api/v1/auth/login/', {
            'email': 'user@example.com',
            'password': 'wrongpassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_requires_auth(self):
        response = self.client.get('/api/v1/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_authenticated(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        response = self.client.get('/api/v1/auth/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'user@example.com')

    def test_logout_blacklists_token(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        response = self.client.post('/api/v1/auth/logout/', {'refresh': str(refresh)}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh token should now be blacklisted
        response2 = self.client.post('/api/v1/auth/token/refresh/', {'refresh': str(refresh)}, format='json')
        self.assertEqual(response2.status_code, status.HTTP_401_UNAUTHORIZED)

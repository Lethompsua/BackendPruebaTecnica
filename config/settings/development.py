from .base import *
from cryptography.fernet import Fernet

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Auto-generate encryption key in development if not set
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    import warnings
    warnings.warn(
        'ENCRYPTION_KEY not set in .env — using a temporary key. '
        'Encrypted data will be lost on restart. Set ENCRYPTION_KEY for persistence.',
        stacklevel=2
    )

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
]

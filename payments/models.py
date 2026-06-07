from django.db import models
from django.conf import settings
from django.utils import timezone


class PaymentMethod(models.Model):
    class Type(models.TextChoices):
        CARD = 'CARD', 'Tarjeta'
        BANK_ACCOUNT = 'BANK_ACCOUNT', 'Cuenta Bancaria'
        CLABE = 'CLABE', 'CLABE'
        OTHER = 'OTHER', 'Otro'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Activo'
        INACTIVE = 'INACTIVE', 'Inactivo'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods',
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    alias = models.CharField(max_length=100)
    institution = models.CharField(max_length=100)
    currency = models.CharField(max_length=3, default='MXN')

    # identifier_encrypted: sensitive data stored with Fernet encryption
    # identifier_last4: last 4 chars in clear for safe display
    # identifier_hash: SHA-256 of the original value for duplicate detection
    identifier_encrypted = models.TextField()
    identifier_last4 = models.CharField(max_length=4)
    identifier_hash = models.CharField(max_length=64)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    # Soft delete — physical rows are never removed
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_methods'
        ordering = ['-created_at']
        # Prevent adding the same identifier twice for the same user (only among active records)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'identifier_hash'],
                condition=models.Q(is_deleted=False),
                name='unique_active_identifier_per_user',
            )
        ]
        verbose_name = 'Método de Pago'
        verbose_name_plural = 'Métodos de Pago'

    def __str__(self):
        return f'{self.get_type_display()} — {self.alias} ({self.user.email})'

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])

    def deactivate(self):
        self.status = self.Status.INACTIVE
        self.save(update_fields=['status', 'updated_at'])

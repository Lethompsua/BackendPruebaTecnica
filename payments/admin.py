from django.contrib import admin
from .models import PaymentMethod


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['alias', 'type', 'institution', 'currency', 'masked_identifier', 'status', 'is_deleted', 'user', 'created_at']
    list_filter = ['type', 'status', 'currency', 'is_deleted']
    search_fields = ['alias', 'institution', 'user__email']
    readonly_fields = ['identifier_encrypted', 'identifier_hash', 'identifier_last4', 'created_at', 'updated_at', 'deleted_at']
    ordering = ['-created_at']

    def masked_identifier(self, obj):
        return f'****{obj.identifier_last4}'
    masked_identifier.short_description = 'Identificador'

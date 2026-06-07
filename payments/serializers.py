from rest_framework import serializers
from .models import PaymentMethod
from .encryption import encrypt, hash_identifier, luhn_check


class PaymentMethodCreateSerializer(serializers.ModelSerializer):
    identifier = serializers.CharField(
        write_only=True,
        help_text='Número de tarjeta, CLABE o identificador del método de pago.',
    )

    class Meta:
        model = PaymentMethod
        fields = ['id', 'type', 'alias', 'institution', 'currency', 'identifier']

    def validate_identifier(self, value: str) -> str:
        return value.strip().replace(' ', '').replace('-', '')

    def validate(self, attrs):
        identifier = attrs.get('identifier', '')
        payment_type = attrs.get('type', '')

        if payment_type == PaymentMethod.Type.CLABE:
            if not identifier.isdigit() or len(identifier) != 18:
                raise serializers.ValidationError(
                    {'identifier': 'La CLABE debe tener exactamente 18 dígitos numéricos.'}
                )
        elif payment_type == PaymentMethod.Type.CARD:
            if not identifier.isdigit() or not (13 <= len(identifier) <= 19):
                raise serializers.ValidationError(
                    {'identifier': 'El número de tarjeta debe tener entre 13 y 19 dígitos numéricos.'}
                )
            if not luhn_check(identifier):
                raise serializers.ValidationError(
                    {'identifier': 'El número de tarjeta no es válido (falla el algoritmo de Luhn).'}
                )
        elif payment_type == PaymentMethod.Type.BANK_ACCOUNT:
            if not identifier.isdigit() or len(identifier) < 10:
                raise serializers.ValidationError(
                    {'identifier': 'El número de cuenta debe contener al menos 10 dígitos.'}
                )

        return attrs

    def create(self, validated_data):
        identifier = validated_data.pop('identifier')
        user = self.context['request'].user
        identifier_hash = hash_identifier(identifier)

        if PaymentMethod.objects.filter(
            user=user, identifier_hash=identifier_hash, is_deleted=False
        ).exists():
            raise serializers.ValidationError(
                {'identifier': 'Ya tienes un método de pago registrado con este identificador.'}
            )

        return PaymentMethod.objects.create(
            user=user,
            identifier_encrypted=encrypt(identifier),
            identifier_last4=identifier[-4:],
            identifier_hash=identifier_hash,
            **validated_data,
        )


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Read serializer — never exposes the raw identifier."""
    identifier_masked = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'type', 'type_display', 'alias', 'institution', 'currency',
            'identifier_masked', 'status', 'status_display', 'created_at', 'updated_at',
        ]

    def get_identifier_masked(self, obj: PaymentMethod) -> str:
        return f'****{obj.identifier_last4}'


class PaymentMethodUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['alias', 'institution', 'currency', 'status']

    def validate_status(self, value):
        # Reactivation via this endpoint is allowed only if the record was inactive
        # (not deleted). Deletion is a separate operation.
        return value

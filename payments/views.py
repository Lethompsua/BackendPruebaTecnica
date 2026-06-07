from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from audit.utils import log_action
from .models import PaymentMethod
from .serializers import (
    PaymentMethodCreateSerializer,
    PaymentMethodSerializer,
    PaymentMethodUpdateSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class PaymentMethodListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = PaymentMethod.objects.filter(user=request.user, is_deleted=False)

        # Optional filters
        if payment_type := request.query_params.get('type'):
            qs = qs.filter(type=payment_type)
        if status_filter := request.query_params.get('status'):
            qs = qs.filter(status=status_filter)
        if search := request.query_params.get('search'):
            qs = qs.filter(alias__icontains=search) | qs.filter(institution__icontains=search)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = PaymentMethodSerializer(page, many=True)
        log_action(
            user=request.user, action='READ', request=request,
            resource_type='PaymentMethod', metadata={'total': qs.count()},
        )
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = PaymentMethodCreateSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            pm = serializer.save()
            log_action(
                user=request.user, action='CREATE', request=request,
                resource_type='PaymentMethod', resource_id=str(pm.id),
                metadata={'type': pm.type, 'alias': pm.alias},
            )
            return Response(PaymentMethodSerializer(pm).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentMethodDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, pk: int, user):
        try:
            return PaymentMethod.objects.get(pk=pk, user=user, is_deleted=False)
        except PaymentMethod.DoesNotExist:
            return None

    def get(self, request, pk: int):
        pm = self._get_object(pk, request.user)
        if not pm:
            return Response({'detail': 'Método de pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        log_action(
            user=request.user, action='READ', request=request,
            resource_type='PaymentMethod', resource_id=str(pk),
        )
        return Response(PaymentMethodSerializer(pm).data)

    def patch(self, request, pk: int):
        pm = self._get_object(pk, request.user)
        if not pm:
            return Response({'detail': 'Método de pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentMethodUpdateSerializer(pm, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            log_action(
                user=request.user, action='UPDATE', request=request,
                resource_type='PaymentMethod', resource_id=str(pk),
                metadata={'fields': list(request.data.keys())},
            )
            return Response(PaymentMethodSerializer(pm).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk: int):
        pm = self._get_object(pk, request.user)
        if not pm:
            return Response({'detail': 'Método de pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        pm.soft_delete()
        log_action(
            user=request.user, action='DELETE', request=request,
            resource_type='PaymentMethod', resource_id=str(pk),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentMethodDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int):
        try:
            pm = PaymentMethod.objects.get(pk=pk, user=request.user, is_deleted=False)
        except PaymentMethod.DoesNotExist:
            return Response({'detail': 'Método de pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if pm.status == PaymentMethod.Status.INACTIVE:
            return Response(
                {'detail': 'El método de pago ya está inactivo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pm.deactivate()
        log_action(
            user=request.user, action='DEACTIVATE', request=request,
            resource_type='PaymentMethod', resource_id=str(pk),
        )
        return Response(PaymentMethodSerializer(pm).data)


class PaymentMethodReactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk: int):
        try:
            pm = PaymentMethod.objects.get(pk=pk, user=request.user, is_deleted=False)
        except PaymentMethod.DoesNotExist:
            return Response({'detail': 'Método de pago no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if pm.status == PaymentMethod.Status.ACTIVE:
            return Response(
                {'detail': 'El método de pago ya está activo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pm.status = PaymentMethod.Status.ACTIVE
        pm.save(update_fields=['status', 'updated_at'])
        log_action(
            user=request.user, action='UPDATE', request=request,
            resource_type='PaymentMethod', resource_id=str(pk),
            metadata={'action': 'reactivate'},
        )
        return Response(PaymentMethodSerializer(pm).data)

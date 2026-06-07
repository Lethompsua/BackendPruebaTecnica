from django.urls import path
from .views import (
    PaymentMethodListCreateView,
    PaymentMethodDetailView,
    PaymentMethodDeactivateView,
    PaymentMethodReactivateView,
)

urlpatterns = [
    path('', PaymentMethodListCreateView.as_view(), name='payment-method-list'),
    path('<int:pk>/', PaymentMethodDetailView.as_view(), name='payment-method-detail'),
    path('<int:pk>/deactivate/', PaymentMethodDeactivateView.as_view(), name='payment-method-deactivate'),
    path('<int:pk>/reactivate/', PaymentMethodReactivateView.as_view(), name='payment-method-reactivate'),
]

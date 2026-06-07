from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.exceptions import TokenError

from audit.utils import log_action
from .serializers import RegisterSerializer, UserProfileSerializer, CustomTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'anon'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            log_action(
                user=user, action='REGISTER', request=request,
                resource_type='User', resource_id=str(user.id)
            )
            return Response({
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                },
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(email=request.data.get('email'))
                log_action(
                    user=user, action='LOGIN', request=request,
                    resource_type='User', resource_id=str(user.id)
                )
            except User.DoesNotExist:
                pass
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'El refresh token es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            log_action(
                user=request.user, action='LOGOUT', request=request,
                resource_type='User', resource_id=str(request.user.id)
            )
            return Response({'detail': 'Sesión cerrada correctamente.'})
        except TokenError:
            return Response(
                {'detail': 'Token inválido o expirado.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            log_action(
                user=request.user, action='UPDATE', request=request,
                resource_type='User', resource_id=str(request.user.id),
                metadata={'fields': list(request.data.keys())}
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

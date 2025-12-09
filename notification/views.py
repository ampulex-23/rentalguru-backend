import logging
import os

from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView

from RentalGuru import settings
from .models import Notification, FCMToken
from .permissions import IsAdminOrOwner, IsAdmin
from .serializers import NotificationSerializer, FCMTokenSerializer


@extend_schema(summary="Уведомления", description="CRUD уведомлений")
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsAdminOrOwner]
        elif self.action in ['create', 'update', 'partial_update']:
            self.permission_classes = [IsAuthenticated, IsAdmin]
        return super().get_permissions()

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related('user').order_by('-created_at')

    @action(detail=True, methods=['get'])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.read_it = True
        notification.save()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)


@extend_schema(summary="FCM токен (тест)", description="Тестовая страница FCM токена")
def get_fcm_token(request):
    return render(request, 'test_push.html')


@extend_schema(
    summary="Регистрация FCM токена",
    description="""
    Регистрация FCM токена для push-уведомлений.
    
    device_type:
    - 'android' - Android устройство
    - 'ios' - iOS устройство  
    - 'web' - Web браузер
    
    Токен автоматически привязывается к текущему пользователю.
    При повторной регистрации того же токена - обновляется привязка к пользователю.
    """
)
class FCMTokenRegisterView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = FCMTokenSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'FCM token registered successfully'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Удаление FCM токена (при выходе из приложения)"""
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted, _ = FCMToken.objects.filter(token=token, user=request.user).delete()
        if deleted:
            return Response(
                {'message': 'FCM token deleted successfully'},
                status=status.HTTP_200_OK
            )
        return Response(
            {'error': 'Token not found'},
            status=status.HTTP_404_NOT_FOUND
        )


logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@cache_control(max_age=0, must_revalidate=True)
def firebase_messaging_sw(request):
    """
    Обслуживание Service Worker для Firebase
    """
    try:
        possible_paths = [
            os.path.join(settings.STATIC_ROOT, 'firebase-messaging-sw.js'),
            os.path.join(settings.BASE_DIR, 'static', 'firebase-messaging-sw.js'),
            os.path.join(settings.BASE_DIR, 'staticfiles', 'firebase-messaging-sw.js'),
        ]

        sw_path = None
        for path in possible_paths:
            if os.path.exists(path):
                sw_path = path
                break

        if sw_path:
            logger.info(f"Service Worker найден по пути: {sw_path}")

            with open(sw_path, 'rb') as f:
                content = f.read()

            response = HttpResponse(content, content_type='application/javascript')

            response['Service-Worker-Allowed'] = '/'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

            if hasattr(settings, 'CORS_ALLOW_ALL_ORIGINS') and settings.CORS_ALLOW_ALL_ORIGINS:
                response['Access-Control-Allow-Origin'] = '*'

            return response
        else:
            logger.error(f"Service Worker не найден. Проверенные пути: {possible_paths}")

            fallback_sw = """
// Fallback Service Worker
console.log('Fallback Service Worker загружен');

self.addEventListener('install', function(event) {
    console.log('Fallback Service Worker установлен');
    event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', function(event) {
    console.log('Fallback Service Worker активирован');
    event.waitUntil(self.clients.claim());
});
"""
            response = HttpResponse(fallback_sw, content_type='application/javascript')
            response['Service-Worker-Allowed'] = '/'
            response['Cache-Control'] = 'no-cache'
            return response

    except Exception as e:
        logger.error(f"Ошибка при обслуживании Service Worker: {str(e)}")

        error_sw = f"""
// Error Service Worker
console.error('Ошибка загрузки Service Worker: {str(e)}');

self.addEventListener('install', function(event) {{
    console.log('Error Service Worker установлен');
    event.waitUntil(self.skipWaiting());
}});

self.addEventListener('activate', function(event) {{
    console.log('Error Service Worker активирован');
    event.waitUntil(self.clients.claim());
}});
"""
        response = HttpResponse(error_sw, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        response['Cache-Control'] = 'no-cache'
        return response

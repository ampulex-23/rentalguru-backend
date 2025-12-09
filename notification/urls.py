from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, get_fcm_token, FCMTokenRegisterView

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('', include(router.urls)),
    path('fcm_token/', get_fcm_token, name='fcm_token'),
    path('fcm/register/', FCMTokenRegisterView.as_view(), name='fcm_register'),
]

from rest_framework import serializers
from .models import Notification, FCMToken


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'content', 'read_it', 'url', 'created_at']
        read_only_fields = ['user', 'read_it', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        notification = Notification.objects.create(user=request.user, **validated_data)
        notification.send_notification()
        return notification


class FCMTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMToken
        fields = ['id', 'token', 'device_type', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_active', 'created_at']

    def create(self, validated_data):
        user = self.context['request'].user
        token = validated_data['token']
        device_type = validated_data.get('device_type', 'android')
        
        # Обновляем существующий токен или создаём новый
        fcm_token, created = FCMToken.objects.update_or_create(
            token=token,
            defaults={
                'user': user,
                'device_type': device_type,
                'is_active': True
            }
        )
        return fcm_token

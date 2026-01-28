from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html

from feedback.models import FeedbackRenter
from .models import User, Lessor, Renter, Currency, Language, RenterDocuments, LessorWithdrawRequest


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'email', 'first_name', 'last_name', 'role', 'date_of_birth',
        'telephone', 'currency', 'avatar', 'get_influencer_code'
    )
    list_filter = ('role',)

    @admin.display(description='Номер реферала')
    def get_influencer_code(self, obj):
        if hasattr(obj, 'lessor') and obj.lessor.influencer:
            return obj.lessor.influencer.id
        elif hasattr(obj, 'renter') and obj.renter.influencer:
            return obj.renter.influencer.id
        return '-'


class BaseUserAdminForm(forms.ModelForm):
    user_first_name = forms.CharField(label='Имя', required=False)
    user_last_name = forms.CharField(label='Фамилия', required=False)
    user_date_of_birth = forms.DateField(label='Дата рождения', required=False)
    user_telephone = forms.CharField(label='Телефон', required=False)
    user_currency = forms.ModelChoiceField(
        queryset=Currency.objects.all(),
        label='Валюта',
        required=False
    )
    user_avatar = forms.ImageField(label='Аватар', required=False)
    user_about = forms.CharField(
        label='О себе',
        widget=forms.Textarea,
        required=False
    )
    user_email_notification = forms.BooleanField(
        label='Email уведомления',
        required=False
    )
    user_push_notification = forms.BooleanField(
        label='Push уведомления',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['user_first_name'].initial = self.instance.user.first_name
            self.fields['user_last_name'].initial = self.instance.user.last_name
            self.fields['user_date_of_birth'].initial = self.instance.user.date_of_birth
            self.fields['user_telephone'].initial = self.instance.user.telephone
            self.fields['user_currency'].initial = self.instance.user.currency
            self.fields['user_avatar'].initial = self.instance.user.avatar
            self.fields['user_about'].initial = self.instance.user.about
            self.fields['user_email_notification'].initial = self.instance.user.email_notification
            self.fields['user_push_notification'].initial = self.instance.user.push_notification


class LessorAdminForm(BaseUserAdminForm):
    class Meta:
        model = Lessor
        fields = '__all__'


class RenterAdminForm(BaseUserAdminForm):
    class Meta:
        model = Renter
        fields = '__all__'


class BaseUserRelatedAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if form.cleaned_data:
            user = obj.user
            user_fields = [
                'first_name', 'last_name', 'date_of_birth', 'telephone',
                'currency', 'avatar', 'about', 'email_notification',
                'push_notification'
            ]

            changed = False
            for field in user_fields:
                field_key = f'user_{field}'
                if field_key in form.cleaned_data:
                    value = form.cleaned_data[field_key]
                    if value != getattr(user, field):
                        setattr(user, field, value)
                        changed = True

            if changed:
                try:
                    user.save()
                    messages.success(request, 'Информация пользователя успешно обновлена')
                except Exception as e:
                    messages.error(request, f'Ошибка при обновлении информации пользователя: {str(e)}')

        super().save_model(request, obj, form, change)


class LessorAdmin(BaseUserRelatedAdmin):
    form = LessorAdminForm
    list_display = ('user', 'super_host', 'count_trip', 'average_response_time', 'commission')
    list_filter = ('super_host',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email')

    fieldsets = [
        ('Основная информация', {
            'fields': ('user', 'super_host', 'count_trip', 'average_response_time', 'commission')
        }),
        ('Информация о пользователе', {
            'fields': (
                'user_first_name', 'user_last_name', 'user_date_of_birth',
                'user_telephone', 'user_currency', 'user_avatar', 'user_about',
                'user_email_notification', 'user_push_notification'
            ),
            'classes': ('collapse',)
        })
    ]


class RenterDocumentsInline(admin.TabularInline):
    model = RenterDocuments
    extra = 0
    fields = ('title', 'number', 'photo', 'status', 'issue_date')
    readonly_fields = ('photo',)
    can_delete = True
    show_change_link = True


class FeedbackRenterInline(admin.TabularInline):
    model = FeedbackRenter
    extra = 0
    fields = ('content', 'answer', 'user',  'timestamp')
    readonly_fields = ('content', 'user', 'timestamp')
    can_delete = True
    show_change_link = True


class RenterAdmin(BaseUserRelatedAdmin):
    form = RenterAdminForm
    inlines = [RenterDocumentsInline, FeedbackRenterInline]
    list_display = (
        'user', 'verification', 'get_average_rating'
    )
    list_filter = ('verification',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email')

    fieldsets = [
        ('Основная информация', {
            'fields': ('user', 'verification', 'bonus_account')
        }),
        ('Информация о пользователе', {
            'fields': (
                'user_first_name', 'user_last_name', 'user_date_of_birth',
                'user_telephone', 'user_currency', 'user_avatar', 'user_about',
                'user_email_notification', 'user_push_notification'
            ),
            'classes': ('collapse',)
        })
    ]


@admin.register(RenterDocuments)
class RenterDocumentsAdmin(admin.ModelAdmin):
    list_display = ['renter', 'title', 'number', 'status', 'issue_date', 'photo_preview']
    list_filter = ['status', 'title']
    search_fields = ['number', 'renter__user__email', 'renter__user__first_name', 'renter__user__last_name']
    list_select_related = ['renter', 'renter__user']
    readonly_fields = ['photo_preview_large']
    list_editable = ['status']
    actions = ['approve_documents', 'reject_documents']

    fieldsets = [
        ('Основная информация', {
            'fields': ('renter', 'title', 'number', 'status', 'issue_date')
        }),
        ('Фото документа', {
            'fields': ('photo', 'photo_preview_large')
        })
    ]

    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 100px;" />', obj.photo.url)
        return '-'
    photo_preview.short_description = 'Превью'

    def photo_preview_large(self, obj):
        if obj.photo:
            return format_html('<img src="{}" style="max-height: 400px; max-width: 600px;" />', obj.photo.url)
        return '-'
    photo_preview_large.short_description = 'Фото документа'

    @admin.action(description='Подтвердить выбранные документы')
    def approve_documents(self, request, queryset):
        from notification.models import Notification
        updated = 0
        for doc in queryset:
            if doc.status != 'approved':
                doc.status = 'approved'
                doc.save()
                Notification.objects.create(
                    user=doc.renter.user,
                    content='Ваш документ подтверждён',
                    url=f'/profile/documents/'
                )
                updated += 1
        self.message_user(request, f'Подтверждено документов: {updated}', messages.SUCCESS)

    @admin.action(description='Отклонить выбранные документы')
    def reject_documents(self, request, queryset):
        from notification.models import Notification
        updated = 0
        for doc in queryset:
            if doc.status != 'rejected':
                doc.status = 'rejected'
                doc.save()
                Notification.objects.create(
                    user=doc.renter.user,
                    content='Ваш документ отклонён. Пожалуйста, загрузите корректное фото.',
                    url=f'/profile/documents/'
                )
                updated += 1
        self.message_user(request, f'Отклонено документов: {updated}', messages.WARNING)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'symbol', 'rate_to_rub']
    search_fields = ['code', 'title']
    ordering = ['code']


admin.site.register(Lessor, LessorAdmin)
admin.site.register(Renter, RenterAdmin)
admin.site.register(Language)


@admin.register(LessorWithdrawRequest)
class LessorWithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'lessor', 'amount', 'status', 'comment', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at']
    search_fields = ['lessor__user__email', 'lessor__user__first_name', 'lessor__user__last_name']
    list_select_related = ['lessor', 'lessor__user']
    list_editable = ['status']
    ordering = ['-created_at']
    actions = ['approve_requests', 'reject_requests']

    fieldsets = [
        ('Основная информация', {
            'fields': ('lessor', 'amount', 'status')
        }),
        ('Дополнительно', {
            'fields': ('denied_reason', 'comment'),
            'classes': ('collapse',)
        })
    ]

    @admin.action(description='Одобрить выбранные заявки')
    def approve_requests(self, request, queryset):
        from notification.models import Notification
        updated = 0
        for req in queryset:
            if req.status != 'completed':
                req.status = 'completed'
                req.save()
                Notification.objects.create(
                    user=req.lessor.user,
                    content=f'Ваша заявка на вывод {req.amount} одобрена',
                    url='/profile/balance/'
                )
                updated += 1
        self.message_user(request, f'Одобрено заявок: {updated}', messages.SUCCESS)

    @admin.action(description='Отклонить выбранные заявки')
    def reject_requests(self, request, queryset):
        from notification.models import Notification
        updated = 0
        for req in queryset:
            if req.status != 'denied':
                req.status = 'denied'
                req.save()
                Notification.objects.create(
                    user=req.lessor.user,
                    content=f'Ваша заявка на вывод {req.amount} отклонена',
                    url='/profile/balance/'
                )
                updated += 1
        self.message_user(request, f'Отклонено заявок: {updated}', messages.WARNING)

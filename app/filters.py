from django_filters import rest_framework as filters
from .models import RenterDocuments, User


class RenterDocumentsFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=RenterDocuments.STATUS_CHOICES)
    title = filters.ChoiceFilter(choices=RenterDocuments.DOCUMENT_TYPE_CHOICES)

    class Meta:
        model = RenterDocuments
        fields = ['status', 'title']


class UserFilter(filters.FilterSet):
    role = filters.ChoiceFilter(choices=User.ROLES)

    class Meta:
        model = User
        fields = ['role']

from django_filters import rest_framework as filters
from .models import RenterDocuments, User


class RenterDocumentsFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=RenterDocuments.STATUS_CHOICES)

    class Meta:
        model = RenterDocuments
        fields = ['status']


class UserFilter(filters.FilterSet):
    role = filters.ChoiceFilter(choices=User.ROLE_CHOICES)

    class Meta:
        model = User
        fields = ['role']

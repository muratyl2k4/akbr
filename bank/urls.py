from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, TransactionViewSet, auth_login, auth_change_password, list_banks

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('auth/login/', auth_login, name='auth-login'),
    path('auth/change-password/', auth_change_password, name='auth-change-password'),
    path('banks/', list_banks, name='list-banks'),
    path('', include(router.urls)),
]

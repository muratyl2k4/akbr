from django.contrib import admin
from .models import Customer, Transaction

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'customer_no', 'branch_name', 'account_no', 'current_balance')
    search_fields = ('full_name', 'customer_no', 'tc_no', 'iban')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'transaction_date', 'transaction_type', 'amount', 'is_credit', 'balance_after', 'receipt_serial_no')
    list_filter = ('is_credit', 'transaction_type', 'transaction_date')
    search_fields = ('receiver_name', 'receiver_iban', 'receipt_serial_no', 'customer__full_name')

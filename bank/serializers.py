from rest_framework import serializers
from .models import Customer, Transaction
from .services import recalculate_balances

class CustomerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    installment_overdraft_limit = serializers.SerializerMethodField()
    available_installment_overdraft_limit = serializers.SerializerMethodField()

    def get_installment_overdraft_limit(self, obj):
        return round(float(obj.overdraft_limit or 0) * 0.8, 2)

    def get_available_installment_overdraft_limit(self, obj):
        return round(float(obj.available_overdraft_limit or 0) * 0.8, 2)

    class Meta:
        model = Customer
        fields = '__all__'
        read_only_fields = ['current_balance', 'created_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if 'current_balance' not in validated_data or validated_data['current_balance'] == 0:
            validated_data['current_balance'] = validated_data.get('initial_balance', 0)
        customer = super().create(validated_data)
        if password:
            customer.set_password(password)
            customer.save(update_fields=['password'])
        recalculate_balances(customer)
        return customer

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        customer = super().update(instance, validated_data)
        if password:
            customer.set_password(password)
            customer.save(update_fields=['password'])
        recalculate_balances(customer)
        return customer


class TransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_iban = serializers.CharField(source='customer.iban', read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['balance_after', 'receipt_serial_no', 'created_at']

    def _format_outgoing_desc(self, validated_data):
        import re, random
        from .banks import find_bank_by_code, find_bank_by_name, find_bank_by_iban
        is_credit = validated_data.get('is_credit', False)
        receiver = (validated_data.get('receiver_name') or '').strip()
        raw_desc = (validated_data.get('description') or '').strip()
        ref = (validated_data.get('reference_no') or '').strip()
        bank_code = (validated_data.get('bank_code') or '').strip()
        bank_name = (validated_data.get('bank_name') or '').strip()
        receiver_iban = (validated_data.get('receiver_iban') or '').strip()

        bank_info = None
        if bank_code:
            bank_info = find_bank_by_code(bank_code)
        if not bank_info and bank_name:
            bank_info = find_bank_by_name(bank_name)
        if not bank_info and receiver_iban:
            bank_info = find_bank_by_iban(receiver_iban)

        if bank_info:
            validated_data['bank_code'] = bank_info['code']
            validated_data['bank_name'] = bank_info['official_name']
            bank_short = bank_info['short_name']
        else:
            bank_short = bank_name if bank_name else "Garanti Bankası"

        if not is_credit and receiver:
            if not ref:
                ref = f"{random.randint(100000, 999999999):09d}"
            elif len(ref) < 9 and ref.isdigit():
                ref = f"{int(ref):09d}"
            validated_data['reference_no'] = ref

            # Orijinal Akbank formatı: [İsim Soyisim] - [Banka]
            validated_data['description'] = f"{receiver} - {bank_short}"
        elif is_credit and receiver:
            has_formatted = bool(
                raw_desc and (
                    raw_desc.startswith('FAST:')
                    or raw_desc.startswith('EFT:')
                    or raw_desc.startswith('HAVALE:')
                )
            )
            if not has_formatted:
                tx_type_upper = (validated_data.get('transaction_type') or '').upper()
                prefix = 'FAST' if 'FAST' in tx_type_upper else ('EFT' if 'EFT' in tx_type_upper else ('HAVALE' if 'HAVALE' in tx_type_upper else 'FAST'))
                sender_upper = receiver.replace('i', 'İ').replace('ı', 'I').upper()
                validated_data['description'] = f"{prefix}:{sender_upper}"

    def create(self, validated_data):
        self._format_outgoing_desc(validated_data)
        tx = super().create(validated_data)
        recalculate_balances(tx.customer)
        tx.refresh_from_db()
        return tx

    def update(self, instance, validated_data):
        self._format_outgoing_desc(validated_data)
        tx = super().update(instance, validated_data)
        recalculate_balances(tx.customer)
        tx.refresh_from_db()
        return tx

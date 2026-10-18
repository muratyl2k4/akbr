import os
import django
from decimal import Decimal
from datetime import date, time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bank.models import Customer, Transaction
from bank.services import recalculate_balances

# 1. Örnek Müşteri (EMRE CAN DEMİRTAŞ)
customer, _ = Customer.objects.get_or_create(
    customer_no="0088219430",
    defaults={
        "full_name": "EMRE CAN DEMİRTAŞ",
        "tc_no": "45210984712",
        "branch_name": "7777 - AKBANK DİREKT MOBİL CEP",
        "account_no": "888-4412-0098124",
        "iban": "TR44 0004 6008 8844 1200 9812 40",
        "address": "BARBAROS MAH. ATATÜRK CAD. NO:42 D:8 KADIKÖY / İSTANBUL",
        "initial_balance": Decimal("75000.00"),
        "current_balance": Decimal("75000.00"),
    }
)

new_txs_data = [
    {
        'transaction_type': 'HESAPTAN HAVALE',
        'amount': Decimal('22500.00'),
        'is_credit': True,
        'commission': Decimal('0.00'),
        'bsmv': Decimal('0.00'),
        'sch_amount': Decimal('0.00'),
        'transaction_date': date(2026, 10, 2),
        'transaction_time': time(10, 14, 22),
        'receiver_name': 'EMRE CAN DEMİRTAŞ',
        'receiver_iban': customer.iban,
        'description': 'Aylık Hakediş / Maaş Transferi',
        'tag': 'Maaş',
    },
    {
        'transaction_type': 'EFT BANKALAR ARASI HESABA HAVALE',
        'amount': Decimal('1450.50'),
        'is_credit': False,
        'commission': Decimal('7.97'),
        'bsmv': Decimal('0.40'),
        'sch_amount': Decimal('1.00'),
        'transaction_date': date(2026, 10, 3),
        'transaction_time': time(12, 45, 10),
        'receiver_name': 'Selin Kaya',
        'receiver_iban': 'TR62 0006 2000 1234 0006 7891 23',
        'description': 'Ofis Mobilya & Ekipman',
        'tag': 'Alışveriş',
    },
    {
        'transaction_type': 'FAST BANKALAR ARASI ANLIK HAVALE',
        'amount': Decimal('320.00'),
        'is_credit': False,
        'commission': Decimal('7.97'),
        'bsmv': Decimal('0.40'),
        'sch_amount': Decimal('1.00'),
        'transaction_date': date(2026, 10, 4),
        'transaction_time': time(15, 30, 45),
        'receiver_name': 'Burak Şahin',
        'receiver_iban': 'TR33 0004 6001 2345 8880 0012 34',
        'description': 'Yemek ve Restoran Ödemesi',
        'tag': 'Yemek',
    },
    {
        'transaction_type': 'HESAPTAN FAST',
        'amount': Decimal('4800.00'),
        'is_credit': True,
        'commission': Decimal('0.00'),
        'bsmv': Decimal('0.00'),
        'sch_amount': Decimal('0.00'),
        'transaction_date': date(2026, 10, 4),
        'transaction_time': time(18, 0, 15),
        'receiver_name': 'EMRE CAN DEMİRTAŞ',
        'receiver_iban': customer.iban,
        'description': 'Freelance Proje Tahsilatı',
        'tag': 'Gelen Transfer',
    },
    {
        'transaction_type': 'EFT BANKALAR ARASI HESABA HAVALE',
        'amount': Decimal('8750.00'),
        'is_credit': False,
        'commission': Decimal('7.97'),
        'bsmv': Decimal('0.40'),
        'sch_amount': Decimal('1.00'),
        'transaction_date': date(2026, 10, 5),
        'transaction_time': time(11, 20, 0),
        'receiver_name': 'Ali İhsan Koçak',
        'receiver_iban': 'TR88 0004 6007 7118 8800 0332 21',
        'description': 'Ekim Ayı Ev Kirası',
        'tag': 'Kira',
    },
]

Transaction.objects.filter(customer=customer).delete()
for tdata in new_txs_data:
    Transaction.objects.create(customer=customer, **tdata)

new_bal = recalculate_balances(customer)
print(f"Müşteri: {customer.full_name}, Güncel Bakiye: {new_bal} TL")

# 2. İkinci Örnek Müşteri (AYŞE GÜL YILMAZ)
customer2, _ = Customer.objects.get_or_create(
    customer_no="0088219401",
    defaults={
        "full_name": "AYŞE GÜL YILMAZ",
        "tc_no": "28374619284",
        "branch_name": "7777 - AKBANK DİREKT MOBİL CEP",
        "account_no": "888-2910-0044120",
        "iban": "TR92 0004 6002 9100 0044 1200 12",
        "address": "ETİLER MAH. NİSPETİYE CAD. NO:18 BEŞİKTAŞ / İSTANBUL",
        "initial_balance": Decimal("35000.00"),
        "current_balance": Decimal("35000.00"),
    }
)

customer2_txs = [
    {
        'transaction_type': 'HESAPTAN HAVALE',
        'amount': Decimal('15000.00'),
        'is_credit': True,
        'commission': Decimal('0.00'),
        'bsmv': Decimal('0.00'),
        'sch_amount': Decimal('0.00'),
        'transaction_date': date(2026, 10, 1),
        'transaction_time': time(9, 30, 0),
        'receiver_name': 'AYŞE GÜL YILMAZ',
        'receiver_iban': customer2.iban,
        'description': 'Maaş Ödemesi',
        'tag': 'Maaş',
    },
    {
        'transaction_type': 'FAST BANKALAR ARASI ANLIK HAVALE',
        'amount': Decimal('750.00'),
        'is_credit': False,
        'commission': Decimal('7.97'),
        'bsmv': Decimal('0.40'),
        'sch_amount': Decimal('1.00'),
        'transaction_date': date(2026, 10, 3),
        'transaction_time': time(14, 15, 20),
        'receiver_name': 'Mert Deniz',
        'receiver_iban': 'TR11 0006 2000 9876 5432 1000 01',
        'description': 'Market Alışverişi',
        'tag': 'Alışveriş',
    },
    {
        'transaction_type': 'EFT BANKALAR ARASI HESABA HAVALE',
        'amount': Decimal('4200.00'),
        'is_credit': False,
        'commission': Decimal('7.97'),
        'bsmv': Decimal('0.40'),
        'sch_amount': Decimal('1.00'),
        'transaction_date': date(2026, 10, 5),
        'transaction_time': time(16, 40, 10),
        'receiver_name': 'Ahmet Can Demir',
        'receiver_iban': 'TR44 0004 6008 8844 1200 9812 40',
        'description': 'Danışmanlık Hizmeti',
        'tag': 'Hizmet',
    },
]

Transaction.objects.filter(customer=customer2).delete()
for tdata in customer2_txs:
    Transaction.objects.create(customer=customer2, **tdata)

new_bal2 = recalculate_balances(customer2)
print(f"Müşteri: {customer2.full_name}, Güncel Bakiye: {new_bal2} TL")

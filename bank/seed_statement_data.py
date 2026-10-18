import os, sys
import django
from decimal import Decimal
from datetime import date, time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bank.models import Customer, Transaction
from bank.services import recalculate_balances

def seed():
    # Serkan Yıldırım müşterisini bul veya oluştur
    customer, created = Customer.objects.get_or_create(
        customer_no="0071948201",
        defaults={
            "username": "serkan",
            "full_name": "SERKAN YILDIRIM",
            "tc_no": "39182746192",
            "branch_name": "1277- TUZLA İÇMELER",
            "account_no": "888-1277-0084920",
            "iban": "TR56 0004 6012 7788 8000 0849 20",
            "address": "AYDINLI MAH. BARIŞ CAD. NO:14 D:5 TUZLA İSTANBUL",
            "initial_balance": Decimal("42491.63"),
            "current_balance": Decimal("38991.63"),
            "overdraft_limit": Decimal("120000.00"),
            "available_overdraft_limit": Decimal("120000.00"),
            "overdraft_interest_rate": Decimal("4.25"),
            "overdraft_late_interest_rate": Decimal("4.55"),
            "next_statement_date": date(2026, 10, 31),
        }
    )

    # Güncelle
    customer.username = "serkan"
    customer.full_name = "SERKAN YILDIRIM"
    customer.tc_no = "39182746192"
    customer.branch_name = "1277- TUZLA İÇMELER"
    customer.account_no = "888-1277-0084920"
    customer.iban = "TR56 0004 6012 7788 8000 0849 20"
    customer.address = "AYDINLI MAH. BARIŞ CAD. NO:14 D:5 TUZLA İSTANBUL"
    customer.initial_balance = Decimal("42491.63")
    customer.overdraft_limit = Decimal("120000.00")
    customer.available_overdraft_limit = Decimal("120000.00")
    customer.overdraft_interest_rate = Decimal("4.25")
    customer.overdraft_late_interest_rate = Decimal("4.55")
    customer.next_statement_date = date(2026, 10, 31)
    customer.set_password("123456")
    customer.save()
    customer.save()

    # Mevcut işlemleri temizle
    customer.transactions.all().delete()

    txs_data = [
        {"d": date(2026, 9, 2), "t": time(10, 15), "desc": "FAST:ELA TORUNOĞLU", "amt": Decimal("1530.00"), "cr": True, "tag": "FAST Transfer"},
        {"d": date(2026, 9, 3), "t": time(11, 20), "desc": "0943604-Havin Yıldız-", "amt": Decimal("2750.00"), "cr": False, "tag": "Transfer"},
        {"d": date(2026, 9, 3), "t": time(11, 21), "desc": "EFT KOMİSYONU", "amt": Decimal("7.97"), "cr": False, "tag": "Masraf"},
        {"d": date(2026, 9, 3), "t": time(11, 21), "desc": "EFT BSMV", "amt": Decimal("0.40"), "cr": False, "tag": "Vergi"},
        {"d": date(2026, 9, 3), "t": time(14, 45), "desc": "046 HEPSİPAY /HEPSIPAY H XXXX 2605", "amt": Decimal("1624.99"), "cr": False, "tag": "Kart Harcaması"},
        {"d": date(2026, 9, 5), "t": time(16, 10), "desc": "064 BİM AS/9562/K713/ESK XXXX 2605", "amt": Decimal("517.00"), "cr": False, "tag": "Market"},
        {"d": date(2026, 9, 6), "t": time(12, 30), "desc": "046 TRENDYOL MİLLA    XXXX 2605-096322-İADE", "amt": Decimal("1063.01"), "cr": True, "tag": "İade"},
        {"d": date(2026, 9, 7), "t": time(13, 15), "desc": "015 RUYA CAFE    XXXX 2605", "amt": Decimal("800.00"), "cr": False, "tag": "Kafe / Restoran"},
        {"d": date(2026, 9, 7), "t": time(15, 40), "desc": "046 KUMLUCA AVM    XXXX 2605", "amt": Decimal("1420.00"), "cr": False, "tag": "Alışveriş"},
        {"d": date(2026, 9, 7), "t": time(18, 55), "desc": "010 A101 9936 K644 NAREN XXXX 2605", "amt": Decimal("243.50"), "cr": False, "tag": "Market"},
        {"d": date(2026, 9, 8), "t": time(11, 10), "desc": "046 TRENDYOL MİLLA    XXXX 2605-096322-İADE", "amt": Decimal("819.98"), "cr": True, "tag": "İade"},
        {"d": date(2026, 9, 12), "t": time(14, 25), "desc": "067 BİM-L926-ORMAN ISLET XXXX 2605", "amt": Decimal("616.00"), "cr": False, "tag": "Market"},
        {"d": date(2026, 9, 13), "t": time(17, 35), "desc": "064 9936-88 82-A101-TEME XXXX 2605", "amt": Decimal("282.50"), "cr": False, "tag": "Market"},
        {"d": date(2026, 9, 14), "t": time(19, 0), "desc": "067 BİM ESKICAMI K713    XXXX 2605", "amt": Decimal("102.97"), "cr": False, "tag": "Market"},
        {"d": date(2026, 9, 22), "t": time(12, 10), "desc": "062 ENMODA AKSESUAR    XXXX 2605", "amt": Decimal("100.00"), "cr": False, "tag": "Alışveriş"},
        {"d": date(2026, 9, 22), "t": time(14, 0), "desc": "FAST:SERKAN YILDIRIM SERKAN YILDIRIM tarafından aktarılan", "amt": Decimal("500.00"), "cr": True, "tag": "FAST Transfer"},
        {"d": date(2026, 9, 24), "t": time(16, 20), "desc": "046 HEPSİPAY/HEPSIPAY HE XXXX 2605-178101-İADE", "amt": Decimal("1624.99"), "cr": True, "tag": "İade"},
        {"d": date(2026, 9, 30), "t": time(23, 50), "desc": "Artı Para Faizi", "amt": Decimal("0.04"), "cr": False, "tag": "Faiz"},
        {"d": date(2026, 9, 30), "t": time(23, 51), "desc": "Artı Para Vergi", "amt": Decimal("0.01"), "cr": False, "tag": "Vergi"},
        {"d": date(2026, 9, 30), "t": time(23, 52), "desc": "Artı Para Fon Payı", "amt": Decimal("0.01"), "cr": False, "tag": "Fon Payı"},
    ]

    for item in txs_data:
        Transaction.objects.create(
            customer=customer,
            transaction_date=item["d"],
            transaction_time=item["t"],
            description=item["desc"],
            transaction_type=item["tag"],
            amount=item["amt"],
            is_credit=item["cr"],
            commission=Decimal("0.00"),
            bsmv=Decimal("0.00"),
            sch_amount=Decimal("0.00"),
            tag=item["tag"],
        )

    new_bal = recalculate_balances(customer)
    print(f"Customer seeded: {customer.full_name} ({customer.customer_no}) - Final balance: {new_bal} TL (Expected: 2,097.00 TL)")
    print(f"Overdraft: {customer.overdraft_limit} TL, Available: {customer.available_overdraft_limit} TL")

if __name__ == '__main__':
    seed()

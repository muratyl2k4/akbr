import datetime
from decimal import Decimal
from django.db import transaction
from .models import Customer, Transaction

def _add_seconds(t, secs):
    if not t:
        return datetime.time(0, 0, secs)
    dt = datetime.datetime.combine(datetime.date.today(), t) + datetime.timedelta(seconds=secs)
    return dt.time()

@transaction.atomic
def recalculate_balances(customer: Customer) -> Decimal:
    """
    Müşteriye ait tüm hesap hareketlerini kronolojik sıraya dizer.
    Para çıkışı (is_credit=False) olup komisyon veya BSMV içeren işlemler için
    ayrı ayrı 'EFT KOMİSYONU' ve 'EFT BSMV' alt işlemlerini üretir / senkronize eder.
    running_balance = initial_balance üzerinden tüm satırların balance_after
    değerini ve müşterinin current_balance değerini günceller.
    """
    # 1. Ana işlemleri kontrol et (fee_transactions haricindekiler)
    parent_transactions = Transaction.objects.filter(
        customer=customer,
        parent_transaction__isnull=True
    )

    for tx in parent_transactions:
        # Eski toplu 'KESİNTİ VE EKLERİ' alt işlemlerini temizle
        Transaction.objects.filter(parent_transaction=tx, transaction_type="KESİNTİ VE EKLERİ").delete()

        # Eğer giden transfer ise bankayı belirle ve açıklamasını [Alıcı] - [Banka] olarak ayarla
        main_title = tx.description
        if not tx.is_credit and tx.receiver_name:
            from .banks import find_bank_by_code, find_bank_by_name, find_bank_by_iban
            bank_info = None
            if tx.bank_code:
                bank_info = find_bank_by_code(tx.bank_code)
            if not bank_info and tx.bank_name:
                bank_info = find_bank_by_name(tx.bank_name)
            if not bank_info and tx.receiver_iban:
                bank_info = find_bank_by_iban(tx.receiver_iban)

            if bank_info:
                bank_short = bank_info["short_name"]
                if not tx.bank_name:
                    tx.bank_name = bank_info["official_name"]
                if not tx.bank_code:
                    tx.bank_code = bank_info["code"]
            else:
                bank_short = tx.bank_name.strip() if tx.bank_name else "Garanti Bankası"

            main_title = f"{tx.receiver_name.strip()} - {bank_short}"
            tx.description = main_title

            ref = tx.reference_no.strip() if tx.reference_no else ""
            if not ref or ref in ["000654698", "0943605"]:
                import random
                ref = f"{random.randint(100000000, 999999999)}"
            elif len(ref) < 9 and ref.isdigit():
                ref = f"{int(ref):09d}"
            tx.reference_no = ref
            tx.save(update_fields=['description', 'reference_no', 'bank_name', 'bank_code'])

        # Eğer gelen transfer ise ve formatlanmamışsa 'FAST:GÖNDEREN' formatını sağla
        if tx.is_credit and tx.receiver_name:
            import re
            raw_desc = (tx.description or '').strip()
            has_formatted = bool(
                raw_desc and (
                    raw_desc.startswith('FAST:')
                    or raw_desc.startswith('EFT:')
                    or raw_desc.startswith('HAVALE:')
                )
            )
            if not has_formatted:
                tx_type_upper = (tx.transaction_type or '').upper()
                prefix = 'FAST' if 'FAST' in tx_type_upper else ('EFT' if 'EFT' in tx_type_upper else ('HAVALE' if 'HAVALE' in tx_type_upper else 'FAST'))
                sender_upper = tx.receiver_name.strip().replace('i', 'İ').replace('ı', 'I').upper()
                tx.description = f"{prefix}:{sender_upper}"
                tx.save(update_fields=['description'])

        # 1.1 EFT KOMİSYONU Satırı
        comm_val = tx.commission or Decimal('0.00')
        if not tx.is_credit and comm_val > Decimal('0.00'):
            comm_tx = Transaction.objects.filter(parent_transaction=tx, tag="Masraf").first()
            if not comm_tx:
                comm_tx = Transaction.objects.filter(parent_transaction=tx, description__contains="KOMİSYON").first()
            if not comm_tx:
                comm_tx = Transaction.objects.filter(parent_transaction=tx, description__contains="Komisyon").first()

            comm_title = f"{main_title}- Komisyon"
            comm_time = _add_seconds(tx.transaction_time, 1)
            if comm_tx:
                updated = False
                if comm_tx.amount != comm_val:
                    comm_tx.amount = comm_val
                    updated = True
                if comm_tx.transaction_date != tx.transaction_date:
                    comm_tx.transaction_date = tx.transaction_date
                    updated = True
                if comm_tx.transaction_time != comm_time:
                    comm_tx.transaction_time = comm_time
                    updated = True
                if comm_tx.transaction_type != "EFT KOMİSYONU":
                    comm_tx.transaction_type = "EFT KOMİSYONU"
                    updated = True
                if comm_tx.description != comm_title:
                    comm_tx.description = comm_title
                    updated = True
                if comm_tx.receiver_name != tx.receiver_name:
                    comm_tx.receiver_name = tx.receiver_name
                    updated = True
                if comm_tx.bank_name != tx.bank_name:
                    comm_tx.bank_name = tx.bank_name
                    updated = True
                if comm_tx.bank_code != tx.bank_code:
                    comm_tx.bank_code = tx.bank_code
                    updated = True
                if comm_tx.tag != "Masraf":
                    comm_tx.tag = "Masraf"
                    updated = True
                if updated:
                    comm_tx.save()
            else:
                Transaction.objects.create(
                    customer=customer,
                    parent_transaction=tx,
                    transaction_type="EFT KOMİSYONU",
                    amount=comm_val,
                    is_credit=False,
                    sch_amount=Decimal('0.00'),
                    commission=Decimal('0.00'),
                    bsmv=Decimal('0.00'),
                    transaction_date=tx.transaction_date,
                    transaction_time=comm_time,
                    valor_date=tx.valor_date or tx.transaction_date,
                    description=comm_title,
                    receiver_name=tx.receiver_name,
                    receiver_iban=tx.receiver_iban,
                    bank_name=tx.bank_name,
                    bank_code=tx.bank_code,
                    tag="Masraf",
                )
        else:
            Transaction.objects.filter(parent_transaction=tx, tag="Masraf").delete()
            Transaction.objects.filter(parent_transaction=tx, description__contains="KOMİSYON").delete()
            Transaction.objects.filter(parent_transaction=tx, description__contains="Komisyon").delete()

        # 1.2 EFT BSMV Satırı
        bsmv_val = tx.bsmv or Decimal('0.00')
        if not tx.is_credit and bsmv_val > Decimal('0.00'):
            bsmv_tx = Transaction.objects.filter(parent_transaction=tx, tag="Vergi").first()
            if not bsmv_tx:
                bsmv_tx = Transaction.objects.filter(parent_transaction=tx, description__contains="BSMV").first()
            if not bsmv_tx:
                bsmv_tx = Transaction.objects.filter(parent_transaction=tx, description__contains="Vergi").first()

            bsmv_title = f"{main_title}- Vergi"
            bsmv_time = _add_seconds(tx.transaction_time, 2)
            if bsmv_tx:
                updated = False
                if bsmv_tx.amount != bsmv_val:
                    bsmv_tx.amount = bsmv_val
                    updated = True
                if bsmv_tx.transaction_date != tx.transaction_date:
                    bsmv_tx.transaction_date = tx.transaction_date
                    updated = True
                if bsmv_tx.transaction_time != bsmv_time:
                    bsmv_tx.transaction_time = bsmv_time
                    updated = True
                if bsmv_tx.transaction_type != "EFT BSMV":
                    bsmv_tx.transaction_type = "EFT BSMV"
                    updated = True
                if bsmv_tx.description != bsmv_title:
                    bsmv_tx.description = bsmv_title
                    updated = True
                if bsmv_tx.receiver_name != tx.receiver_name:
                    bsmv_tx.receiver_name = tx.receiver_name
                    updated = True
                if bsmv_tx.bank_name != tx.bank_name:
                    bsmv_tx.bank_name = tx.bank_name
                    updated = True
                if bsmv_tx.bank_code != tx.bank_code:
                    bsmv_tx.bank_code = tx.bank_code
                    updated = True
                if bsmv_tx.tag != "Vergi":
                    bsmv_tx.tag = "Vergi"
                    updated = True
                if updated:
                    bsmv_tx.save()
            else:
                Transaction.objects.create(
                    customer=customer,
                    parent_transaction=tx,
                    transaction_type="EFT BSMV",
                    amount=bsmv_val,
                    is_credit=False,
                    sch_amount=Decimal('0.00'),
                    commission=Decimal('0.00'),
                    bsmv=Decimal('0.00'),
                    transaction_date=tx.transaction_date,
                    transaction_time=bsmv_time,
                    valor_date=tx.valor_date or tx.transaction_date,
                    description=bsmv_title,
                    receiver_name=tx.receiver_name,
                    receiver_iban=tx.receiver_iban,
                    bank_name=tx.bank_name,
                    bank_code=tx.bank_code,
                    tag="Vergi",
                )
        else:
            Transaction.objects.filter(parent_transaction=tx, tag="Vergi").delete()
            Transaction.objects.filter(parent_transaction=tx, description__contains="BSMV").delete()
            Transaction.objects.filter(parent_transaction=tx, description__contains="Vergi").delete()

    # 2. Tüm işlemleri kronolojik olarak sırala
    all_txs = list(
        Transaction.objects.filter(customer=customer)
        .order_by('transaction_date', 'transaction_time', 'id')
    )

    # 3. Yürüyen bakiye (running balance) hesapla
    running_balance = Decimal(str(customer.initial_balance))

    for tx in all_txs:
        if tx.is_credit:
            running_balance += Decimal(str(tx.amount))
        else:
            running_balance -= Decimal(str(tx.amount))

        used_od = abs(running_balance) if running_balance < Decimal('0.00') else Decimal('0.00')
        if customer.overdraft_limit and used_od > customer.overdraft_limit:
            used_od = customer.overdraft_limit

        updated_fields = []
        if tx.balance_after != running_balance:
            tx.balance_after = running_balance
            updated_fields.append('balance_after')
        if tx.used_overdraft != used_od:
            tx.used_overdraft = used_od
            updated_fields.append('used_overdraft')

        if updated_fields:
            tx.save(update_fields=updated_fields)

    # 4. Müşterinin güncel bakiyesini ve kalan artı para limitini kaydet
    customer.current_balance = running_balance
    if customer.overdraft_limit:
        used_now = abs(running_balance) if running_balance < Decimal('0.00') else Decimal('0.00')
        ov_limit = Decimal(str(customer.overdraft_limit))
        customer.available_overdraft_limit = max(Decimal('0.00'), ov_limit - used_now)
    customer.save(update_fields=['current_balance', 'available_overdraft_limit'])

    return running_balance

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_profile')
    username = models.CharField(max_length=50, blank=True, default="", verbose_name="Kullanıcı Adı")
    full_name = models.CharField(max_length=150, verbose_name="Adı Soyadı / Unvan")
    tc_no = models.CharField(max_length=11, verbose_name="TCKN / VKN")
    customer_no = models.CharField(max_length=20, default="0071948201", verbose_name="Müşteri No")
    branch_name = models.CharField(max_length=100, default="1277- TUZLA İÇMELER", verbose_name="Düzenleyen Şube")
    account_no = models.CharField(max_length=30, default="888-1277-0084920", verbose_name="Borçlu Hesap No")
    iban = models.CharField(max_length=34, default="TR56 0004 6012 7788 8000 0849 20", verbose_name="IBAN")
    address = models.TextField(default="AYDINLI MAH. BARIŞ CAD. NO:14 D:5 TUZLA İSTANBUL", verbose_name="Adres")
    initial_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Başlangıç Bakiyesi")
    current_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="Güncel Bakiye")
    overdraft_limit = models.DecimalField(max_digits=14, decimal_places=2, default=115500.00, verbose_name="Artı Para Limiti")
    available_overdraft_limit = models.DecimalField(max_digits=14, decimal_places=2, default=115500.00, verbose_name="Kullanılabilir Artı Para Limiti")
    overdraft_interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=4.25, verbose_name="Artı Para Akdi Faiz Oranı (Aylık)")
    overdraft_late_interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=4.55, verbose_name="Gecikme Faizi Oranı")
    next_statement_date = models.DateField(null=True, blank=True, verbose_name="Bir Sonraki Ekstre Tarihi")
    password = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Giriş Şifresi",
        help_text="Kullanıcının giriş şifresini buraya normal (düz) olarak yazabilirsiniz (Örn: 123456 veya injection.123). Otomatik hashlenir."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Müşteri"
        verbose_name_plural = "Müşteriler"
        ordering = ['-id']

    def save(self, *args, **kwargs):
        # Eğer şifre düz metin girildiyse (hash formatında değilse) otomatik hash'le
        if self.password and not (self.password.startswith('pbkdf2_') or self.password.startswith('argon2') or self.password.startswith('bcrypt')):
            self.set_password(self.password)
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        if not self.password:
            return False
        # Düz metin olarak kaydedilmişse doğrudan eşleştir
        if self.password == raw_password:
            return True
        try:
            return check_password(raw_password, self.password)
        except Exception:
            return self.password == raw_password

    def __str__(self):
        return f"{self.full_name} ({self.customer_no})"


class Transaction(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions', verbose_name="Müşteri")
    parent_transaction = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='fee_transactions',
        verbose_name="Ana İşlem (Masraf Bağlantısı)"
    )
    transaction_type = models.CharField(
        max_length=60,
        default="EFT BANKALAR ARASI HESABA HAVALE",
        verbose_name="İşlem Tipi"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Tutar")
    is_credit = models.BooleanField(default=False, verbose_name="Gelen Para (+)")  # False: Giden (-), True: Gelen (+)
    used_overdraft = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Kullanılan Artı Para")

    # Akbank Dekont Tutar Tablosu Kalemleri
    sch_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="ŞCH Tutarı")
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=15.96, verbose_name="GECEFT Komisyon")
    bsmv = models.DecimalField(max_digits=10, decimal_places=2, default=0.80, verbose_name="GEC EFT BSMV")

    # Tarih ve Saat
    transaction_date = models.DateField(default=timezone.now, verbose_name="İşlem Tarihi")
    transaction_time = models.TimeField(default=timezone.now, verbose_name="İşlem Saati")
    valor_date = models.DateField(null=True, blank=True, verbose_name="Valör Tarihi")

    # Alıcı Bilgileri
    receiver_name = models.CharField(max_length=150, blank=True, verbose_name="Alıcı Adı Soyadı")
    receiver_iban = models.CharField(max_length=34, blank=True, verbose_name="Alıcı IBAN")
    bank_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Banka Adı")
    bank_code = models.CharField(max_length=10, blank=True, default="", verbose_name="Banka Kodu")
    user_note = models.CharField(max_length=255, blank=True, default="", verbose_name="Açıklama / Not")
    receiver_branch = models.CharField(max_length=100, default="-", blank=True, verbose_name="Karşı Şube")
    receiver_account_no = models.CharField(max_length=34, blank=True, verbose_name="Alıcı Hesap No")
    receiver_vkn_tckn = models.CharField(max_length=20, blank=True, verbose_name="Alıcı VKN/TCKN")
    receiver_address = models.TextField(blank=True, verbose_name="Alıcı Adresi")

    # Dekont ve Operatör Bilgileri
    reference_no = models.CharField(max_length=50, blank=True, verbose_name="Referans No")
    operator = models.CharField(max_length=50, default="KENDISI", verbose_name="İşlemi Yapan")
    operator_name = models.CharField(max_length=150, blank=True, verbose_name="İşlemi Yapan Ad-Soyad")
    operator_tckn = models.CharField(max_length=11, blank=True, verbose_name="İşlemi Yapan TCKN")
    channel_code = models.CharField(max_length=50, default="40033406 / 554193 /", verbose_name="Kanal Kodu")
    qr_token = models.CharField(max_length=50, default="OZDM6v57aYB601", verbose_name="QR Token")

    description = models.CharField(max_length=255, blank=True, verbose_name="Açıklama")
    tag = models.CharField(max_length=50, default="Para Transferi", verbose_name="Etiket")
    balance_after = models.DecimalField(max_digits=14, decimal_places=2, default=0.00, verbose_name="İşlem Sonrası Bakiye")
    receipt_serial_no = models.CharField(max_length=64, blank=True, unique=True, verbose_name="Dekont Seri No")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hesap Hareketi"
        verbose_name_plural = "Hesap Hareketleri"
        ordering = ['transaction_date', 'transaction_time', 'id']

    def save(self, *args, **kwargs):
        if not self.receipt_serial_no:
            self.receipt_serial_no = f"AKB-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        if not self.reference_no or self.reference_no in ["000654698", "0943605"]:
            import random
            self.reference_no = f"{random.randint(100000000, 999999999)}"
        if not self.valor_date:
            self.valor_date = self.transaction_date
        if not self.operator_name and self.customer:
            self.operator_name = self.customer.full_name
        if not self.operator_tckn and self.customer:
            self.operator_tckn = self.customer.tc_no
        super().save(*args, **kwargs)

    def __str__(self):
        sign = "+" if self.is_credit else "-"
        return f"{self.transaction_date} | {self.customer.full_name} | {sign}{self.amount} TL ({self.transaction_type})"

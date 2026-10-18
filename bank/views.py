from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Customer, Transaction
from .serializers import CustomerSerializer, TransactionSerializer
from .services import recalculate_balances
from .pdf_generator import generate_transaction_receipt_pdf, render_pdf_to_png

from .statement_generator import generate_account_statement_pdf, render_statement_png

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def list(self, request, *args, **kwargs):
        # Güvenlik gereği tüm müşterilerin genel erişimle toplu listelenmesi engellenmiştir.
        # Giriş işlemleri /api/auth/login/ üzerinden güvenli kimlik doğrulama ile yapılır.
        return Response(
            {"detail": "Genel müşteri listesi güvenlik nedeniyle erişime kapatılmıştır. Lütfen kimlik doğrulama yapınız."},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        customer = self.get_object()
        txs = customer.transactions.all().order_by('transaction_date', 'transaction_time', 'id')
        serializer = TransactionSerializer(txs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        customer = self.get_object()
        new_balance = recalculate_balances(customer)
        return Response({
            "status": "success",
            "message": "Bakiyeler ve kesintiler yeniden hesaplandı.",
            "current_balance": str(new_balance)
        })

    @action(detail=True, methods=['get'])
    def statement(self, request, pk=None):
        """Müşteriye ait 2 sayfalık piksel-kusursuz Akbank Hesap Özeti PDF'ini oluşturur ve döndürür"""
        customer = self.get_object()
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        period = request.query_params.get('period') or request.query_params.get('filter') or '1m'
        
        latest_tx = customer.transactions.order_by('transaction_date', 'transaction_time', 'id').last()
        default_month = latest_tx.transaction_date.month if latest_tx else 10
        default_year = latest_tx.transaction_date.year if latest_tx else 2026
        
        month = int(month) if month else default_month
        year = int(year) if year else default_year

        pdf_bytes = generate_account_statement_pdf(customer, month=month, year=year, period_filter=period)
        filename = f"Akbank_Hesap_Ozeti_{customer.customer_no}_{period}_{year}_{month:02d}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='statement-preview')
    def statement_preview(self, request, pk=None):
        """Hesap Özeti PDF'inin yüksek çözünürlüklü sayfa önizleme görselini döndürür"""
        customer = self.get_object()
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        period = request.query_params.get('period') or request.query_params.get('filter') or '1m'
        page_num = int(request.query_params.get('page', 1)) - 1
        
        latest_tx = customer.transactions.order_by('transaction_date', 'transaction_time', 'id').last()
        default_month = latest_tx.transaction_date.month if latest_tx else 10
        default_year = latest_tx.transaction_date.year if latest_tx else 2026
        
        month = int(month) if month else default_month
        year = int(year) if year else default_year

        pdf_bytes = generate_account_statement_pdf(customer, month=month, year=year, period_filter=period)
        png_bytes = render_statement_png(pdf_bytes, page_num=max(0, page_num), dpi=180)
        return HttpResponse(png_bytes, content_type='image/png')


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, 'detail', False) or self.action in ['retrieve', 'receipt', 'receipt_preview', 'update', 'partial_update', 'destroy']:
            return qs
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            return qs.filter(customer_id=customer_id).order_by('-transaction_date', '-transaction_time', '-id')
        # Güvenlik gereği müşteri parametresi olmadan genel işlem listesi döndürülmez
        return qs.none()

    def perform_destroy(self, instance):
        customer = instance.customer
        instance.delete()
        recalculate_balances(customer)

    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        """İşleme ait piksel-kusursuz Akbank dekont PDF'ini oluşturur ve döndürür"""
        try:
            tx = Transaction.objects.get(pk=pk)
        except Transaction.DoesNotExist:
            return Response({"detail": "İşlem bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        mask = request.query_params.get('mask', 'false').lower() in ('true', '1')
        pdf_bytes = generate_transaction_receipt_pdf(tx, mask_identity=mask)

        filename = f"Akbank_Dekont_{tx.receipt_serial_no}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='receipt-preview')
    def receipt_preview(self, request, pk=None):
        """Dekont PDF'inin yüksek çözünürlüklü vektörel PNG önizlemesini döndürür"""
        try:
            tx = Transaction.objects.get(pk=pk)
        except Transaction.DoesNotExist:
            return Response({"detail": "İşlem bulunamadı."}, status=status.HTTP_404_NOT_FOUND)

        mask = request.query_params.get('mask', 'false').lower() in ('true', '1')
        pdf_bytes = generate_transaction_receipt_pdf(tx, mask_identity=mask)
        png_bytes = render_pdf_to_png(pdf_bytes, dpi=180)
        return HttpResponse(png_bytes, content_type='image/png')


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.db.models import Q

@api_view(['POST'])
@permission_classes([AllowAny])
def auth_login(request):
    """
    Güvenli Kimlik Doğrulama Endpoint'i.
    Kullanıcı adı, TCKN veya Müşteri No ve Şifre kontrol edilir.
    Hatalı girişte asla spesifik hesap detayı sızdırılmaz.
    Başarılı girişte YALNIZCA o müşterinin verisi döndürülür.
    """
    identifier = str(request.data.get('username') or request.data.get('identifier') or '').strip()
    password = str(request.data.get('password') or '').strip()

    if not identifier or not password:
        return Response(
            {"status": "error", "message": "Kullanıcı adı ve şifre zorunludur."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Kullanıcı Adı, Müşteri No, TCKN veya bağlı Django user username ile ara
    customer = Customer.objects.filter(
        Q(username__iexact=identifier) |
        Q(customer_no__iexact=identifier) |
        Q(tc_no__iexact=identifier) |
        Q(user__username__iexact=identifier)
    ).first()

    if not customer:
        customer = Customer.objects.filter(full_name__iexact=identifier).first()

    if not customer:
        return Response(
            {"status": "error", "message": "Geçersiz kullanıcı adı veya şifre."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not customer.check_password(password):
        return Response(
            {"status": "error", "message": "Geçersiz kullanıcı adı veya şifre."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    serializer = CustomerSerializer(customer)
    return Response({
        "status": "success",
        "message": "Giriş başarılı.",
        "customer": serializer.data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_change_password(request):
    """Kullanıcının şifresini güvenle güncellemesi için endpoint"""
    identifier = str(request.data.get('username') or request.data.get('identifier') or '').strip()
    old_password = str(request.data.get('old_password') or '').strip()
    new_password = str(request.data.get('new_password') or '').strip()

    if not identifier or not old_password or not new_password:
        return Response(
            {"status": "error", "message": "Tüm alanlar zorunludur."},
            status=status.HTTP_400_BAD_REQUEST
        )

    customer = Customer.objects.filter(
        Q(username__iexact=identifier) |
        Q(customer_no__iexact=identifier) |
        Q(tc_no__iexact=identifier) |
        Q(user__username__iexact=identifier)
    ).first()

    if not customer or not customer.check_password(old_password):
        return Response(
            {"status": "error", "message": "Mevcut şifre hatalı."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if len(new_password) < 4:
        return Response(
            {"status": "error", "message": "Yeni şifre en az 4 karakter olmalıdır."},
            status=status.HTTP_400_BAD_REQUEST
        )

    customer.set_password(new_password)
    customer.save(update_fields=['password'])
    return Response({
        "status": "success",
        "message": "Şifreniz başarıyla güncellendi."
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def list_banks(request):
    """Türkiye'deki tüm bankaların listesini ve IBAN kodlarını döndürür"""
    from .banks import TURKISH_BANKS
    return Response(TURKISH_BANKS)




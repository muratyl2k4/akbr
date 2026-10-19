import os
import io
import fitz
import qrcode
from decimal import Decimal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

SYSTEM_ARIAL = r"C:\Windows\Fonts\arial.ttf"
FALLBACK_FONT = os.path.join(ASSETS_DIR, "arial_narrow.ttf")
FONT_FILE = SYSTEM_ARIAL if os.path.exists(SYSTEM_ARIAL) else FALLBACK_FONT
LOGO_PATH = os.path.join(ASSETS_DIR, "akbank_logo_crisp.png")

FONT_OBJ = fitz.Font(fontfile=FONT_FILE)

def get_text_width(text: str, fontsize: float, is_bold: bool = False) -> float:
    """Metnin 0.82 yatay oranlı Arial ile nokta (point) cinsinden genişliğini hesaplar"""
    w = FONT_OBJ.text_length(text, fontsize=fontsize) * 0.82
    if is_bold:
        w += len(text) * 0.0333 * fontsize * 0.82
    return w

def wrap_text(text: str, max_width: float, fontsize: float = 10.0) -> list[str]:
    """Uzun metinleri kelime bazlı bölerek satırlara ayırır"""
    words = text.split()
    if not words:
        return [""]
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        if get_text_width(test_line, fontsize) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def mask_text(text: str) -> str:
    if not text:
        return text
    parts = text.strip().split()
    masked = []
    for p in parts:
        if len(p) <= 1:
            masked.append(p)
        else:
            masked.append(p[0] + "*" * (len(p) - 1))
    return " ".join(masked)

def convert_to_turkish_words(amount: float) -> str:
    """Para tutarını Türkçe metin olarak yazar (Örn: 9.77 -> 'YALNIZ DOKUZ TL YETMİŞYEDİ KR')"""
    whole = int(amount)
    decimal = int(round((amount - whole) * 100))

    units = ["", "BİR", "İKİ", "ÜÇ", "DÖRT", "BEŞ", "ALTI", "YEDİ", "SEKİZ", "DOKUZ"]
    tens = ["", "ON", "YİRMİ", "OTUZ", "KIRK", "ELLİ", "ALTMIŞ", "YETMİŞ", "SEKSEN", "DOKSAN"]
    thousands = ["", "BİN", "MİLYON", "MİLYAR"]

    def convert_three_digits(number: int) -> str:
        h = number // 100
        t = (number % 100) // 10
        u = number % 10
        res = ""
        if h > 0:
            if h == 1:
                res += "YÜZ"
            else:
                res += f"{units[h]}YÜZ"
        if t > 0:
            res += tens[t]
        if u > 0:
            res += units[u]
        return res

    def convert_whole(number: int) -> str:
        if number == 0:
            return "SIFIR"
        res = ""
        group_count = 0
        temp = number
        while temp > 0:
            part = temp % 1000
            if part > 0:
                part_str = convert_three_digits(part)
                if group_count == 1 and part == 1:
                    res = "BİN" + res
                else:
                    res = part_str + thousands[group_count] + res
            temp //= 1000
            group_count += 1
        return res

    whole_str = convert_whole(whole)
    dec_str = ""
    if decimal > 0:
        t = decimal // 10
        u = decimal % 10
        dec_str = f"{tens[t]}{units[u]} KR"

    if dec_str:
        return f"YALNIZ {whole_str} TL {dec_str}"
    else:
        return f"YALNIZ {whole_str} TL"

def format_tr_currency(val: float) -> str:
    """Para tutarını Türk bankacılık standardında formatlar (Örn: 45850.75 -> '45.850,75')"""
    s = f"{val:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def generate_qr_stream(data: str) -> bytes:
    """QR kod üretip PNG byte olarak döner"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def insert_text_styled(
    page,
    point,
    text: str,
    fontsize: float,
    is_bold: bool = False,
    max_width: float = None,
    align: str = "left",
    color=(0.0, 0.0, 0.0),
):
    """Orijinal Akbank dekontundaki kalın/ince stroke mekanizmasını uygular"""
    if not text:
        return

    actual_fontsize = fontsize
    text_w = get_text_width(text, actual_fontsize, is_bold)

    if max_width and text_w > max_width:
        actual_fontsize = max(6.5, fontsize * (max_width / text_w))
        text_w = get_text_width(text, actual_fontsize, is_bold)

    px = point.x
    if align == "right":
        px = point.x - text_w
    elif align == "center":
        px = point.x - (text_w / 2.0)

    p = fitz.Point(px, point.y)
    m = (p, fitz.Matrix(0.82, 1.0))

    if is_bold:
        page.insert_text(
            p,
            text,
            fontname="ArialCustom",
            fontsize=actual_fontsize,
            color=color,
            fill=color,
            border_width=0.03333,
            render_mode=2,
            morph=m,
        )
    else:
        page.insert_text(
            p,
            text,
            fontname="ArialCustom",
            fontsize=actual_fontsize,
            color=color,
            render_mode=0,
            morph=m,
        )

def generate_akbank_pdf_bytes(
    transaction_title: str = "EFT BANKALAR ARASI HESABA HAVALE",
    branch_name: str = "1277- TUZLA İÇMELER",
    sender_account_no: str = "888-1277-0084920",
    sender_customer_no: str = "0071948201",
    sender_vkn_tckn: str = "39182746192",
    sender_name: str = "SERKAN YILDIRIM",
    sender_address: str = "AYDINLI MAH. BARIŞ CAD. NO:14 D:5 TUZLA İSTANBUL",
    sender_iban: str = "TR560004601277888000084920",
    receiver_iban: str = "TR44 0006 2000 1122 3344 5566 77",
    receiver_branch: str = "-",
    receiver_vkn_tckn: str = "",
    receiver_name: str = "Buse Kaya",
    receiver_address: str = "",
    amount: float = 3500.00,
    sch_amount: float = 1.00,
    commission: float = 7.97,
    bsmv: float = 0.40,
    date_str: str = "15.09.2026",
    time_str: str = "14:25:00",
    valor_str: str = "15.09.2026",
    reference_no: str = "0943605",
    operator: str = "KENDISI",
    operator_name: str = "SERKAN YILDIRIM",
    operator_tckn: str = "39182746192",
    channel_code: str = "07194820 / 554193 /",
    qr_token: str = "OZDM6v57aYB601",
    mask_identity: bool = False,
) -> bytes:
    """Orijinal Akbank dekontunu oluşturup PDF baytları olarak döndürür"""
    if mask_identity:
        sender_vkn_tckn = "***********"
        sender_name = mask_text(sender_name)
        sender_address = "******************"
        operator_tckn = "***********"
        operator_name = mask_text(operator_name)
        if receiver_name:
            receiver_name = mask_text(receiver_name)

    doc = fitz.open()
    page = doc.new_page(width=595.0, height=842.0)
    page.insert_font(fontname="ArialCustom", fontfile=FONT_FILE)

    black = (0.0, 0.0, 0.0)

    # 1. HEADER KUTUSU
    page.draw_rect(fitz.Rect(30.0, 30.0, 565.0, 80.0), color=black, width=1.0)
    if os.path.exists(LOGO_PATH):
        page.insert_image(fitz.Rect(36.88, 46.0, 156.88, 64.0), filename=LOGO_PATH)

    qr_bytes = generate_qr_stream(qr_token)
    page.insert_image(fitz.Rect(515.0, 32.5, 560.0, 77.5), stream=qr_bytes)

    # Başlık Metinleri
    insert_text_styled(page, fitz.Point(297.5, 46.0), "DEKONT", 12.0, is_bold=True, align="center")
    title_text = transaction_title if transaction_title else "EFT BANKALAR ARASI HESABA HAVALE"
    insert_text_styled(page, fitz.Point(297.5, 69.0), title_text.upper(), 12.0, is_bold=True, align="center", max_width=330.0)

    # 2. GÖNDERİCİ & ALICI BİLGİLERİ
    page.draw_rect(fitz.Rect(30.0, 80.0, 565.0, 225.0), color=black, width=1.0)
    page.draw_line(fitz.Point(297.5, 80.0), fitz.Point(297.5, 225.0), color=black, width=1.0)

    insert_text_styled(page, fitz.Point(32.0, 93.0), "GÖNDERİCİ BİLGİLERİ", 11.0, is_bold=True)
    insert_text_styled(page, fitz.Point(299.5, 93.0), "ALICI BİLGİLERİ", 11.0, is_bold=True)

    col_w_sender = 172.0
    col_w_receiver = 172.0

    insert_text_styled(page, fitz.Point(32.0, 107.0), "Düzenleyen Şube", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(121.2, 107.0), f": {branch_name}", 10.0, is_bold=False, max_width=col_w_sender)

    insert_text_styled(page, fitz.Point(32.0, 121.0), "Borçlu Hesap No", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(121.2, 121.0), f": {sender_account_no}", 10.0, is_bold=False, max_width=col_w_sender)

    insert_text_styled(page, fitz.Point(32.0, 135.0), "Müşteri No", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(121.2, 135.0), f": {sender_customer_no}", 10.0, is_bold=False, max_width=col_w_sender)

    insert_text_styled(page, fitz.Point(32.0, 149.0), "VKN/Vergi Dairesi", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(121.2, 149.0), f": {sender_vkn_tckn}", 10.0, is_bold=False, max_width=col_w_sender)

    insert_text_styled(page, fitz.Point(32.0, 163.0), "Adı Soyadı/Unvan", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(121.2, 163.0), f": {sender_name.upper()}", 10.0, is_bold=False, max_width=col_w_sender)

    # Gönderici Adres Satırları
    insert_text_styled(page, fitz.Point(32.0, 177.0), "Adres", 10.0, is_bold=True)
    addr_lines = wrap_text(sender_address.upper(), max_width=col_w_sender - 10.0, fontsize=10.0)
    if addr_lines:
        insert_text_styled(page, fitz.Point(121.2, 177.0), f": {addr_lines[0]}", 10.0, is_bold=False)
        curr_addr_y = 187.0
        for extra_line in addr_lines[1:3]:
            insert_text_styled(page, fitz.Point(121.2, curr_addr_y), extra_line, 10.0, is_bold=False)
            curr_addr_y += 10.0

    # Alıcı Alanları
    insert_text_styled(page, fitz.Point(299.5, 121.0), "Alacaklı Hesap No", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(388.7, 121.0), f": {receiver_iban}", 10.0, is_bold=False, max_width=col_w_receiver)

    insert_text_styled(page, fitz.Point(299.5, 135.0), "Karşı Şube", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(388.7, 135.0), f":   {receiver_branch}", 10.0, is_bold=False, max_width=col_w_receiver)

    insert_text_styled(page, fitz.Point(299.5, 149.0), "VKN/Vergi Dairesi", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(388.7, 149.0), f": {receiver_vkn_tckn}" if receiver_vkn_tckn else ":", 10.0, is_bold=False, max_width=col_w_receiver)

    insert_text_styled(page, fitz.Point(299.5, 163.0), "Adı Soyadı/Unvan", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(388.7, 163.0), f": {receiver_name}", 10.0, is_bold=False, max_width=col_w_receiver)

    insert_text_styled(page, fitz.Point(299.5, 177.0), "Adres", 10.0, is_bold=True)
    rec_addr_lines = wrap_text(receiver_address.upper() if receiver_address else "", max_width=col_w_receiver - 10.0, fontsize=10.0)
    if receiver_address and rec_addr_lines:
        insert_text_styled(page, fitz.Point(388.7, 177.0), f": {rec_addr_lines[0]}", 10.0, is_bold=False)
        curr_rec_y = 187.0
        for extra_line in rec_addr_lines[1:3]:
            insert_text_styled(page, fitz.Point(388.7, curr_rec_y), extra_line, 10.0, is_bold=False)
            curr_rec_y += 10.0
    else:
        insert_text_styled(page, fitz.Point(388.7, 177.0), ":", 10.0, is_bold=False)

    # 3. IBAN KUTUSU
    page.draw_rect(fitz.Rect(30.0, 225.0, 565.0, 341.0), color=black, width=1.0)
    insert_text_styled(page, fitz.Point(32.0, 237.0), sender_iban.replace(" ", ""), 10.0, is_bold=False)

    # 4. TUTAR BİLGİLERİ (4 Sabit Kalem)
    page.draw_rect(fitz.Rect(30.0, 341.0, 565.0, 524.0), color=black, width=1.0)
    insert_text_styled(page, fitz.Point(32.0, 354.0), "TUTAR BİLGİLERİ", 11.0, is_bold=True)

    amt_str = format_tr_currency(amount)
    sch_val = sch_amount if (sch_amount is not None and sch_amount > 0) else 1.00
    comm_val = commission if (commission is not None and commission > 0) else 7.97
    bsmv_val = bsmv if (bsmv is not None and bsmv > 0) else 0.40

    sch_str = format_tr_currency(sch_val)
    comm_str = format_tr_currency(comm_val)
    bsmv_str = format_tr_currency(bsmv_val)

    items = [
        ("MEVDUAT", f"{amt_str}  TL", "0,00  TL"),
        ("ŞCH", "0,00  TL", f"{sch_str}  TL"),
        ("GECEFT KOMİSYON", "0,00  TL", f"{comm_str}  TL"),
        ("GEC EFT BSMV", "0,00  TL", f"{bsmv_str}  TL"),
    ]

    row_y = 368.0
    for title, col1, col2 in items:
        insert_text_styled(page, fitz.Point(32.0, row_y), title, 10.0, is_bold=False)
        insert_text_styled(page, fitz.Point(385.0, row_y), col1, 10.0, is_bold=False, align="right")
        insert_text_styled(page, fitz.Point(563.0, row_y), col2, 10.0, is_bold=False, align="right")
        row_y += 14.0

    grand_total = float(amount) + float(sch_val or 0.0) + float(comm_val or 0.0) + float(bsmv_val or 0.0)
    total_val_str = format_tr_currency(grand_total)
    insert_text_styled(page, fitz.Point(32.0, 508.0), "TOPLAM", 10.0, is_bold=False)
    insert_text_styled(page, fitz.Point(563.0, 508.0), f"{total_val_str} TL", 10.0, is_bold=False, align="right")

    words_turkish = convert_to_turkish_words(grand_total)
    insert_text_styled(page, fitz.Point(32.0, 522.0), words_turkish, 10.0, is_bold=False, max_width=525.0)

    # 5. AYIRICI BOŞ KUTU
    page.draw_rect(fitz.Rect(30.0, 524.0, 565.0, 592.0), color=black, width=1.0)

    # 6. İŞLEM DETAYLARI & MÜŞTERİ İMZASI
    page.draw_rect(fitz.Rect(30.0, 592.0, 565.0, 690.0), color=black, width=1.0)
    page.draw_line(fitz.Point(297.5, 592.0), fitz.Point(297.5, 690.0), color=black, width=1.0)
    page.draw_line(fitz.Point(297.5, 606.0), fitz.Point(565.0, 606.0), color=black, width=1.0)

    insert_text_styled(page, fitz.Point(299.5, 604.0), "MÜŞTERİ İMZASI", 10.0, is_bold=True)

    max_w_dt = 127.0
    insert_text_styled(page, fitz.Point(32.0, 604.0), "İşlem Tarihi/Saati", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(165.8, 604.0), f": {date_str} {time_str}", 10.0, is_bold=False, max_width=max_w_dt)

    insert_text_styled(page, fitz.Point(32.0, 618.0), "Valör", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(165.8, 618.0), f": {valor_str}", 10.0, is_bold=False, max_width=max_w_dt)

    insert_text_styled(page, fitz.Point(32.0, 632.0), "Referans", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(165.8, 632.0), f": {reference_no}" if reference_no else ":", 10.0, is_bold=False, max_width=max_w_dt)

    insert_text_styled(page, fitz.Point(32.0, 646.0), "İşlemi Yapan", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(165.8, 646.0), f": {operator}", 10.0, is_bold=False, max_width=max_w_dt)

    insert_text_styled(page, fitz.Point(32.0, 660.0), "İşlemi Yapan Ad-Soyad", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(165.8, 660.0), f": {operator_name.upper()}", 10.0, is_bold=False, max_width=max_w_dt)

    insert_text_styled(page, fitz.Point(32.0, 674.0), "İşlemi Yapan TCKN", 10.0, is_bold=True)
    insert_text_styled(page, fitz.Point(165.8, 674.0), f": {operator_tckn}", 10.0, is_bold=False, max_width=max_w_dt)

    insert_text_styled(page, fitz.Point(32.0, 688.0), channel_code, 10.0, is_bold=True)

    # 7. ALT BİLGİ & YETKİLİ İMZASI
    page.draw_rect(fitz.Rect(30.0, 690.0, 565.0, 760.0), color=black, width=1.0)
    page.draw_line(fitz.Point(297.5, 690.0), fitz.Point(297.5, 760.0), color=black, width=1.0)

    insert_text_styled(page, fitz.Point(299.5, 702.0), "YETKİLİ İMZASI", 10.0, is_bold=True)

    insert_text_styled(page, fitz.Point(32.0, 698.0), "Akbank T.A.Ş.", 6.0, is_bold=False)
    insert_text_styled(page, fitz.Point(180.6, 698.0), "Vergi Dairesi: Büyük Mükellefler", 6.0, is_bold=False)

    insert_text_styled(page, fitz.Point(32.0, 712.0), "Genel Müdürlük: Sabancı Center 4.Levent 34330", 6.0, is_bold=False)
    insert_text_styled(page, fitz.Point(180.6, 712.0), "Vergi No: 0150015264", 6.0, is_bold=False)

    insert_text_styled(page, fitz.Point(32.0, 726.0), "İstanbul", 6.0, is_bold=False)
    insert_text_styled(page, fitz.Point(180.6, 726.0), "www.akbank.com", 6.0, is_bold=False)

    insert_text_styled(page, fitz.Point(32.0, 740.0), "Mersis No: 0015001526400497", 6.0, is_bold=False)

    doc.set_metadata({
        "format": "PDF 1.4",
        "title": "Akbank Dekont",
        "author": "Akbank",
        "producer": "OpenPDF 1.2.3.java7",
        "creationDate": fitz.get_pdf_now(),
    })

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def generate_transaction_receipt_pdf(tx, mask_identity: bool = False) -> bytes:
    """Verilen Transaction model nesnesi için dekont PDF baytlarını oluşturur"""
    customer = tx.customer
    date_formatted = tx.transaction_date.strftime("%d.%m.%Y")
    time_formatted = tx.transaction_time.strftime("%H:%M:%S")
    valor_formatted = tx.valor_date.strftime("%d.%m.%Y") if tx.valor_date else date_formatted

    return generate_akbank_pdf_bytes(
        transaction_title="EFT BANKALAR ARASI HESABA HAVALE",
        branch_name=customer.branch_name,
        sender_account_no=customer.account_no,
        sender_customer_no=customer.customer_no,
        sender_vkn_tckn=customer.tc_no,
        sender_name=customer.full_name,
        sender_address=customer.address,
        sender_iban=customer.iban,
        receiver_iban=tx.receiver_iban,
        receiver_branch=tx.receiver_branch or "-",
        receiver_vkn_tckn=tx.receiver_vkn_tckn,
        receiver_name=tx.receiver_name,
        receiver_address=tx.receiver_address,
        amount=float(tx.amount),
        sch_amount=float(tx.sch_amount) if tx.sch_amount else 1.00,
        commission=float(tx.commission) if tx.commission else 7.97,
        bsmv=float(tx.bsmv) if tx.bsmv else 0.40,
        date_str=date_formatted,
        time_str=time_formatted,
        valor_str=valor_formatted,
        reference_no=tx.reference_no,
        operator=tx.operator or "KENDISI",
        operator_name=tx.operator_name or customer.full_name,
        operator_tckn=tx.operator_tckn or customer.tc_no,
        channel_code=tx.channel_code if (tx.channel_code and tx.channel_code != "40033406 / 554193 /") else f"{str(customer.customer_no).lstrip('0')} / 554193 /",
        qr_token=tx.qr_token or "OZDM6v57aYB601",
        mask_identity=mask_identity,
    )

def render_pdf_to_png(pdf_bytes: bytes, dpi: int = 180) -> bytes:
    """PDF baytlarını yüksek çözünürlüklü PNG görseline dönüştürür"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes


import os
from decimal import Decimal
import fitz

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets", "statement")
TEMPLATE_PDF = os.path.join(ASSETS_DIR, "statement_template.pdf")
IMG_TITLE = os.path.join(ASSETS_DIR, "header_title.png")
IMG_SUBTITLE = os.path.join(ASSETS_DIR, "header_subtitle.png")
IMG_AKBANK = os.path.join(ASSETS_DIR, "header_akbank.png")
IMG_FOOTER_INFO = os.path.join(ASSETS_DIR, "footer_info.png")
IMG_SEE_BACK = os.path.join(ASSETS_DIR, "footer_see_back.png")
IMG_SIZIN_ICIN = os.path.join(ASSETS_DIR, "footer_sizin_icin.png")

def resolve_font(filename, fallback_filename="arial_narrow.ttf"):
    # 1. Windows font dir
    win_dir = os.environ.get("WINDIR", "C:\\Windows")
    p = os.path.join(win_dir, "Fonts", filename)
    if os.path.exists(p):
        return p
    # 2. Linux common font locations
    is_bold = "bd" in filename.lower() or "bold" in filename.lower()
    linux_paths = [
        f"/usr/share/fonts/truetype/msttcorefonts/{filename}",
        f"/usr/share/fonts/truetype/liberation/LiberationSans-{'Bold' if is_bold else 'Regular'}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if is_bold else ''}.ttf",
    ]
    for lp in linux_paths:
        if os.path.exists(lp):
            return lp
    # 3. Project assets fallback
    local_asset = os.path.join(os.path.dirname(__file__), "assets", fallback_filename)
    if os.path.exists(local_asset):
        return local_asset
    return filename

FONT_REGULAR = resolve_font("arial.ttf")
FONT_BOLD = resolve_font("arialbd.ttf")

AKBANK_RED = (0.863, 0.0, 0.102)   # #DC001A
TEXT_BLACK = (0.0, 0.0, 0.0)
LINE_BLACK = (0.0, 0.0, 0.0)

TURKISH_MONTHS = [
    "OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN",
    "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"
]

def format_curr(val):
    if val is None:
        return "0.00"
    val = Decimal(str(val))
    is_neg = val < 0
    abs_val = abs(val)
    formatted = f"{abs_val:,.2f}"
    return f"-{formatted}" if is_neg else formatted

def build_statement_pdf(customer_data, transactions, statement_meta=None):
    """
    Generates a 2-page PDF identical to the original Akbank Account Statement.
    """
    if statement_meta is None:
        statement_meta = {}

    doc = fitz.open()
    # A4 dimensions: 595.2 x 841.68 pt
    p1 = doc.new_page(width=595.2, height=841.68)

    # Load font objects for text length calculations
    f_reg_obj = fitz.Font(fontfile=FONT_REGULAR)
    f_bold_obj = fitz.Font(fontfile=FONT_BOLD)

    # Insert fonts into page
    f_reg = "Arial"
    f_bold = "Arial-Bold"
    p1.insert_font(fontname=f_reg, fontfile=FONT_REGULAR)
    p1.insert_font(fontname=f_bold, fontfile=FONT_BOLD)

    # 1. Header Images
    if os.path.exists(IMG_TITLE):
        p1.insert_image(fitz.Rect(42.24, 4.08, 249.60, 24.72), filename=IMG_TITLE)
    
    # Red separator line: Rect(41.76, 21.84, 244.08, 22.80)
    p1.draw_rect(fitz.Rect(41.76, 21.84, 244.08, 22.80), color=None, fill=(0.837, 0.090, 0.176))

    if os.path.exists(IMG_SUBTITLE):
        p1.insert_image(fitz.Rect(42.72, 25.92, 227.04, 38.88), filename=IMG_SUBTITLE)

    if os.path.exists(IMG_AKBANK):
        p1.insert_image(fitz.Rect(437.04, 13.44, 582.96, 28.80), filename=IMG_AKBANK)

    # 2. Customer Name & Address (Left block)
    full_name = customer_data.get("full_name", "SERKAN YILDIRIM").upper()
    p1.insert_text(fitz.Point(62.4, 73.2), f"Sayın {full_name}", fontname=f_bold, fontsize=8.5, color=TEXT_BLACK)

    # Address lines
    raw_address = customer_data.get("address", "")
    address_lines = customer_data.get("address_lines")
    if not address_lines:
        if raw_address:
            address_lines = [l.strip() for l in raw_address.split("\n") if l.strip()]
        else:
            address_lines = [
                "AYDINLI MAH.",
                "BARIŞ CAD.",
                "NO:14 D:5",
                "34953 TUZLA İSTANBUL"
            ]

    addr_y = [83.5, 97.0, 108.5, 120.0, 131.8]
    for idx, line in enumerate(address_lines[:5]):
        y_pos = addr_y[idx] if idx < len(addr_y) else 131.8 + idx * 11.5
        p1.insert_text(fitz.Point(62.4, y_pos), line, fontname=f_reg, fontsize=8.2, color=TEXT_BLACK)

    # 3. Right Block: Period & Customer Metadata
    period_str = statement_meta.get("period", "EYLÜL 2026").upper()
    w_per = f_bold_obj.text_length(period_str, fontsize=10.0)
    p1.insert_text(fitz.Point(max(340.0, 581.0 - w_per), 76.3), period_str, fontname=f_bold, fontsize=10.0, color=TEXT_BLACK)

    customer_no = customer_data.get("customer_no", "0071948201")
    branch_name = customer_data.get("branch_name", "1277- TUZLA İÇMELER")
    vkn = customer_data.get("tc_no", "39182746192")

    meta_items = [
        ("Müşteri No", customer_no, 90.2),
        ("Şube", branch_name, 100.6),
        ("Vergi Kimlik No", vkn, 108.5),
    ]
    for label, val, y_pos in meta_items:
        p1.insert_text(fitz.Point(345.8, y_pos), label, fontname=f_reg, fontsize=8.0, color=TEXT_BLACK)
        p1.insert_text(fitz.Point(430.8, y_pos), ":", fontname=f_reg, fontsize=8.0, color=TEXT_BLACK)
        p1.insert_text(fitz.Point(436.8, y_pos), str(val), fontname=f_reg, fontsize=8.0, color=TEXT_BLACK)

    # 4. Red Header Bar
    p1.draw_rect(fitz.Rect(42.48, 223.20, 581.04, 245.76), color=None, fill=(0.860, 0.101, 0.129))
    p1.insert_text(fitz.Point(340.0, 239.5), "VADESİZ HESAP HAREKETLERİNİZ", fontname=f_bold, fontsize=9.2, color=(1.0, 1.0, 1.0))

    # 5. Sub-header & Account Details Box
    p1.insert_text(fitz.Point(42.5, 254.0), "VADESİZ TL HESABI", fontname=f_bold, fontsize=7.8, color=TEXT_BLACK)

    account_no = customer_data.get("account_no", "0076358")
    iban = customer_data.get("iban", "TR97 0004 6012 7788 8000 0763 58")
    overdraft_limit = customer_data.get("overdraft_limit", Decimal("115500.00"))
    available_overdraft = customer_data.get("available_overdraft_limit", Decimal("115500.00"))
    interest_rate = customer_data.get("overdraft_interest_rate", Decimal("4.25"))
    late_interest = customer_data.get("overdraft_late_interest_rate", Decimal("4.55"))
    next_stmt_date = customer_data.get("next_statement_date", "31.10.2026")
    prev_month_overdraft = customer_data.get("prev_month_overdraft", Decimal("0.00"))

    # Left account details
    p1.insert_text(fitz.Point(42.5, 265.0), f"Hesap No: {account_no}", fontname=f_reg, fontsize=7.6, color=TEXT_BLACK)
    p1.insert_text(fitz.Point(42.5, 274.0), f"Şube : {branch_name}", fontname=f_reg, fontsize=7.6, color=TEXT_BLACK)
    p1.insert_text(fitz.Point(42.5, 283.0), f"IBAN : {iban}", fontname=f_reg, fontsize=7.6, color=TEXT_BLACK)

    # Right Artı Para details
    right_labels = [
        ("Artı Para Limiti", format_curr(overdraft_limit), 265.0),
        ("Kullanılabilir Artı Para Limiti", format_curr(available_overdraft), 274.0),
        ("Artı Para Akdi Faiz Oranı (Aylık)", f"% {Decimal(str(interest_rate)):.2f}", 283.0),
        ("Gecikme Faizi Oranı", f"% {Decimal(str(late_interest)):.2f}", 292.0),
        ("Bir Sonraki Ekstre Tarihi", str(next_stmt_date), 301.0),
        ("Önceki Aydan Devreden", format_curr(prev_month_overdraft), 310.0),
    ]
    for label, val, y_pos in right_labels:
        p1.insert_text(fitz.Point(297.6, y_pos), label, fontname=f_reg, fontsize=7.6, color=TEXT_BLACK)
        p1.insert_text(fitz.Point(427.9, y_pos), ":", fontname=f_reg, fontsize=7.6, color=TEXT_BLACK)
        val_w = f_reg_obj.text_length(val, fontsize=7.6)
        p1.insert_text(fitz.Point(581.0 - val_w, y_pos), val, fontname=f_reg, fontsize=7.6, color=TEXT_BLACK)

    # 6. Table Header
    p1.insert_text(fitz.Point(42.5, 328.0), "İşlem Tarihi", fontname=f_bold, fontsize=7.8, color=TEXT_BLACK)
    p1.insert_text(fitz.Point(87.8, 328.0), "Dönem İçi İşlemler", fontname=f_bold, fontsize=7.8, color=TEXT_BLACK)
    p1.insert_text(fitz.Point(402.5, 324.0), "Kullanılan Artı", fontname=f_bold, fontsize=7.8, color=TEXT_BLACK)
    p1.insert_text(fitz.Point(402.5, 332.5), "Para", fontname=f_bold, fontsize=7.8, color=TEXT_BLACK)

    w_tut = f_bold_obj.text_length("İşlem Tutarı", fontsize=7.8)
    p1.insert_text(fitz.Point(518.0 - w_tut, 328.0), "İşlem Tutarı", fontname=f_bold, fontsize=7.8, color=TEXT_BLACK)

    w_bak = f_bold_obj.text_length("Hesap Bakiyesi", fontsize=7.8)
    p1.insert_text(fitz.Point(581.0 - w_bak, 328.0), "Hesap Bakiyesi", fontname=f_bold, fontsize=7.8, color=TEXT_BLACK)

    # 7. Table Rows
    curr_y = 343.2
    row_height = 8.4

    # Row 0: Önceki Aydan Devreden / Önceki Dönemden Devreden
    opening_label = statement_meta.get("opening_label", "Önceki Aydan Devreden")
    init_balance = statement_meta.get("initial_balance", customer_data.get("initial_balance", Decimal("5024.41")))
    p1.insert_text(fitz.Point(87.8, curr_y), opening_label, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)
    init_bal_str = format_curr(init_balance)
    w_ib = f_reg_obj.text_length(init_bal_str, fontsize=7.4)
    p1.insert_text(fitz.Point(581.0 - w_ib, curr_y), init_bal_str, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)
    curr_y += row_height

    # Transactions
    for tx in transactions:
        tx_date = tx.get("date", "")
        tx_desc = tx.get("desc", "")
        tx_used_od = tx.get("used_overdraft", Decimal("0.00"))
        tx_amount = tx.get("amount", Decimal("0.00"))
        tx_is_credit = tx.get("is_credit", False)
        tx_balance = tx.get("balance", Decimal("0.00"))

        p1.insert_text(fitz.Point(42.5, curr_y), tx_date, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)

        # Truncate description gracefully if it exceeds column width (~305 pt)
        if f_reg_obj.text_length(tx_desc, fontsize=7.4) > 305:
            while len(tx_desc) > 10 and f_reg_obj.text_length(tx_desc + "..", fontsize=7.4) > 305:
                tx_desc = tx_desc[:-1]
            tx_desc = tx_desc + ".."
        p1.insert_text(fitz.Point(87.8, curr_y), tx_desc, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)

        # Used Overdraft
        if tx_used_od and Decimal(str(tx_used_od)) > Decimal("0.00"):
            od_str = format_curr(tx_used_od)
            w_od = f_reg_obj.text_length(od_str, fontsize=7.4)
            p1.insert_text(fitz.Point(448.0 - w_od, curr_y), od_str, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)

        # Amount
        amt_decimal = Decimal(str(tx_amount))
        if not tx_is_credit:
            amt_decimal = -abs(amt_decimal)
        else:
            amt_decimal = abs(amt_decimal)
        amt_str = format_curr(amt_decimal)
        w_amt = f_reg_obj.text_length(amt_str, fontsize=7.4)
        p1.insert_text(fitz.Point(518.0 - w_amt, curr_y), amt_str, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)

        # Balance
        bal_str = format_curr(tx_balance)
        w_bal = f_reg_obj.text_length(bal_str, fontsize=7.4)
        p1.insert_text(fitz.Point(581.0 - w_bal, curr_y), bal_str, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)

        curr_y += row_height

    # Dönem Sonu / Aysonu Hesap Bakiyesi
    curr_y += 1.5
    closing_label = statement_meta.get("closing_label", "Aysonu Hesap Bakiyesi")
    final_balance = statement_meta.get("final_balance", customer_data.get("current_balance", Decimal("2097.00")))
    p1.insert_text(fitz.Point(87.8, curr_y), closing_label, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)
    fin_bal_str = format_curr(final_balance)
    w_fb = f_reg_obj.text_length(fin_bal_str, fontsize=7.4)
    p1.insert_text(fitz.Point(581.0 - w_fb, curr_y), fin_bal_str, fontname=f_reg, fontsize=7.4, color=TEXT_BLACK)

    # 8. Divider line above announcement box
    p1.draw_rect(fitz.Rect(42.48, 544.56, 581.04, 545.20), color=None, fill=LINE_BLACK)

    # 9. Announcement Box
    announcement_text = (
        "Değerli Akbanklı, Temmuz 2026 tarihinden itibaren geçerli olacak şekilde "
        "Artı Para'nıza ait her ayın 15'i olan son ödeme tarihi, Artı Para Ekstre Kesim Tarihini "
        "(her ayın son takvim günü) takip eden ayın son takvim günü olarak güncellendi. "
        "Bu değişiklik sözleşme güncellemesi niteliğindedir."
    )
    ann_rect = fitz.Rect(42.48, 554.0, 581.04, 605.0)
    p1.insert_textbox(ann_rect, announcement_text, fontname=f_bold, fontsize=8.6, color=TEXT_BLACK, align=fitz.TEXT_ALIGN_LEFT)

    # Divider line below announcement box
    p1.draw_rect(fitz.Rect(42.48, 608.40, 581.04, 609.00), color=None, fill=LINE_BLACK)

    # 10. Footer Section
    if os.path.exists(IMG_SEE_BACK):
        p1.insert_image(fitz.Rect(415.20, 791.76, 515.04, 799.44), filename=IMG_SEE_BACK)

    p1.insert_text(fitz.Point(536.2, 798.0), "Sayfa 1/2", fontname=f_reg, fontsize=8.0, color=TEXT_BLACK)

    if os.path.exists(IMG_FOOTER_INFO):
        p1.insert_image(fitz.Rect(23.28, 817.92, 430.32, 827.04), filename=IMG_FOOTER_INFO)

    if os.path.exists(IMG_SIZIN_ICIN):
        p1.insert_image(fitz.Rect(496.56, 814.56, 573.36, 827.28), filename=IMG_SIZIN_ICIN)

    # 11. Page 2: Exact copy of Page 2 from template PDF
    if os.path.exists(TEMPLATE_PDF):
        tpl_doc = fitz.open(TEMPLATE_PDF)
        if len(tpl_doc) > 1:
            p2 = doc.new_page(width=595.2, height=841.68)
            p2.show_pdf_page(p2.rect, tpl_doc, 1)

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes

def generate_account_statement_pdf(customer, month=9, year=2026, period_filter='1m'):
    """
    High-level generator taking a Django Customer model instance.
    period_filter options:
      - '1d' / '1_day' / '1gun' -> Son 1 Gün (Günlük ekstre)
      - '1w' / '1_week' / '1hafta' -> Son 1 Hafta (Haftalık ekstre)
      - '1m' / '1_month' / '1ay' -> 1 Aylık Dönem (Varsayılan tüm ay)
    """
    import datetime
    period_filter = str(period_filter or '1m').lower().strip()
    month = int(month or 9)
    year = int(year or 2026)
    month_name = TURKISH_MONTHS[(month - 1) % 12]

    # Get latest transaction across all customer transactions
    latest_tx = customer.transactions.order_by('transaction_date', 'transaction_time', 'id').last()
    
    if period_filter in ('all', 'tumu', 'hepsi'):
        target_txs = list(customer.transactions.all().order_by('transaction_date', 'transaction_time', 'id'))
        opening_balance = customer.initial_balance
        final_balance = target_txs[-1].balance_after if target_txs else customer.current_balance
        first_d = target_txs[0].transaction_date.strftime('%d.%m.%Y') if target_txs else '01.01.2026'
        last_d = target_txs[-1].transaction_date.strftime('%d.%m.%Y') if target_txs else '31.12.2026'
        period_title = f"{first_d} - {last_d} (TÜM İŞLEMLER)"
        opening_label = "Dönem Başı Hesap Bakiyesi"
        closing_label = "Güncel Hesap Bakiyesi"

    elif period_filter in ('1d', '1_day', '1gun', 'day', 'daily'):
        # 1 Günlük ekstre: En son işlem günü
        target_date = latest_tx.transaction_date if latest_tx else datetime.date(year, month, 30)
        target_txs = list(customer.transactions.filter(transaction_date=target_date).order_by('transaction_date', 'transaction_time', 'id'))
        
        # Önceki gün bakiyesi: Bu günden önceki son işlemin balance_after'ı veya initial_balance
        prev_tx = customer.transactions.filter(transaction_date__lt=target_date).order_by('transaction_date', 'transaction_time', 'id').last()
        opening_balance = prev_tx.balance_after if prev_tx else customer.initial_balance
        
        final_balance = target_txs[-1].balance_after if target_txs else opening_balance
        period_title = f"{target_date.strftime('%d.%m.%Y')} (1 GÜN)"
        opening_label = "Önceki Günden Devreden"
        closing_label = "Gün Sonu Hesap Bakiyesi"

    elif period_filter in ('1w', '1_week', '1hafta', 'week', 'weekly'):
        # 1 Haftalık ekstre: Son 7 gün
        max_date = latest_tx.transaction_date if latest_tx else datetime.date(year, month, 30)
        start_date = max_date - datetime.timedelta(days=6)
        target_txs = list(customer.transactions.filter(transaction_date__gte=start_date, transaction_date__lte=max_date).order_by('transaction_date', 'transaction_time', 'id'))
        
        prev_tx = customer.transactions.filter(transaction_date__lt=start_date).order_by('transaction_date', 'transaction_time', 'id').last()
        opening_balance = prev_tx.balance_after if prev_tx else customer.initial_balance

        final_balance = target_txs[-1].balance_after if target_txs else opening_balance
        period_title = f"{start_date.strftime('%d.%m')} - {max_date.strftime('%d.%m.%Y')} (1 HAFTA)"
        opening_label = "Önceki Dönemden Devreden"
        closing_label = "Dönem Sonu Hesap Bakiyesi"

    else:
        # 1 Aylık ekstre (Varsayılan)
        all_month_qs = customer.transactions.filter(
            transaction_date__year=year,
            transaction_date__month=month
        ).order_by('transaction_date', 'transaction_time', 'id')
        if not all_month_qs.exists():
            all_month_qs = customer.transactions.all().order_by('transaction_date', 'transaction_time', 'id')
        
        target_txs = list(all_month_qs)
        prev_tx = customer.transactions.filter(transaction_date__year=year, transaction_date__month__lt=month).order_by('transaction_date', 'transaction_time', 'id').last()
        if not prev_tx:
            prev_tx = customer.transactions.filter(transaction_date__year__lt=year).order_by('transaction_date', 'transaction_time', 'id').last()
        opening_balance = prev_tx.balance_after if prev_tx else customer.initial_balance
        final_balance = target_txs[-1].balance_after if target_txs else customer.current_balance
        period_title = f"{month_name} {year}"
        opening_label = "Önceki Aydan Devreden"
        closing_label = "Aysonu Hesap Bakiyesi"

    formatted_txs = []
    import re
    for tx in target_txs:
        date_str = tx.transaction_date.strftime("%d.%m.%Y")
        
        # Açıklama metnini belirle: Numara-İsim-, EFT KOMİSYONU, EFT BSMV formatları
        raw_desc = (tx.description or "").strip()
        if raw_desc and (
            re.match(r'^\d{3,}-\S+', raw_desc)
            or raw_desc.startswith('FAST:')
            or raw_desc.startswith('EFT:')
            or raw_desc.startswith('HAVALE:')
            or raw_desc in ('EFT KOMİSYONU', 'EFT BSMV')
            or 'KOMİSYON' in raw_desc.upper()
            or 'BSMV' in raw_desc.upper()
        ):
            desc = raw_desc
        elif not tx.is_credit and tx.receiver_name:
            ref = tx.reference_no.strip() if tx.reference_no else "0943604"
            if len(ref) < 7 and ref.isdigit():
                ref = f"{int(ref):07d}"
            extra = raw_desc if raw_desc and raw_desc != tx.receiver_name.strip() else ""
            desc = f"{ref}-{tx.receiver_name.strip()}-{extra}" if extra else f"{ref}-{tx.receiver_name.strip()}-"
        elif tx.is_credit and tx.receiver_name:
            tx_type_upper = (tx.transaction_type or '').upper()
            prefix = 'FAST' if 'FAST' in tx_type_upper else ('EFT' if 'EFT' in tx_type_upper else ('HAVALE' if 'HAVALE' in tx_type_upper else 'FAST'))
            sender_upper = tx.receiver_name.strip().replace('i', 'İ').replace('ı', 'I').upper()
            desc = f"{prefix}:{sender_upper}"
        elif raw_desc:
            desc = raw_desc
        elif tx.receiver_name:
            desc = tx.receiver_name.strip()
        else:
            desc = tx.transaction_type

        formatted_txs.append({
            "date": date_str,
            "desc": desc,
            "used_overdraft": tx.used_overdraft,
            "amount": tx.amount,
            "is_credit": tx.is_credit,
            "balance": tx.balance_after,
        })

    next_st_date = customer.next_statement_date.strftime("%d.%m.%Y") if customer.next_statement_date else "31.10.2026"

    addr = customer.address or "BAĞLIK MAH. GÖDENE CAD. NO:103 D:23 07000 KUMLUCA ANTALYA"
    addr_lines = [l.strip() for l in addr.split("\n") if l.strip()]
    if len(addr_lines) <= 1:
        words = addr.split()
        addr_lines = []
        cur = []
        for w in words:
            cur.append(w)
            if len(" ".join(cur)) > 20:
                addr_lines.append(" ".join(cur))
                cur = []
        if cur:
            addr_lines.append(" ".join(cur))

    customer_data = {
        "full_name": customer.full_name,
        "customer_no": customer.customer_no,
        "branch_name": customer.branch_name,
        "tc_no": customer.tc_no,
        "account_no": customer.account_no,
        "iban": customer.iban,
        "initial_balance": opening_balance,
        "current_balance": final_balance,
        "overdraft_limit": customer.overdraft_limit,
        "available_overdraft_limit": customer.available_overdraft_limit,
        "overdraft_interest_rate": customer.overdraft_interest_rate,
        "overdraft_late_interest_rate": customer.overdraft_late_interest_rate,
        "next_statement_date": next_st_date,
        "prev_month_overdraft": Decimal("0.00"),
        "address_lines": addr_lines,
    }

    statement_meta = {
        "period": period_title,
        "opening_label": opening_label,
        "closing_label": closing_label,
        "initial_balance": opening_balance,
        "final_balance": final_balance,
    }

    return build_statement_pdf(customer_data, formatted_txs, statement_meta=statement_meta)

def render_statement_png(pdf_bytes, page_num=0, dpi=180):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()
    return png_bytes

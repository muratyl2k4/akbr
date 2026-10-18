import fitz

doc = fitz.open('backend/bank/assets/statement/statement_template.pdf')
p1 = doc[0]

blocks = p1.get_text('dict')['blocks']
text_blocks = [b for b in blocks if b.get('type') == 0]

lines_decoded = []
for b in text_blocks:
    for l in b['lines']:
        line_str = ''
        for s in l['spans']:
            raw_text = s['text']
            raw_bytes = bytes([ord(c) if ord(c) < 256 else 0x40 for c in raw_text])
            decoded = raw_bytes.decode('cp1026', errors='replace')
            line_str += decoded
        lines_decoded.append({
            'bbox': [round(x, 2) for x in l['bbox']],
            'text': line_str,
        })

lines_decoded.sort(key=lambda item: (item['bbox'][1], item['bbox'][0]))

grouped_lines = []
curr_y = None
curr_group = []
for item in lines_decoded:
    y = item['bbox'][1]
    if curr_y is None or abs(y - curr_y) > 3.0:
        if curr_group:
            grouped_lines.append(curr_group)
        curr_group = [item]
        curr_y = y
    else:
        curr_group.append(item)
if curr_group:
    grouped_lines.append(curr_group)

with open('backend/bank/p1_lines_all.txt', 'w', encoding='utf-8') as out_f:
    for grp in grouped_lines:
        y = grp[0]['bbox'][1]
        grp.sort(key=lambda it: it['bbox'][0])
        parts = []
        for it in grp:
            t = it['text'].strip()
            if t:
                parts.append(f"({it['bbox'][0]:.1f}) {t}")
        if parts:
            out_f.write(f"y={y:5.1f} => " + "  |  ".join(parts) + "\n")

print("Done writing p1_lines_all.txt")

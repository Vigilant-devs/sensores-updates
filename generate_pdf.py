#!/usr/bin/env python3
"""
Gera PDF profissional a partir de ROTEIRO-TESTES.md
"""
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import ParagraphStyle

PAGE_W, PAGE_H = A4
MARGIN_L = 2.2 * cm
MARGIN_R = 2.2 * cm
MARGIN_T = 2.8 * cm
MARGIN_B = 2.5 * cm

# ---- Paleta: preto sobre branco ----
BLACK    = colors.HexColor("#000000")
WHITE    = colors.HexColor("#FFFFFF")
ACCENT   = colors.HexColor("#1A2540")   # azul-marinho escuro
ACCENT2  = colors.HexColor("#2E4272")   # azul-marinho médio
CODE_BG  = colors.HexColor("#EEF2FF")   # azul muito claro
TABLE_HDR = colors.HexColor("#1A2540")
TABLE_ALT = colors.HexColor("#EEF2FF")
BORDER   = colors.HexColor("#1A2540")


def build_styles():
    s = {}
    s['h3'] = ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=10,
        leading=14, textColor=BLACK, spaceBefore=12, spaceAfter=4)
    s['body'] = ParagraphStyle('body', fontName='Helvetica', fontSize=9,
        leading=13, textColor=BLACK, spaceAfter=5)
    s['bullet'] = ParagraphStyle('bullet', fontName='Helvetica', fontSize=9,
        leading=13, textColor=BLACK, spaceAfter=3, leftIndent=14,
        bulletIndent=2, bulletText='\u2022')
    s['subbullet'] = ParagraphStyle('subbullet', fontName='Helvetica', fontSize=9,
        leading=13, textColor=BLACK, spaceAfter=2, leftIndent=28,
        bulletIndent=16, bulletText='\u2013')
    s['note'] = ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=8.5,
        leading=12, textColor=BLACK, spaceAfter=5, leftIndent=10)
    s['tbl_hdr'] = ParagraphStyle('tbl_hdr', fontName='Helvetica-Bold', fontSize=8,
        leading=10, textColor=WHITE)
    s['tbl_cell'] = ParagraphStyle('tbl_cell', fontName='Courier', fontSize=7.5,
        leading=10, textColor=BLACK)
    s['tbl_cell_plain'] = ParagraphStyle('tbl_cell_plain', fontName='Helvetica',
        fontSize=8, leading=10, textColor=BLACK)
    return s


class HeaderBanner(Flowable):
    def __init__(self, text, width):
        super().__init__()
        self.text = text
        self.bwidth = width
        self.height = 44

    def draw(self):
        c = self.canv
        c.setFillColor(ACCENT)
        c.rect(0, 0, self.bwidth, self.height, fill=1, stroke=0)
        c.setFillColor(ACCENT2)
        c.rect(0, 0, 6, self.height, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 16)
        c.drawString(14, 14, self.text)

    def wrap(self, *args):
        return (self.bwidth, self.height)


class SectionBanner(Flowable):
    def __init__(self, text, width):
        super().__init__()
        self.text = text
        self.bwidth = width
        self.height = 22

    def draw(self):
        c = self.canv
        c.setFillColor(ACCENT2)
        c.rect(0, 0, self.bwidth, self.height, fill=1, stroke=0)
        c.setFillColor(ACCENT)
        c.rect(0, 0, 4, self.height, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(10, 7, self.text)

    def wrap(self, *args):
        return (self.bwidth, self.height)


class CodeBlock(Flowable):
    def __init__(self, lines, width):
        super().__init__()
        self.lines = lines
        self.bwidth = width
        self.padding = 8
        self.line_h = 11
        self.height = len(lines) * self.line_h + self.padding * 2

    def draw(self):
        c = self.canv
        h = self.height
        c.setFillColor(CODE_BG)
        c.rect(0, 0, self.bwidth, h, fill=1, stroke=0)
        c.setFillColor(ACCENT2)
        c.rect(0, 0, 3, h, fill=1, stroke=0)
        c.setStrokeColor(ACCENT2)
        c.setLineWidth(0.5)
        c.rect(0, 0, self.bwidth, h, fill=0, stroke=1)
        c.setFillColor(BLACK)
        c.setFont('Courier', 7.5)
        for i, line in enumerate(self.lines):
            y = h - self.padding - (i + 1) * self.line_h + 2
            # clip long lines
            if len(line) > 120:
                line = line[:117] + '...'
            c.drawString(10, y, line)

    def wrap(self, avail_w, avail_h):
        return (self.bwidth, self.height)


def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # header
    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 1.5 * cm, w, 1.5 * cm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(MARGIN_L, h - 0.95 * cm, "Vigilant NDR \u2014 Sensor Update System")
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(w - MARGIN_R, h - 0.95 * cm, "Roteiro de Testes  |  v2.0.3")
    # footer
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, w, 1.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(MARGIN_L, 0.45 * cm, "Confidencial \u2014 uso interno")
    canvas.drawRightString(w - MARGIN_R, 0.45 * cm, f"P\u00e1gina {doc.page}")
    canvas.restoreState()


def escape_xml(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def inline_format(text):
    # Extract code spans first to protect underscores/asterisks inside them
    code_spans = []
    def save_code(m):
        idx = len(code_spans)
        raw = escape_xml(m.group(1))
        code_spans.append(f'<font name="Courier" size="8"><b>{raw}</b></font>')
        return f'\x00CODE{idx}\x00'
    text = re.sub(r'`([^`]+)`', save_code, text)

    text = escape_xml(text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
    text = re.sub(r'\*([^*\n]+?)\*', r'<i>\1</i>', text)

    # Restore code spans
    for idx, span in enumerate(code_spans):
        text = text.replace(f'\x00CODE{idx}\x00', span)
    return text


def parse_table(lines):
    rows = []
    for line in lines:
        if re.match(r'\s*\|[-| :]+\|\s*$', line):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        rows.append(cells)
    return rows


def md_to_flowables(md_text, styles, content_width):
    story = []
    lines = md_text.split('\n')
    i = 0
    first_h1 = True

    while i < len(lines):
        line = lines[i]

        # H1
        if re.match(r'^# [^#]', line):
            text = line[2:].strip()
            if first_h1:
                story.append(HeaderBanner(text, content_width))
                story.append(Spacer(1, 10))
                first_h1 = False
            else:
                story.append(Spacer(1, 8))
                story.append(HeaderBanner(text, content_width))
                story.append(Spacer(1, 10))
            i += 1
            continue

        # H2
        if re.match(r'^## [^#]', line):
            text = line[3:].strip()
            story.append(Spacer(1, 8))
            story.append(SectionBanner(text, content_width))
            story.append(Spacer(1, 6))
            i += 1
            continue

        # H3
        if re.match(r'^### [^#]', line):
            text = line[4:].strip()
            story.append(Paragraph(inline_format(text), styles['h3']))
            i += 1
            continue

        # H4+
        if re.match(r'^####', line):
            text = re.sub(r'^#+\s*', '', line)
            st = ParagraphStyle('h4tmp', parent=styles['h3'], fontSize=9,
                                textColor=ACCENT2)
            story.append(Paragraph(inline_format(text), st))
            i += 1
            continue

        # HR
        if re.match(r'^---+\s*$', line.strip()):
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=1, color=ACCENT2))
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Code block
        if line.strip().startswith('```'):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i].rstrip())
                i += 1
            i += 1
            if code_lines:
                story.append(Spacer(1, 4))
                story.append(CodeBlock(code_lines, content_width))
                story.append(Spacer(1, 6))
            continue

        # Table
        if line.strip().startswith('|'):
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                tbl_lines.append(lines[i])
                i += 1
            rows = parse_table(tbl_lines)
            if rows:
                ncols = max(len(r) for r in rows)
                tbl_data = []
                for r_idx, row in enumerate(rows):
                    # pad row if needed
                    while len(row) < ncols:
                        row.append('')
                    styled_row = []
                    for cell in row:
                        if r_idx == 0:
                            styled_row.append(Paragraph(inline_format(cell), styles['tbl_hdr']))
                        elif re.match(r'^`', cell.strip()):
                            styled_row.append(Paragraph(inline_format(cell), styles['tbl_cell']))
                        else:
                            styled_row.append(Paragraph(inline_format(cell), styles['tbl_cell_plain']))
                    tbl_data.append(styled_row)

                col_w = content_width / ncols
                ts = TableStyle([
                    ('BACKGROUND',   (0, 0), (-1, 0),  TABLE_HDR),
                    ('TEXTCOLOR',    (0, 0), (-1, 0),  WHITE),
                    ('ROWBACKGROUNDS',(0, 1),(-1, -1), [WHITE, TABLE_ALT]),
                    ('GRID',         (0, 0), (-1, -1), 0.5, BORDER),
                    ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING',  (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING',   (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
                ])
                t = Table(tbl_data, colWidths=[col_w] * ncols)
                t.setStyle(ts)
                story.append(Spacer(1, 4))
                story.append(t)
                story.append(Spacer(1, 6))
            continue

        # Blockquote
        if line.startswith('>'):
            text = line[1:].strip()
            story.append(Paragraph('> ' + inline_format(text), styles['note']))
            i += 1
            continue

        # Bullet
        m = re.match(r'^(\s*)[-*+] (.*)', line)
        if m:
            indent = len(m.group(1))
            text = m.group(2)
            st = styles['subbullet'] if indent >= 2 else styles['bullet']
            story.append(Paragraph(inline_format(text), st))
            i += 1
            continue

        # Numbered list
        m = re.match(r'^\s*\d+\.\s+(.*)', line)
        if m:
            story.append(Paragraph(inline_format(m.group(1)), styles['bullet']))
            i += 1
            continue

        # Empty line
        if not line.strip():
            story.append(Spacer(1, 4))
            i += 1
            continue

        # Normal text
        story.append(Paragraph(inline_format(line), styles['body']))
        i += 1

    return story


def main():
    src = '/Users/senna/WORK/Sensores-Updates/ROTEIRO-TESTES.md'
    dst = '/Users/senna/WORK/Sensores-Updates/ROTEIRO-TESTES.pdf'

    with open(src, 'r', encoding='utf-8') as f:
        md = f.read()

    doc = SimpleDocTemplate(
        dst,
        pagesize=A4,
        leftMargin=MARGIN_L,
        rightMargin=MARGIN_R,
        topMargin=MARGIN_T,
        bottomMargin=MARGIN_B,
        title="Roteiro de Testes \u2014 Vigilant Sensor Update System",
        author="Vigilant NDR",
    )

    content_width = PAGE_W - MARGIN_L - MARGIN_R
    styles = build_styles()
    story = md_to_flowables(md, styles, content_width)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"PDF gerado: {dst}")


if __name__ == '__main__':
    main()

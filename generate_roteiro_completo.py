#!/usr/bin/env python3
"""
Vigilant NDR — Roteiro de Testes Completo
Página 1 : Diagrama de arquitetura (landscape A4)
Páginas 2+: Roteiro de testes (portrait A4)
"""
import re, math
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rc
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfWriter, PdfReader

# ─────────────────────────────────────────────────────────────────────────────
#  PALETA  (sem cinza algum)
# ─────────────────────────────────────────────────────────────────────────────
BLACK  = colors.HexColor("#000000")
WHITE  = colors.HexColor("#FFFFFF")
NAVY   = colors.HexColor("#1A2540")   # fundo de header / títulos escuros
BLUE   = colors.HexColor("#2E4272")   # títulos de seção
LBLUE  = colors.HexColor("#E8EEFF")   # fundo de código / células alt.
TEAL   = colors.HexColor("#00B89F")   # acento / destaques
DTEAL  = colors.HexColor("#007A6B")   # teal mais escuro para texto sobre branco
GOLD   = colors.HexColor("#A07000")   # bordas manifest
LGOLD  = colors.HexColor("#FFF8DC")   # fundo manifest
LGREEN = colors.HexColor("#E8FFF4")   # fundo nota de atenção

LOGO   = "/Users/senna/WORK/Sensores-Updates/logo.png"
URL    = "vigilant.com.br"

# ─────────────────────────────────────────────────────────────────────────────
#  PRIMITIVOS DE DESENHO
# ─────────────────────────────────────────────────────────────────────────────
def fill(c, col):   c.setFillColor(col)
def stroke(c, col): c.setStrokeColor(col)

def txt(c, x, y, s, font="Helvetica", size=9, col=BLACK, align="left"):
    c.setFillColor(col); c.setFont(font, size)
    {"left": c.drawString, "center": c.drawCentredString,
     "right": c.drawRightString}[align](x, y, s)

def box(c, x, y, w, h, fill_col=WHITE, stroke_col=NAVY, lw=1.5, r=5):
    c.setFillColor(fill_col); c.setStrokeColor(stroke_col); c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)

def accent_bar(c, x, y, h, col=TEAL, bw=4):
    """Barra vertical colorida no lado esquerdo de uma caixa."""
    c.setFillColor(col); c.setStrokeColor(col); c.setLineWidth(0)
    c.rect(x, y, bw, h, fill=1, stroke=0)

def titled_box(c, x, y, w, h, title, title_h=20, body_col=WHITE,
               title_col=NAVY, text_col=WHITE, lw=1.5, r=5):
    """Caixa com faixa de título colorida no topo."""
    # corpo
    c.setFillColor(body_col); c.setStrokeColor(title_col); c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)
    # topo: arredondar apenas cantos superiores
    c.setFillColor(title_col); c.setStrokeColor(title_col); c.setLineWidth(0)
    c.roundRect(x, y+h-title_h, w, title_h, r, fill=1, stroke=0)
    c.rect(x, y+h-title_h, w, title_h//2+1, fill=1, stroke=0)  # canto inferior reto
    # borda geral por cima
    c.setFillColor(colors.Color(0,0,0,0)); c.setStrokeColor(title_col); c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, fill=0, stroke=1)
    # texto
    txt(c, x+w/2, y+h-title_h+(title_h-9)/2, title,
        "Helvetica-Bold", 8, text_col, "center")

def arrow(c, x1, y1, x2, y2, col=NAVY, lw=1.5, dashed=False, hs=7,
          label=None, lo=(0, 5)):
    c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(lw)
    c.setDash([5, 4] if dashed else [])
    c.line(x1, y1, x2, y2); c.setDash()
    a = math.atan2(y2-y1, x2-x1)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2-hs*math.cos(a-0.38), y2-hs*math.sin(a-0.38))
    p.lineTo(x2-hs*math.cos(a+0.38), y2-hs*math.sin(a+0.38))
    p.close(); c.setFillColor(col); c.drawPath(p, fill=1, stroke=0)
    if label:
        txt(c, (x1+x2)/2+lo[0], (y1+y2)/2+lo[1],
            label, "Helvetica-Oblique", 6.5, BLUE)

def dot(c, cx, cy, r, col=TEAL):
    c.setFillColor(col); c.setStrokeColor(col)
    c.circle(cx, cy, r, fill=1, stroke=0)

def badge(c, x, y, w, h, text, bg=TEAL, fg=WHITE, fs=7):
    c.setFillColor(bg); c.setStrokeColor(bg)
    c.roundRect(x, y, w, h, 3, fill=1, stroke=0)
    txt(c, x+w/2, y+(h-fs)/2+1, text, "Helvetica-Bold", fs, fg, "center")


# ─────────────────────────────────────────────────────────────────────────────
#  CABEÇALHO / RODAPÉ  (reutilizável)
# ─────────────────────────────────────────────────────────────────────────────
def draw_header(c, pw, ph, subtitle="", page_label=""):
    """Faixa de cabeçalho com logo + subtítulo."""
    HH = 58
    c.setFillColor(NAVY)
    c.rect(0, ph-HH, pw, HH, fill=1, stroke=0)
    # linha teal na base do header
    c.setFillColor(TEAL)
    c.rect(0, ph-HH-2, pw, 3, fill=1, stroke=0)
    # logo
    try:
        c.drawImage(LOGO, 18, ph-HH+11, width=200, height=37,
                    mask='auto', preserveAspectRatio=True)
    except Exception:
        txt(c, 20, ph-30, "VIGILANT", "Helvetica-Bold", 18, WHITE)
    # subtítulo
    if subtitle:
        txt(c, pw-20, ph-26, subtitle, "Helvetica-Bold", 11, WHITE, "right")
    if page_label:
        txt(c, pw-20, ph-42, page_label, "Helvetica", 8, TEAL, "right")


def draw_footer(c, pw, page_text=""):
    """Faixa de rodapé com URL + número de página."""
    FH = 26
    c.setFillColor(NAVY)
    c.rect(0, 0, pw, FH, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, FH, pw, 2, fill=1, stroke=0)
    txt(c, 20, 8, "Confidencial — uso interno", "Helvetica", 7.5, WHITE)
    txt(c, pw/2, 8, URL, "Helvetica-Bold", 8, TEAL, "center")
    if page_text:
        txt(c, pw-20, 8, page_text, "Helvetica", 7.5, WHITE, "right")


# ─────────────────────────────────────────────────────────────────────────────
#  PÁGINA 1 — DIAGRAMA DE ARQUITETURA  (landscape A4)
# ─────────────────────────────────────────────────────────────────────────────
def build_arch_page(buf):
    PW, PH = landscape(A4)   # 841.89 × 595.27
    c = rc.Canvas(buf, pagesize=landscape(A4))

    draw_header(c, PW, PH,
                subtitle="ARQUITETURA — SENSOR UPDATE SYSTEM",
                page_label="Vigilant-devs/sensores-updates  |  v2.0.3")
    draw_footer(c, PW, "Página 1")

    # ─── centro horizontal e limites úteis ──────────────────────────────────
    GCX = PW / 2

    # ════════════════════════════════════════════════════════════════════════
    # A — DESENVOLVEDOR
    # ════════════════════════════════════════════════════════════════════════
    DX, DY, DW, DH = 28, 370, 148, 140
    titled_box(c, DX, DY, DW, DH, "DESENVOLVEDOR",
               title_h=22, body_col=WHITE, title_col=NAVY)
    accent_bar(c, DX, DY, DH, TEAL)

    c.setFillColor(NAVY); c.circle(DX+DW/2, DY+DH-52, 22, fill=1, stroke=0)
    txt(c, DX+DW/2, DY+DH-58, "D", "Helvetica-Bold", 18, WHITE, "center")

    c.setStrokeColor(LBLUE); c.setLineWidth(1)
    c.line(DX+14, DY+72, DX+DW-14, DY+72)
    for i, ln in enumerate(["git tag vX.Y.Z",
                             "git push origin main",
                             "git push origin vX.Y.Z"]):
        yy = DY+62 - i*20
        dot(c, DX+20, yy+5, 4)
        txt(c, DX+30, yy, ln, "Courier", 8.5, BLACK)

    # ════════════════════════════════════════════════════════════════════════
    # B — GITHUB
    # ════════════════════════════════════════════════════════════════════════
    GX, GY, GW, GH = 196, 310, 450, 210
    titled_box(c, GX, GY, GW, GH,
               "GITHUB  —  Vigilant-devs / sensores-updates",
               title_h=22, body_col=colors.HexColor("#F2F5FF"), title_col=BLUE)
    accent_bar(c, GX, GY, GH, TEAL)

    # Sub: CI/Actions
    CX, CY, CW, CH = 212, 330, 195, 162
    titled_box(c, CX, CY, CW, CH, "CI / CD Actions",
               title_h=20, body_col=LBLUE, title_col=NAVY, lw=1)
    for i, ln in enumerate(["Detecta o git tag",
                             "Empacota os arquivos",
                             "Calcula SHA256",
                             "Assina com GPG",
                             "Publica Release"]):
        yy = CY+CH-38 - i*22
        dot(c, CX+16, yy+5, 5, NAVY)
        txt(c, CX+28, yy, ln, "Helvetica", 9, BLACK)

    # Sub: Releases
    RX, RY, RW, RH = 423, 380, 208, 112
    titled_box(c, RX, RY, RW, RH, "GitHub Releases",
               title_h=20, body_col=LBLUE, title_col=NAVY, lw=1)
    for i, fn in enumerate(["sensor-pack.tar.gz",
                             "sensor-pack.sha256",
                             "sensor-pack.sig"]):
        dot(c, RX+16, RY+RH-36-i*25, 4)
        txt(c, RX+28, RY+RH-40-i*25, fn, "Courier", 8.5, BLACK)

    # manifest.json
    MX, MY, MW, MH = 423, 330, 208, 44
    c.setFillColor(LGOLD); c.setStrokeColor(GOLD); c.setLineWidth(1.5)
    c.roundRect(MX, MY, MW, MH, 5, fill=1, stroke=1)
    c.setFillColor(GOLD); c.rect(MX, MY, 5, MH, fill=1, stroke=0)
    txt(c, MX+MW/2, MY+28, "manifest.json", "Helvetica-Bold", 11, BLACK, "center")
    txt(c, MX+MW/2, MY+12, "versão atual + URL do pacote", "Helvetica-Oblique", 8, GOLD, "center")

    # setas internas
    arrow(c, CX+CW, CY+CH-42, RX, RY+RH-28,
          col=NAVY, lw=1.2, label="publica Release", lo=(0, 7))
    arrow(c, CX+CW, CY+32, MX, MY+MH/2,
          col=GOLD, lw=1.2, label="atualiza versão", lo=(0, 7))

    # seta Dev → GitHub (cotovelo)
    dev_cy = DY + DH/2
    gh_cy  = GY + GH/2
    mid_x  = DX + DW + 12
    c.setStrokeColor(NAVY); c.setFillColor(NAVY); c.setLineWidth(2); c.setDash()
    c.line(DX+DW, dev_cy, mid_x, dev_cy)
    c.line(mid_x, dev_cy, mid_x, gh_cy)
    c.line(mid_x, gh_cy, GX, gh_cy)
    hs = 9
    p = c.beginPath()
    p.moveTo(GX, gh_cy)
    p.lineTo(GX-hs, gh_cy-4); p.lineTo(GX-hs, gh_cy+4); p.close()
    c.setFillColor(NAVY); c.drawPath(p, fill=1, stroke=0)
    txt(c, mid_x+4, (dev_cy+gh_cy)/2+4,
        "git push + tag", "Helvetica-BoldOblique", 8, NAVY)

    # ════════════════════════════════════════════════════════════════════════
    # C — SENSORES  (4 caixas, sem IPs)
    # ════════════════════════════════════════════════════════════════════════
    SW, SH, SGAP = 148, 90, 14
    SY = 200
    s0 = GCX - (4*SW + 3*SGAP) / 2
    s_cx = []

    for idx, name in enumerate(["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"]):
        sx = s0 + idx*(SW+SGAP)
        s_cx.append(sx + SW/2)
        titled_box(c, sx, SY, SW, SH, name.upper(),
                   title_h=22, body_col=WHITE, title_col=NAVY)
        accent_bar(c, sx, SY, SH, TEAL)
        c.setFillColor(BLUE); c.circle(sx+SW/2, SY+SH-40, 20, fill=1, stroke=0)
        txt(c, sx+SW/2, SY+SH-46, "S", "Helvetica-Bold", 16, WHITE, "center")
        badge(c, sx+SW/2-50, SY+9, 100, 18, "Vigilant Sensor", BLUE)

    # bifurcação GitHub → Sensores
    FORK_Y = GY - 12
    c.setStrokeColor(NAVY); c.setLineWidth(2); c.setDash()
    c.line(GCX, GY, GCX, FORK_Y)
    c.line(s_cx[0], FORK_Y, s_cx[-1], FORK_Y)
    for scx in s_cx:
        arrow(c, scx, FORK_Y, scx, SY+SH, col=NAVY, lw=1.8, hs=7)
    txt(c, GCX, FORK_Y-10,
        "download  ·  verificação GPG/SHA256  ·  post-install.sh",
        "Helvetica-Oblique", 8, NAVY, "center")

    # polling tracejado (apenas indicação, sem texto excessivo)
    arrow(c, s_cx[0]-20, SY+SH, s_cx[0]-20, GY,
          col=BLUE, lw=1.2, dashed=True, hs=6)
    txt(c, s_cx[0]-44, (SY+SH+GY)//2,
        "polling\n(timer)", "Helvetica-Oblique", 7.5, BLUE, "center")

    # ════════════════════════════════════════════════════════════════════════
    # D — SERVIDOR DE LOGS
    # ════════════════════════════════════════════════════════════════════════
    LW, LH = 430, 112
    LX = GCX - LW/2
    LY = 42
    titled_box(c, LX, LY, LW, LH, "SERVIDOR DE LOGS",
               title_h=22, body_col=WHITE, title_col=NAVY)
    accent_bar(c, LX, LY, LH, TEAL)

    svcs = [("rsyslog", "coleta TCP"),
            ("Promtail", "envia p/ Loki"),
            ("Loki",    "armazena"),
            ("Grafana",  "dashboard")]
    sw2 = (LW - 50) / 4
    for i, (svc, desc) in enumerate(svcs):
        sx2 = LX + 12 + i*(sw2+8)
        box(c, sx2, LY+10, sw2, LH-34, fill_col=LBLUE, stroke_col=BLUE, lw=1, r=4)
        txt(c, sx2+sw2/2, LY+LH-26, svc,  "Helvetica-Bold", 10, NAVY, "center")
        txt(c, sx2+sw2/2, LY+30,    desc, "Helvetica", 8, BLACK, "center")
        if i < 3:
            arrow(c, sx2+sw2+1, LY+LH/2-8, sx2+sw2+7, LY+LH/2-8,
                  col=NAVY, lw=1.2, hs=4)

    # sensores → logs (teal)
    LOG_TOP = LY + LH
    LOG_CX  = LX + LW/2
    CONV_Y  = SY - 12
    c.setStrokeColor(TEAL); c.setLineWidth(2); c.setDash()
    c.line(s_cx[0], SY, s_cx[-1], SY)
    for scx in s_cx:
        c.line(scx, SY, scx, CONV_Y)
    c.line(s_cx[0], CONV_Y, s_cx[-1], CONV_Y)
    c.line(LOG_CX, CONV_Y, LOG_CX, LOG_TOP+2)
    c.setFillColor(TEAL)
    p = c.beginPath()
    p.moveTo(LOG_CX, LOG_TOP)
    p.lineTo(LOG_CX-8, LOG_TOP+12)
    p.lineTo(LOG_CX+8, LOG_TOP+12)
    p.close(); c.drawPath(p, fill=1, stroke=0)
    txt(c, LOG_CX+12, CONV_Y+5,
        "envio de logs de atualização",
        "Helvetica-Oblique", 8, DTEAL)

    # ════════════════════════════════════════════════════════════════════════
    # LEGENDA  (canto direito, compacta)
    # ════════════════════════════════════════════════════════════════════════
    LGX = GX + GW + 16
    titled_box(c, LGX, 370, 138, 110, "LEGENDA",
               title_h=20, body_col=WHITE, title_col=NAVY)
    for i, (col, dash, lbl) in enumerate([
            (NAVY, False, "Fluxo principal"),
            (BLUE, True,  "Polling (timer)"),
            (TEAL, False, "Envio de logs"),
    ]):
        yy = 370+110-38 - i*26
        c.setStrokeColor(col); c.setLineWidth(2)
        c.setDash([5, 3] if dash else [])
        c.line(LGX+12, yy+6, LGX+44, yy+6); c.setDash()
        c.setFillColor(col)
        p = c.beginPath()
        p.moveTo(LGX+44, yy+6)
        p.lineTo(LGX+39, yy+3); p.lineTo(LGX+39, yy+9); p.close()
        c.drawPath(p, fill=1, stroke=0)
        txt(c, LGX+50, yy+2, lbl, "Helvetica", 8, BLACK)

    c.save()


# ─────────────────────────────────────────────────────────────────────────────
#  PÁGINAS 2+ — ROTEIRO DE TESTES  (portrait A4)
# ─────────────────────────────────────────────────────────────────────────────
PW, PH = A4
ML, MR, MT, MB = 2.2*cm, 2.2*cm, 2.9*cm, 2.5*cm


def build_text_styles():
    s = {}
    s['h3'] = ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=10,
        leading=14, textColor=NAVY, spaceBefore=14, spaceAfter=5)
    s['h4'] = ParagraphStyle('h4', fontName='Helvetica-Bold', fontSize=9,
        leading=13, textColor=BLUE, spaceBefore=8, spaceAfter=3)
    s['body'] = ParagraphStyle('body', fontName='Helvetica', fontSize=9,
        leading=14, textColor=BLACK, spaceAfter=5)
    s['bullet'] = ParagraphStyle('bullet', fontName='Helvetica', fontSize=9,
        leading=14, textColor=BLACK, spaceAfter=3,
        leftIndent=14, bulletIndent=2, bulletText='\u2022')
    s['subbullet'] = ParagraphStyle('subbullet', fontName='Helvetica', fontSize=9,
        leading=13, textColor=BLACK, spaceAfter=2,
        leftIndent=28, bulletIndent=16, bulletText='\u2013')
    s['note'] = ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=8.5,
        leading=12, textColor=NAVY, spaceAfter=5, leftIndent=12)
    s['tbl_hdr']   = ParagraphStyle('tbl_hdr',   fontName='Helvetica-Bold', fontSize=8,  leading=10, textColor=WHITE)
    s['tbl_code']  = ParagraphStyle('tbl_code',  fontName='Courier',        fontSize=7.5, leading=10, textColor=BLACK)
    s['tbl_plain'] = ParagraphStyle('tbl_plain', fontName='Helvetica',      fontSize=8,  leading=10, textColor=BLACK)
    return s


class H1Banner(Flowable):
    def __init__(self, text, w):
        super().__init__()
        self.text = text; self.bwidth = w; self.height = 48
    def draw(self):
        c = self.canv
        c.setFillColor(NAVY); c.rect(0, 0, self.bwidth, self.height, fill=1, stroke=0)
        c.setFillColor(TEAL);  c.rect(0, 0, 6, self.height, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('Helvetica-Bold', 15)
        c.drawString(16, 16, self.text)
    def wrap(self, *a): return (self.bwidth, self.height)


class H2Banner(Flowable):
    def __init__(self, text, w):
        super().__init__()
        self.text = text; self.bwidth = w; self.height = 24
    def draw(self):
        c = self.canv
        c.setFillColor(BLUE); c.rect(0, 0, self.bwidth, self.height, fill=1, stroke=0)
        c.setFillColor(TEAL);  c.rect(0, 0, 5, self.height, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('Helvetica-Bold', 10)
        c.drawString(12, 8, self.text)
    def wrap(self, *a): return (self.bwidth, self.height)


class CodeBlock(Flowable):
    def __init__(self, lines, w):
        super().__init__()
        self.lines = lines; self.bwidth = w
        self.pad = 9; self.lh = 12
        self.height = len(lines)*self.lh + self.pad*2
    def draw(self):
        c = self.canv; h = self.height
        # fundo azul claro
        c.setFillColor(LBLUE); c.rect(0, 0, self.bwidth, h, fill=1, stroke=0)
        # barra esquerda teal
        c.setFillColor(TEAL); c.rect(0, 0, 5, h, fill=1, stroke=0)
        # borda
        c.setStrokeColor(BLUE); c.setLineWidth(0.7)
        c.rect(0, 0, self.bwidth, h, fill=0, stroke=1)
        # texto preto
        c.setFillColor(BLACK); c.setFont('Courier', 8)
        for i, ln in enumerate(self.lines):
            y = h - self.pad - (i+1)*self.lh + 2
            if len(ln) > 114: ln = ln[:111]+'...'
            c.drawString(12, y, ln)
    def wrap(self, aw, ah): return (self.bwidth, self.height)


def on_text_page(canvas, doc):
    canvas.saveState()
    w, h = A4

    # header
    HH = 56
    canvas.setFillColor(NAVY)
    canvas.rect(0, h-HH, w, HH, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, h-HH-2, w, 3, fill=1, stroke=0)
    try:
        canvas.drawImage(LOGO, 18, h-HH+10, width=195, height=36,
                         mask='auto', preserveAspectRatio=True)
    except Exception:
        canvas.setFillColor(WHITE); canvas.setFont('Helvetica-Bold', 11)
        canvas.drawString(20, h-28, "VIGILANT")
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(w-20, h-26, "Roteiro de Testes  |  v2.0.3")
    canvas.setFillColor(TEAL)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawRightString(w-20, h-40, "Sensor Update System")

    # footer
    FH = 26
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, FH, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, FH, w, 2, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(20, 8, "Confidencial — uso interno")
    canvas.setFillColor(TEAL)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawCentredString(w/2, 8, URL)
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawRightString(w-20, 8, f"Página {doc.page + 1}")

    canvas.restoreState()


def esc(t):
    return t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')


def ifmt(text):
    spans = []
    def save(m):
        idx = len(spans)
        spans.append(f'<font name="Courier" size="8.5"><b>{esc(m.group(1))}</b></font>')
        return f'\x00C{idx}\x00'
    text = re.sub(r'`([^`]+)`', save, text)
    text = esc(text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'\*\*(.+?)\*\*',     r'<b>\1</b>',         text)
    text = re.sub(r'_(.+?)_',           r'<i>\1</i>',         text)
    text = re.sub(r'\*([^*\n]+?)\*',    r'<i>\1</i>',         text)
    for idx, sp in enumerate(spans):
        text = text.replace(f'\x00C{idx}\x00', sp)
    return text


def parse_table_rows(lines):
    rows = []
    for ln in lines:
        if re.match(r'\s*\|[-| :]+\|\s*$', ln): continue
        rows.append([c.strip() for c in ln.strip().strip('|').split('|')])
    return rows


def md_to_flowables(md, styles, cw):
    story = []
    lines = md.split('\n')
    i = 0; first_h1 = True

    while i < len(lines):
        ln = lines[i]

        # H1
        if re.match(r'^# [^#]', ln):
            t = ln[2:].strip()
            story += ([H1Banner(t, cw), Spacer(1, 12)] if first_h1
                      else [Spacer(1,8), H1Banner(t, cw), Spacer(1,12)])
            first_h1 = False; i += 1; continue

        # H2
        if re.match(r'^## [^#]', ln):
            story += [Spacer(1,10), H2Banner(ln[3:].strip(), cw), Spacer(1,7)]
            i += 1; continue

        # H3
        if re.match(r'^### [^#]', ln):
            story.append(Paragraph(ifmt(ln[4:].strip()), styles['h3']))
            i += 1; continue

        # H4
        if re.match(r'^####', ln):
            story.append(Paragraph(ifmt(re.sub(r'^#+\s*','',ln)), styles['h4']))
            i += 1; continue

        # HR
        if re.match(r'^---+\s*$', ln.strip()):
            story += [Spacer(1,4),
                      HRFlowable(width="100%", thickness=1.5, color=TEAL),
                      Spacer(1,4)]
            i += 1; continue

        # Code block
        if ln.strip().startswith('```'):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code.append(lines[i].rstrip()); i += 1
            i += 1
            if code:
                story += [Spacer(1,5), CodeBlock(code, cw), Spacer(1,7)]
            continue

        # Table
        if ln.strip().startswith('|'):
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                tbl_lines.append(lines[i]); i += 1
            rows = parse_table_rows(tbl_lines)
            if rows:
                ncols = max(len(r) for r in rows)
                data = []
                for ri, row in enumerate(rows):
                    while len(row) < ncols: row.append('')
                    sr = []
                    for cell in row:
                        if ri == 0:
                            sr.append(Paragraph(ifmt(cell), styles['tbl_hdr']))
                        elif re.match(r'^`', cell.strip()):
                            sr.append(Paragraph(ifmt(cell), styles['tbl_code']))
                        else:
                            sr.append(Paragraph(ifmt(cell), styles['tbl_plain']))
                    data.append(sr)
                ts = TableStyle([
                    ('BACKGROUND',    (0,0),(-1,0),  NAVY),
                    ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, LBLUE]),
                    ('GRID',          (0,0),(-1,-1), 0.6, NAVY),
                    ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
                    ('LEFTPADDING',   (0,0),(-1,-1), 7),
                    ('RIGHTPADDING',  (0,0),(-1,-1), 7),
                    ('TOPPADDING',    (0,0),(-1,-1), 5),
                    ('BOTTOMPADDING', (0,0),(-1,-1), 5),
                ])
                t = Table(data, colWidths=[cw/ncols]*ncols)
                t.setStyle(ts)
                story += [Spacer(1,5), t, Spacer(1,7)]
            continue

        # Blockquote
        if ln.startswith('>'):
            # caixa de nota com fundo verde claro
            inner = ifmt(ln[1:].strip())
            style = ParagraphStyle('note_tmp', fontName='Helvetica-Oblique',
                fontSize=8.5, leading=12, textColor=NAVY,
                backColor=LGREEN, borderColor=TEAL, borderWidth=1,
                borderPadding=(4,6,4,6), spaceAfter=6,
                leftIndent=0, borderRadius=3)
            story.append(Paragraph('<b>&#x25B6;</b> ' + inner, style))
            i += 1; continue

        # Bullet
        m = re.match(r'^(\s*)[-*+] (.*)', ln)
        if m:
            st = styles['subbullet'] if len(m.group(1)) >= 2 else styles['bullet']
            story.append(Paragraph(ifmt(m.group(2)), st))
            i += 1; continue

        # Numbered list
        m = re.match(r'^\s*\d+\.\s+(.*)', ln)
        if m:
            story.append(Paragraph(ifmt(m.group(1)), styles['bullet']))
            i += 1; continue

        # Empty
        if not ln.strip():
            story.append(Spacer(1, 5)); i += 1; continue

        # Normal
        story.append(Paragraph(ifmt(ln), styles['body']))
        i += 1

    return story


def build_text_pages(buf, md):
    cw = PW - ML - MR
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
        title="Roteiro de Testes — Vigilant Sensor Update System",
        author="Vigilant NDR",
    )
    doc.build(md_to_flowables(md, build_text_styles(), cw),
              onFirstPage=on_text_page, onLaterPages=on_text_page)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    src = "/Users/senna/WORK/Sensores-Updates/ROTEIRO-TESTES.md"
    dst = "/Users/senna/WORK/Sensores-Updates/ROTEIRO-COMPLETO.pdf"

    with open(src, encoding="utf-8") as f:
        md = f.read()

    arch_buf = BytesIO()
    build_arch_page(arch_buf)
    arch_buf.seek(0)

    text_buf = BytesIO()
    build_text_pages(text_buf, md)
    text_buf.seek(0)

    writer = PdfWriter()
    writer.add_page(PdfReader(arch_buf).pages[0])
    for page in PdfReader(text_buf).pages:
        writer.add_page(page)

    with open(dst, "wb") as f:
        writer.write(f)
    print(f"PDF gerado: {dst}")


if __name__ == "__main__":
    main()

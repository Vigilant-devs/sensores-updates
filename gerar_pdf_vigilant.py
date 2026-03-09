#!/usr/bin/env python3
"""
Vigilant NDR — Roteiro de Testes  (gerador limpo)
Página 1: fluxograma de arquitetura (landscape A4)
Páginas 2+: conteúdo do roteiro (portrait A4)
"""
import re, math
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as C
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfWriter, PdfReader

# ─── paleta ──────────────────────────────────────────────────────────────────
NAVY  = colors.HexColor("#1A2540")
BLUE  = colors.HexColor("#2E4272")
TEAL  = colors.HexColor("#00B89F")
DTEAL = colors.HexColor("#007A6B")
ICE   = colors.HexColor("#E8EEFF")   # fundo leve (não cinza)
GOLD  = colors.HexColor("#A07000")
CREAM = colors.HexColor("#FFF8DC")
BLACK = colors.HexColor("#000000")
WHITE = colors.HexColor("#FFFFFF")

LOGO = "/Users/senna/WORK/Sensores-Updates/logo.png"
URL  = "vigilant.com.br"

# ─── utilidades de canvas ────────────────────────────────────────────────────
def hdr(c, pw, ph, right_top="", right_sub=""):
    c.setFillColor(NAVY)
    c.rect(0, ph-55, pw, 55, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(0, ph-57, pw, 3, fill=1, stroke=0)
    try:
        c.drawImage(LOGO, 16, ph-50, width=190, height=35,
                    mask='auto', preserveAspectRatio=True)
    except Exception:
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 16)
        c.drawString(18, ph-36, "VIGILANT")
    if right_top:
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 11)
        c.drawRightString(pw-18, ph-24, right_top)
    if right_sub:
        c.setFillColor(TEAL); c.setFont("Helvetica", 8)
        c.drawRightString(pw-18, ph-40, right_sub)

def ftr(c, pw, page_txt=""):
    c.setFillColor(NAVY)
    c.rect(0, 0, pw, 24, fill=1, stroke=0)
    c.setFillColor(TEAL); c.rect(0, 24, pw, 2, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica", 7.5)
    c.drawString(18, 8, "Confidencial — uso interno")
    c.setFillColor(TEAL); c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(pw/2, 8, URL)
    if page_txt:
        c.setFillColor(WHITE); c.setFont("Helvetica", 7.5)
        c.drawRightString(pw-18, 8, page_txt)

def node(c, x, y, w, h, title, body_col=WHITE, title_col=NAVY, r=6, lw=1.5):
    """Caixa com faixa de título arredondada."""
    TH = 22
    # corpo
    c.setFillColor(body_col); c.setStrokeColor(title_col); c.setLineWidth(lw)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)
    # topo colorido
    c.setFillColor(title_col); c.setStrokeColor(title_col); c.setLineWidth(0)
    c.roundRect(x, y+h-TH, w, TH, r, fill=1, stroke=0)
    c.rect(x, y+h-TH, w, TH//2+2, fill=1, stroke=0)
    # borda final
    c.setStrokeColor(title_col); c.setLineWidth(lw)
    c.setFillColor(colors.Color(0,0,0,0))
    c.roundRect(x, y, w, h, r, fill=0, stroke=1)
    # acento teal esquerdo
    c.setFillColor(TEAL); c.rect(x, y, 5, h, fill=1, stroke=0)
    # título
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(x+w/2, y+h-TH+(TH-9)/2, title)

def bullet_row(c, x, y, text, col=TEAL, font="Helvetica", size=8.5, tcol=BLACK):
    c.setFillColor(col); c.circle(x, y+4, 4, fill=1, stroke=0)
    c.setFillColor(tcol); c.setFont(font, size)
    c.drawString(x+10, y, text)

def arr(c, x1, y1, x2, y2, col=NAVY, lw=1.8, dashed=False, hs=8):
    c.setStrokeColor(col); c.setFillColor(col); c.setLineWidth(lw)
    c.setDash([6,4] if dashed else [])
    c.line(x1, y1, x2, y2); c.setDash()
    a = math.atan2(y2-y1, x2-x1)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2-hs*math.cos(a-0.35), y2-hs*math.sin(a-0.35))
    p.lineTo(x2-hs*math.cos(a+0.35), y2-hs*math.sin(a+0.35))
    p.close(); c.setFillColor(col); c.drawPath(p, fill=1, stroke=0)

def lbl(c, x, y, t, size=7.5, col=NAVY, align="center"):
    c.setFillColor(col); c.setFont("Helvetica-Oblique", size)
    {"center": c.drawCentredString, "left": c.drawString,
     "right": c.drawRightString}[align](x, y, t)

# ─────────────────────────────────────────────────────────────────────────────
#  PÁGINA 1 — FLUXOGRAMA DE ARQUITETURA
# ─────────────────────────────────────────────────────────────────────────────
def pagina_fluxograma(buf):
    PW, PH = landscape(A4)
    cv = C.Canvas(buf, pagesize=landscape(A4))

    hdr(cv, PW, PH,
        right_top="FLUXOGRAMA DE ARQUITETURA",
        right_sub="Sensor Update System  |  v2.0.3")
    ftr(cv, PW, "Página 1")

    # ── A  DESENVOLVEDOR ─────────────────────────────────────────────────────
    DX, DY, DW, DH = 22, 362, 152, 158
    node(cv, DX, DY, DW, DH, "DESENVOLVEDOR")

    cv.setFillColor(BLUE); cv.circle(DX+DW/2, DY+DH-52, 24, fill=1, stroke=0)
    cv.setFillColor(WHITE); cv.setFont("Helvetica-Bold", 20)
    cv.drawCentredString(DX+DW/2, DY+DH-59, "D")

    cv.setStrokeColor(ICE); cv.setLineWidth(1)
    cv.line(DX+14, DY+84, DX+DW-14, DY+84)
    for i, t in enumerate(["git tag vX.Y.Z",
                            "git push origin main",
                            "git push origin vX.Y.Z"]):
        yy = DY+74 - i*22
        cv.setFillColor(TEAL); cv.circle(DX+19, yy+5, 4, fill=1, stroke=0)
        cv.setFillColor(BLACK); cv.setFont("Courier", 8.5)
        cv.drawString(DX+29, yy, t)

    # ── B  GITHUB ────────────────────────────────────────────────────────────
    GX, GY, GW, GH = 194, 298, 468, 222
    node(cv, GX, GY, GW, GH,
         "GITHUB  —  Vigilant-devs / sensores-updates",
         body_col=colors.HexColor("#F4F6FF"), title_col=BLUE)

    # CI/CD
    CX, CY, CW, CH = 210, 316, 200, 176
    node(cv, CX, CY, CW, CH, "CI / CD Actions",
         body_col=ICE, title_col=NAVY, lw=1)
    for i, t in enumerate(["Detecta o git tag",
                            "Empacota arquivos",
                            "Calcula SHA256",
                            "Assina com GPG",
                            "Publica Release",
                            "Atualiza manifest"]):
        bullet_row(cv, CX+18, CY+CH-42-i*23, t, col=NAVY, size=8.5)

    # Releases
    RX, RY, RW, RH = 428, 380, 218, 116
    node(cv, RX, RY, RW, RH, "GitHub Releases",
         body_col=ICE, title_col=NAVY, lw=1)
    for i, fn in enumerate(["sensor-pack.tar.gz",
                             "sensor-pack.sha256",
                             "sensor-pack.sig"]):
        bullet_row(cv, RX+18, RY+RH-40-i*26, fn,
                   col=TEAL, font="Courier", size=8.5)

    # manifest badge
    MX, MY, MW, MH = 428, 316, 218, 58
    cv.setFillColor(CREAM); cv.setStrokeColor(GOLD); cv.setLineWidth(1.5)
    cv.roundRect(MX, MY, MW, MH, 5, fill=1, stroke=1)
    cv.setFillColor(GOLD); cv.rect(MX, MY, 5, MH, fill=1, stroke=0)
    cv.setFillColor(BLACK); cv.setFont("Helvetica-Bold", 11)
    cv.drawCentredString(MX+MW/2, MY+36, "manifest.json")
    cv.setFillColor(GOLD); cv.setFont("Helvetica-Oblique", 8)
    cv.drawCentredString(MX+MW/2, MY+18, "versão atual + URL do pacote")

    # setas internas
    arr(cv, CX+CW, CY+CH-45, RX, RY+RH-28, col=NAVY, lw=1.2, hs=6)
    lbl(cv, (CX+CW+RX)/2, CY+CH-26, "publica Release", 7)
    arr(cv, CX+CW, CY+35, MX, MY+MH/2, col=GOLD, lw=1.2, hs=6)
    lbl(cv, (CX+CW+MX)/2, CY+42, "atualiza versão", 7, GOLD)

    # seta Dev → GitHub (cotovelo)
    dcx = DY + DH/2
    gcx = GY + GH/2
    mx  = DX + DW + 14
    cv.setStrokeColor(NAVY); cv.setLineWidth(2.2); cv.setDash()
    cv.line(DX+DW, dcx, mx, dcx)
    cv.line(mx, dcx, mx, gcx)
    cv.line(mx, gcx, GX, gcx)
    cv.setFillColor(NAVY)
    p = cv.beginPath()
    p.moveTo(GX, gcx); p.lineTo(GX-9, gcx-4); p.lineTo(GX-9, gcx+4); p.close()
    cv.drawPath(p, fill=1, stroke=0)
    cv.setFillColor(NAVY); cv.setFont("Helvetica-BoldOblique", 8.5)
    cv.drawString(mx+5, (dcx+gcx)/2+4, "git push + tag")

    # ── C  SENSORES ──────────────────────────────────────────────────────────
    SW, SH, SGAP = 152, 96, 14
    SY = 186
    GCX = GX + GW/2
    sx0 = GCX - (4*SW + 3*SGAP)/2
    scx = []

    for i, nm in enumerate(["Sensor 1", "Sensor 2", "Sensor 3", "Sensor 4"]):
        sx = sx0 + i*(SW+SGAP)
        scx.append(sx + SW/2)
        node(cv, sx, SY, SW, SH, nm.upper())
        cv.setFillColor(BLUE); cv.circle(sx+SW/2, SY+SH-40, 22, fill=1, stroke=0)
        cv.setFillColor(WHITE); cv.setFont("Helvetica-Bold", 18)
        cv.drawCentredString(sx+SW/2, SY+SH-47, "S")
        # badge
        bw = 110
        cv.setFillColor(BLUE); cv.setStrokeColor(BLUE)
        cv.roundRect(sx+SW/2-bw/2, SY+8, bw, 17, 3, fill=1, stroke=0)
        cv.setFillColor(WHITE); cv.setFont("Helvetica-Bold", 7.5)
        cv.drawCentredString(sx+SW/2, SY+14, "Vigilant Sensor")

    # bifurcação GitHub ↓ Sensores
    FY = GY - 14
    cv.setStrokeColor(NAVY); cv.setLineWidth(2.2); cv.setDash()
    cv.line(GCX, GY, GCX, FY)
    cv.line(scx[0], FY, scx[-1], FY)
    for cx in scx:
        arr(cv, cx, FY, cx, SY+SH, col=NAVY, lw=2, hs=8)
    lbl(cv, GCX, FY-11,
        "download  ·  verificação GPG/SHA256  ·  post-install.sh",
        8.5, NAVY)

    # polling (tracejado ↑, somente no lado esquerdo)
    px = scx[0] - 22
    arr(cv, px, SY+SH, px, GY, col=BLUE, lw=1.2, dashed=True, hs=6)
    cv.setFillColor(BLUE); cv.setFont("Helvetica-Oblique", 7.5)
    cv.drawCentredString(px-22, (SY+SH+GY)//2+6, "polling")
    cv.drawCentredString(px-22, (SY+SH+GY)//2-8, "(timer)")

    # ── D  LOGS ──────────────────────────────────────────────────────────────
    LW2, LH2 = 450, 112
    LX = GCX - LW2/2
    LY = 40
    node(cv, LX, LY, LW2, LH2, "SERVIDOR DE LOGS",
         body_col=WHITE, title_col=NAVY)

    svcs = [("rsyslog", "recebe TCP"),
            ("Promtail","coleta & envia"),
            ("Loki",   "armazena"),
            ("Grafana", "dashboard")]
    sw3 = (LW2 - 50) / 4
    for i, (sv, ds) in enumerate(svcs):
        sx3 = LX + 12 + i*(sw3+8)
        cv.setFillColor(ICE); cv.setStrokeColor(BLUE); cv.setLineWidth(1)
        cv.roundRect(sx3, LY+10, sw3, LH2-34, 4, fill=1, stroke=1)
        cv.setFillColor(NAVY); cv.setFont("Helvetica-Bold", 10)
        cv.drawCentredString(sx3+sw3/2, LY+LH2-28, sv)
        cv.setFillColor(BLACK); cv.setFont("Helvetica", 8)
        cv.drawCentredString(sx3+sw3/2, LY+30, ds)
        if i < 3:
            arr(cv, sx3+sw3+1, LY+LH2/2-8, sx3+sw3+7, LY+LH2/2-8,
                col=NAVY, lw=1.2, hs=4)

    # sensores ↓ logs
    LOGT = LY + LH2
    LOGCX = LX + LW2/2
    CY2 = SY - 12
    cv.setStrokeColor(TEAL); cv.setLineWidth(2.2); cv.setDash()
    cv.line(scx[0], SY, scx[-1], SY)
    for cx in scx:
        cv.line(cx, SY, cx, CY2)
    cv.line(scx[0], CY2, scx[-1], CY2)
    cv.line(LOGCX, CY2, LOGCX, LOGT+2)
    cv.setFillColor(TEAL)
    p = cv.beginPath()
    p.moveTo(LOGCX, LOGT); p.lineTo(LOGCX-9, LOGT+13); p.lineTo(LOGCX+9, LOGT+13)
    p.close(); cv.drawPath(p, fill=1, stroke=0)
    lbl(cv, LOGCX+14, CY2+5, "envio de logs (rsyslog)", 8, DTEAL, "left")

    # ── LEGENDA ───────────────────────────────────────────────────────────────
    LGX = GX + GW + 18
    cv.setFillColor(WHITE); cv.setStrokeColor(NAVY); cv.setLineWidth(1.2)
    cv.roundRect(LGX, 370, 130, 100, 5, fill=1, stroke=1)
    cv.setFillColor(NAVY); cv.setFont("Helvetica-Bold", 8)
    cv.drawCentredString(LGX+65, 453, "LEGENDA")
    cv.setStrokeColor(NAVY); cv.setLineWidth(0.5)
    cv.line(LGX+10, 447, LGX+120, 447)
    for i, (col, dash, lbl_t) in enumerate([
            (NAVY, False, "Fluxo principal"),
            (BLUE, True,  "Polling (timer)"),
            (TEAL, False, "Envio de logs")]):
        yy = 433 - i*24
        cv.setStrokeColor(col); cv.setLineWidth(1.8)
        cv.setDash([6,4] if dash else [])
        cv.line(LGX+10, yy+5, LGX+40, yy+5); cv.setDash()
        cv.setFillColor(col)
        p = cv.beginPath()
        p.moveTo(LGX+40, yy+5)
        p.lineTo(LGX+35, yy+2); p.lineTo(LGX+35, yy+8); p.close()
        cv.drawPath(p, fill=1, stroke=0)
        cv.setFillColor(BLACK); cv.setFont("Helvetica", 8)
        cv.drawString(LGX+46, yy+1, lbl_t)

    cv.save()


# ─────────────────────────────────────────────────────────────────────────────
#  PÁGINAS 2+  ROTEIRO DE TESTES  (portrait A4)
# ─────────────────────────────────────────────────────────────────────────────
PW, PH = A4
ML, MR, MT, MB = 2.2*cm, 2.2*cm, 2.9*cm, 2.4*cm

def estilos():
    s = {}
    s['h3'] = ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=10,
        leading=14, textColor=NAVY, spaceBefore=14, spaceAfter=5)
    s['h4'] = ParagraphStyle('h4', fontName='Helvetica-Bold', fontSize=9,
        leading=13, textColor=BLUE, spaceBefore=8, spaceAfter=4)
    s['body'] = ParagraphStyle('body', fontName='Helvetica', fontSize=9,
        leading=14, textColor=BLACK, spaceAfter=5)
    s['bullet'] = ParagraphStyle('bullet', fontName='Helvetica', fontSize=9,
        leading=14, textColor=BLACK, spaceAfter=3,
        leftIndent=14, bulletIndent=2, bulletText='\u2022')
    s['subbullet'] = ParagraphStyle('subbullet', fontName='Helvetica', fontSize=9,
        leading=13, textColor=BLACK, spaceAfter=2,
        leftIndent=28, bulletIndent=16, bulletText='\u2013')
    s['note'] = ParagraphStyle('note', fontName='Helvetica-Oblique', fontSize=8.5,
        leading=12, textColor=NAVY, spaceAfter=6, leftIndent=0,
        backColor=colors.HexColor("#E8FFF4"),
        borderColor=TEAL, borderWidth=1, borderPadding=(5, 8, 5, 8),
        borderRadius=3)
    s['th'] = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8,
        leading=10, textColor=WHITE)
    s['tc'] = ParagraphStyle('tc', fontName='Courier', fontSize=7.5,
        leading=10, textColor=BLACK)
    s['td'] = ParagraphStyle('td', fontName='Helvetica', fontSize=8,
        leading=10, textColor=BLACK)
    return s


class BannerH1(Flowable):
    def __init__(self, text, w):
        super().__init__()
        self.text = text; self.bwidth = w; self.height = 50
    def draw(self):
        c = self.canv
        c.setFillColor(NAVY); c.rect(0, 0, self.bwidth, self.height, fill=1, stroke=0)
        c.setFillColor(TEAL);  c.rect(0, 0, 6, self.height, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('Helvetica-Bold', 16)
        c.drawString(16, 17, self.text)
    def wrap(self, *a): return (self.bwidth, self.height)


class BannerH2(Flowable):
    def __init__(self, text, w):
        super().__init__()
        self.text = text; self.bwidth = w; self.height = 26
    def draw(self):
        c = self.canv
        c.setFillColor(BLUE); c.rect(0, 0, self.bwidth, self.height, fill=1, stroke=0)
        c.setFillColor(TEAL);  c.rect(0, 0, 5, self.height, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont('Helvetica-Bold', 10)
        c.drawString(12, 9, self.text)
    def wrap(self, *a): return (self.bwidth, self.height)


class Codigo(Flowable):
    def __init__(self, linhas, w):
        super().__init__()
        self.linhas = linhas; self.bwidth = w
        self.pad = 10; self.lh = 12
        self.height = len(linhas)*self.lh + self.pad*2
    def draw(self):
        c = self.canv; h = self.height
        c.setFillColor(ICE);  c.rect(0, 0, self.bwidth, h, fill=1, stroke=0)
        c.setFillColor(TEAL); c.rect(0, 0, 5, h, fill=1, stroke=0)
        c.setStrokeColor(BLUE); c.setLineWidth(0.8)
        c.rect(0, 0, self.bwidth, h, fill=0, stroke=1)
        c.setFillColor(BLACK); c.setFont('Courier', 8.5)
        for i, ln in enumerate(self.linhas):
            y = h - self.pad - (i+1)*self.lh + 2
            if len(ln) > 110: ln = ln[:107]+'...'
            c.drawString(12, y, ln)
    def wrap(self, aw, ah): return (self.bwidth, self.height)

    def split(self, avail_w, avail_h):
        max_lines = int((avail_h - self.pad * 2) / self.lh)
        if max_lines <= 0:
            return []  # não cabe nada — mover para próxima página
        if max_lines >= len(self.linhas):
            return [self]
        return [Codigo(self.linhas[:max_lines], self.bwidth),
                Codigo(self.linhas[max_lines:], self.bwidth)]


def cabecalho_rodape(canvas, doc):
    canvas.saveState()
    w, h = A4
    # header
    canvas.setFillColor(NAVY)
    canvas.rect(0, h-54, w, 54, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.rect(0, h-56, w, 3, fill=1, stroke=0)
    try:
        canvas.drawImage(LOGO, 16, h-50, width=190, height=35,
                         mask='auto', preserveAspectRatio=True)
    except Exception:
        canvas.setFillColor(WHITE); canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(18, h-32, "VIGILANT")
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(w-18, h-26, "Roteiro de Testes  |  v2.0.3")
    canvas.setFillColor(TEAL)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawRightString(w-18, h-40, "Sensor Update System")
    # footer
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, 24, fill=1, stroke=0)
    canvas.setFillColor(TEAL); canvas.rect(0, 24, w, 2, fill=1, stroke=0)
    canvas.setFillColor(WHITE); canvas.setFont('Helvetica', 7.5)
    canvas.drawString(18, 8, "Confidencial — uso interno")
    canvas.setFillColor(TEAL); canvas.setFont('Helvetica-Bold', 8)
    canvas.drawCentredString(w/2, 8, URL)
    canvas.setFillColor(WHITE); canvas.setFont('Helvetica', 7.5)
    canvas.drawRightString(w-18, 8, f"Página {doc.page + 1}")
    canvas.restoreState()


def esc(t):
    return t.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def fmt(text):
    spans = []
    def save(m):
        i = len(spans)
        spans.append(f'<font name="Courier" size="9"><b>{esc(m.group(1))}</b></font>')
        return f'\x00{i}\x00'
    text = re.sub(r'`([^`]+)`', save, text)
    text = esc(text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    text = re.sub(r'\*\*(.+?)\*\*',     r'<b>\1</b>',         text)
    text = re.sub(r'_(.+?)_',           r'<i>\1</i>',         text)
    text = re.sub(r'\*([^*\n]+?)\*',    r'<i>\1</i>',         text)
    for i, sp in enumerate(spans):
        text = text.replace(f'\x00{i}\x00', sp)
    return text

def parse_tbl(lines):
    rows = []
    for ln in lines:
        if re.match(r'\s*\|[-| :]+\|\s*$', ln): continue
        rows.append([c.strip() for c in ln.strip().strip('|').split('|')])
    return rows

def md_flowables(md, st, cw):
    story = []; lines = md.split('\n'); i = 0; fh1 = True
    while i < len(lines):
        ln = lines[i]
        # H1
        if re.match(r'^# [^#]', ln):
            t = ln[2:].strip()
            story += ([BannerH1(t,cw), Spacer(1,12)] if fh1
                      else [Spacer(1,10), BannerH1(t,cw), Spacer(1,12)])
            fh1 = False; i += 1; continue
        # H2
        if re.match(r'^## [^#]', ln):
            story += [Spacer(1,10), BannerH2(ln[3:].strip(),cw), Spacer(1,8)]
            i += 1; continue
        # H3
        if re.match(r'^### [^#]', ln):
            story.append(Paragraph(fmt(ln[4:].strip()), st['h3']))
            i += 1; continue
        # H4
        if re.match(r'^####', ln):
            story.append(Paragraph(fmt(re.sub(r'^#+\s*','',ln)), st['h4']))
            i += 1; continue
        # HR
        if re.match(r'^---+\s*$', ln.strip()):
            story += [Spacer(1,4),
                      HRFlowable(width="100%", thickness=1.5, color=TEAL),
                      Spacer(1,4)]
            i += 1; continue
        # Código
        if ln.strip().startswith('```'):
            cod = []; i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                cod.append(lines[i].rstrip()); i += 1
            i += 1
            if cod: story += [Spacer(1,5), Codigo(cod,cw), Spacer(1,7)]
            continue
        # Tabela
        if ln.strip().startswith('|'):
            tl = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                tl.append(lines[i]); i += 1
            rows = parse_tbl(tl)
            if rows:
                nc = max(len(r) for r in rows)
                data = []
                for ri, row in enumerate(rows):
                    while len(row) < nc: row.append('')
                    sr = []
                    for cell in row:
                        if ri == 0: sr.append(Paragraph(fmt(cell), st['th']))
                        elif re.match(r'^`', cell.strip()): sr.append(Paragraph(fmt(cell), st['tc']))
                        else: sr.append(Paragraph(fmt(cell), st['td']))
                    data.append(sr)
                ts = TableStyle([
                    ('BACKGROUND',    (0,0),(-1,0),  NAVY),
                    ('ROWBACKGROUNDS',(0,1),(-1,-1), [WHITE, ICE]),
                    ('GRID',          (0,0),(-1,-1), 0.6, NAVY),
                    ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
                    ('LEFTPADDING',   (0,0),(-1,-1), 8),
                    ('RIGHTPADDING',  (0,0),(-1,-1), 8),
                    ('TOPPADDING',    (0,0),(-1,-1), 5),
                    ('BOTTOMPADDING', (0,0),(-1,-1), 5),
                ])
                t = Table(data, colWidths=[cw/nc]*nc)
                t.setStyle(ts)
                story += [Spacer(1,5), t, Spacer(1,7)]
            continue
        # Nota >
        if ln.startswith('>'):
            story.append(Paragraph('<b>&#x25B6;</b> ' + fmt(ln[1:].strip()), st['note']))
            i += 1; continue
        # Bullet
        m = re.match(r'^(\s*)[-*+] (.*)', ln)
        if m:
            st2 = st['subbullet'] if len(m.group(1)) >= 2 else st['bullet']
            story.append(Paragraph(fmt(m.group(2)), st2))
            i += 1; continue
        # Numerada
        m = re.match(r'^\s*\d+\.\s+(.*)', ln)
        if m:
            story.append(Paragraph(fmt(m.group(1)), st['bullet']))
            i += 1; continue
        # Vazia
        if not ln.strip():
            story.append(Spacer(1,5)); i += 1; continue
        # Normal
        story.append(Paragraph(fmt(ln), st['body']))
        i += 1
    return story

def paginas_texto(buf, md):
    cw = PW - ML - MR
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
        title="Roteiro de Testes — Vigilant Sensor Update System",
        author="Vigilant NDR")
    doc.build(md_flowables(md, estilos(), cw),
              onFirstPage=cabecalho_rodape,
              onLaterPages=cabecalho_rodape)

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    src = "/Users/senna/WORK/Sensores-Updates/Documentacao/README.md"
    dst = "/Users/senna/WORK/Sensores-Updates/Documentacao/VIGILANT-ROTEIRO.pdf"
    install_src = "/Users/senna/WORK/Sensores-Updates/tools/install-updater-only.sh"

    with open(src, encoding="utf-8") as f:
        md = f.read()

    with open(install_src, encoding="utf-8") as f:
        install_sh = f.read()

    extra_md = """

---

# Instalação em Sensores Legados

## install-updater-only.sh

### Sobre este script

O `install-updater-only.sh` instala **somente o vigilant-updater** em sensores que já estão operacionais mas não possuem o sistema de atualização automática. Não altera configurações existentes de hostname, VPN, Snort, Dionaea, Cowrie, Bettercap ou ExaBGP.

### Quando usar

- Sensor já instalado e operacional, sem o updater Vigilant
- Migração de sensores legados para o novo sistema de atualização automática

### Pré-requisitos

- Acesso root ao sensor (SSH porta 12222)
- Conectividade com o GitHub (para download dos arquivos)
- Rocky Linux / RHEL (usa `dnf` ou `yum`)

### Como executar

```bash
# Conectar ao sensor
ssh -p 12222 root@<IP-SENSOR>

# Baixar e executar o script
curl -fsSL https://raw.githubusercontent.com/Vigilant-devs/sensores-updates/main/tools/install-updater-only.sh -o install-updater-only.sh
bash install-updater-only.sh
```

> O script solicita interativamente: `sensor_id`, `client_id` (Vigilant ID) e o IP do servidor de logs. Valores existentes são detectados automaticamente e podem ser mantidos pressionando Enter.

### O que o script faz

| Etapa | Ação |
|---|---|
| 1. Verifica root | Aborta se não executado como root |
| 2. Coleta identidade | sensor_id, client_id, IP do servidor de logs |
| 3. Instala jq | Via dnf/yum se ausente |
| 4. Cria diretórios | `/vigilant/scripts/vigilantsensor/updater/` e `logs/` |
| 5. Baixa arquivos | vigilant-updater.sh, GPG key, units systemd |
| 6. Grava identidade | sensor_id, client_id, log_server_ip em `/vigilant/scripts/` |
| 7. Ativa timer | `vigilant-updater-test.timer` (a cada 5 min) |
| 8. Configura rsyslog | Encaminha logs para o servidor central na porta 514 |

### Script completo

```
""" + install_sh + """
```
"""
    md = md + extra_md

    b1 = BytesIO(); pagina_fluxograma(b1); b1.seek(0)
    b2 = BytesIO(); paginas_texto(b2, md); b2.seek(0)

    w = PdfWriter()
    w.add_page(PdfReader(b1).pages[0])
    for pg in PdfReader(b2).pages:
        w.add_page(pg)

    with open(dst, "wb") as f:
        w.write(f)
    print(f"Gerado: {dst}")

if __name__ == "__main__":
    main()

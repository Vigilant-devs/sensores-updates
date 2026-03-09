#!/usr/bin/env python3
"""
Vigilant NDR — Diagrama de Arquitetura do Sensor Update System
Formato: Landscape A4
"""
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import Image as RLImage

# ── Dimensões ──────────────────────────────────────────────────────────────────
PW, PH = landscape(A4)   # 841.89 x 595.27 pt

# ── Paleta ────────────────────────────────────────────────────────────────────
BLACK   = colors.HexColor("#000000")
WHITE   = colors.HexColor("#FFFFFF")
NAVY    = colors.HexColor("#1A2540")   # fundo escuro / header
BLUE    = colors.HexColor("#2E4272")   # titulos de caixas
LBLUE   = colors.HexColor("#EEF2FF")   # fundo claro de caixas
TEAL    = colors.HexColor("#0EBD9F")   # destaque acento (gradiente logo)
BORDER  = colors.HexColor("#1A2540")

# ── Helpers ────────────────────────────────────────────────────────────────────
def set_black(c): c.setFillColor(BLACK); c.setStrokeColor(BLACK)
def set_navy(c):  c.setFillColor(NAVY);  c.setStrokeColor(NAVY)
def set_blue(c):  c.setFillColor(BLUE);  c.setStrokeColor(BLUE)

def draw_box(c, x, y, w, h, title=None, title_h=18, bg=WHITE,
             border_color=NAVY, border_w=1.5, radius=4):
    """Caixa com fundo opcional e título na faixa superior."""
    # sombra leve
    c.setFillColor(colors.HexColor("#CCCCCC"))
    c.setStrokeColor(colors.HexColor("#CCCCCC"))
    c.roundRect(x+2, y-2, w, h, radius, fill=1, stroke=0)

    # corpo
    c.setFillColor(bg)
    c.setStrokeColor(border_color)
    c.setLineWidth(border_w)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)

    if title:
        # faixa do título
        c.setFillColor(BLUE)
        c.setStrokeColor(BLUE)
        c.setLineWidth(0)
        # topo arredondado manualmente: retangulo + parte reta em baixo
        c.roundRect(x, y+h-title_h, w, title_h, radius, fill=1, stroke=0)
        c.rect(x, y+h-title_h, w, title_h//2, fill=1, stroke=0)
        # restaurar borda
        c.setStrokeColor(border_color)
        c.setLineWidth(border_w)
        c.roundRect(x, y, w, h, radius, fill=0, stroke=1)
        # texto título
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(x + w/2, y + h - title_h + 5, title)


def draw_arrow(c, x1, y1, x2, y2, label=None, label_offset=(0, 4),
               color=NAVY, width=1.2, dashed=False, head_size=6):
    """Seta de (x1,y1) a (x2,y2) com arrowhead e rótulo opcional."""
    import math
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    if dashed:
        c.setDash([4, 3])
    else:
        c.setDash()

    c.line(x1, y1, x2, y2)
    c.setDash()

    # arrowhead
    angle = math.atan2(y2 - y1, x2 - x1)
    ax1 = x2 - head_size * math.cos(angle - 0.4)
    ay1 = y2 - head_size * math.sin(angle - 0.4)
    ax2 = x2 - head_size * math.cos(angle + 0.4)
    ay2 = y2 - head_size * math.sin(angle + 0.4)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(ax1, ay1)
    p.lineTo(ax2, ay2)
    p.close()
    c.setFillColor(color)
    c.drawPath(p, fill=1, stroke=0)

    if label:
        c.setFillColor(BLACK)
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawCentredString(mx, my, label)


def draw_elbow_arrow(c, x1, y1, x2, y2, bend_y=None, bend_x=None,
                     label=None, label_offset=(0, 4),
                     color=NAVY, width=1.2, dashed=False, head_size=6):
    """Seta em L (vertical depois horizontal, ou horizontal depois vertical)."""
    import math
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    if dashed:
        c.setDash([4, 3])
    else:
        c.setDash()

    if bend_y is not None:
        # vai até bend_y na vertical, depois horizontal até x2
        c.line(x1, y1, x1, bend_y)
        c.line(x1, bend_y, x2, bend_y)
        c.line(x2, bend_y, x2, y2)
        last_x, last_y = x2, bend_y
        end_x, end_y = x2, y2
    elif bend_x is not None:
        c.line(x1, y1, bend_x, y1)
        c.line(bend_x, y1, bend_x, y2)
        c.line(bend_x, y2, x2, y2)
        last_x, last_y = bend_x, y2
        end_x, end_y = x2, y2
    else:
        c.line(x1, y1, x2, y2)
        last_x, last_y = x1, y1
        end_x, end_y = x2, y2

    c.setDash()

    # arrowhead
    angle = math.atan2(end_y - last_y, end_x - last_x)
    ax1 = end_x - head_size * math.cos(angle - 0.4)
    ay1 = end_y - head_size * math.sin(angle - 0.4)
    ax2 = end_x - head_size * math.cos(angle + 0.4)
    ay2 = end_y - head_size * math.sin(angle + 0.4)
    p = c.beginPath()
    p.moveTo(end_x, end_y)
    p.lineTo(ax1, ay1)
    p.lineTo(ax2, ay2)
    p.close()
    c.setFillColor(color)
    c.drawPath(p, fill=1, stroke=0)

    if label:
        c.setFillColor(BLACK)
        if bend_y is not None:
            lx = (x1 + x2) / 2 + label_offset[0]
            ly = bend_y + label_offset[1]
        else:
            lx = (x1 + x2) / 2 + label_offset[0]
            ly = (y1 + y2) / 2 + label_offset[1]
        c.setFont("Helvetica-Oblique", 6.5)
        c.drawCentredString(lx, ly, label)


def draw_badge(c, x, y, w, h, text, bg=TEAL, fg=WHITE, fontsize=7):
    """Pequeno badge colorido."""
    c.setFillColor(bg)
    c.setStrokeColor(bg)
    c.roundRect(x, y, w, h, 3, fill=1, stroke=0)
    c.setFillColor(fg)
    c.setFont("Helvetica-Bold", fontsize)
    c.drawCentredString(x + w/2, y + (h - fontsize) / 2 + 1, text)


def draw_icon_circle(c, cx, cy, r, icon, bg=BLUE, fg=WHITE):
    """Círculo com letra/ícone (para identificar componentes)."""
    c.setFillColor(bg)
    c.setStrokeColor(bg)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillColor(fg)
    c.setFont("Helvetica-Bold", r * 1.1)
    c.drawCentredString(cx, cy - r * 0.4, icon)


def text(c, x, y, s, font="Helvetica", size=8, color=BLACK, align="left"):
    c.setFillColor(color)
    c.setFont(font, size)
    if align == "center":
        c.drawCentredString(x, y, s)
    elif align == "right":
        c.drawRightString(x, y, s)
    else:
        c.drawString(x, y, s)


# ── DIAGRAMA PRINCIPAL ─────────────────────────────────────────────────────────
def draw_diagram(c):
    # ── Header ──────────────────────────────────────────────────────────────────
    c.setFillColor(NAVY)
    c.rect(0, PH - 54, PW, 54, fill=1, stroke=0)

    # Faixa teal accent na base do header
    c.setFillColor(TEAL)
    c.rect(0, PH - 56, PW, 3, fill=1, stroke=0)

    # Logo
    try:
        logo = RLImage("/Users/senna/WORK/Sensores-Updates/logo.png",
                       width=190, height=35)
        logo.drawOn(c, 20, PH - 48)
    except Exception:
        text(c, 22, PH - 35, "VIGILANT", "Helvetica-Bold", 20, WHITE)

    # Título do diagrama
    text(c, PW - 20, PH - 24, "ARQUITETURA — SENSOR UPDATE SYSTEM",
         "Helvetica-Bold", 11, WHITE, align="right")
    text(c, PW - 20, PH - 39, "Vigilant-devs/sensores-updates  |  v2.0.3",
         "Helvetica", 8, TEAL, align="right")

    # ── Footer ──────────────────────────────────────────────────────────────────
    c.setFillColor(NAVY)
    c.rect(0, 0, PW, 22, fill=1, stroke=0)
    text(c, 22, 7, "Confidencial — uso interno Vigilant NDR",
         "Helvetica", 7.5, WHITE)
    text(c, PW - 22, 7, "vigilantndr.com.br",
         "Helvetica", 7.5, TEAL, align="right")

    # ── Separadores de zona (linhas guia leves) ──────────────────────────────
    # (não desenhadas no PDF final, apenas para referência de layout)

    # ═══════════════════════════════════════════════════════════════════════════
    # ZONA 1 — DESENVOLVEDOR  (x=22, y=380-490)
    # ═══════════════════════════════════════════════════════════════════════════
    DEV_X, DEV_Y, DEV_W, DEV_H = 22, 385, 148, 118
    draw_box(c, DEV_X, DEV_Y, DEV_W, DEV_H, title="DESENVOLVEDOR", bg=WHITE)

    draw_icon_circle(c, DEV_X + 28, DEV_Y + DEV_H - 40, 16, "D")
    text(c, DEV_X + 52, DEV_Y + DEV_H - 35, "Máquina local",
         "Helvetica-Bold", 7.5, BLACK)
    text(c, DEV_X + 52, DEV_Y + DEV_H - 47, "git add / commit",
         "Helvetica", 7, BLACK)

    # bullets
    for i, line in enumerate([
        "git tag vX.Y.Z",
        "git push origin main",
        "git push origin vX.Y.Z",
    ]):
        yy = DEV_Y + 65 - i * 14
        c.setFillColor(TEAL)
        c.circle(DEV_X + 14, yy + 3, 2.5, fill=1, stroke=0)
        text(c, DEV_X + 22, yy, line, "Courier", 7, BLACK)

    # ═══════════════════════════════════════════════════════════════════════════
    # ZONA 2 — GITHUB  (x=195, y=330-505)
    # ═══════════════════════════════════════════════════════════════════════════
    GH_X, GH_Y, GH_W, GH_H = 195, 328, 415, 188
    draw_box(c, GH_X, GH_Y, GH_W, GH_H, title="GITHUB  —  Vigilant-devs / sensores-updates",
             title_h=20, bg=colors.HexColor("#F7F9FF"))

    # ── Sub-box: CI/Actions ──────────────────────────────────────────────────
    CI_X, CI_Y, CI_W, CI_H = 210, 350, 175, 130
    draw_box(c, CI_X, CI_Y, CI_W, CI_H, title="GitHub Actions CI/CD",
             title_h=17, bg=LBLUE, border_color=BLUE, border_w=1)

    for i, line in enumerate([
        "1. git tag detectado",
        "2. Build sensor-pack.tar.gz",
        "3. Calcular SHA256",
        "4. Assinar GPG",
        "5. Criar Release",
        "6. Atualizar manifest.json",
    ]):
        yy = CI_Y + CI_H - 30 - i * 16
        c.setFillColor(TEAL)
        c.circle(CI_X + 12, yy + 3, 2, fill=1, stroke=0)
        text(c, CI_X + 20, yy, line, "Helvetica", 7, BLACK)

    # ── Sub-box: GitHub Releases ─────────────────────────────────────────────
    REL_X, REL_Y, REL_W, REL_H = 410, 390, 180, 90
    draw_box(c, REL_X, REL_Y, REL_W, REL_H, title="GitHub Releases",
             title_h=17, bg=LBLUE, border_color=BLUE, border_w=1)

    text(c, REL_X + REL_W/2, REL_Y + 57, "sensor-pack.tar.gz",
         "Courier", 8, BLACK, align="center")
    text(c, REL_X + REL_W/2, REL_Y + 43, "sensor-pack.sha256",
         "Courier", 8, BLACK, align="center")
    text(c, REL_X + REL_W/2, REL_Y + 29, "sensor-pack.tar.gz.sig",
         "Courier", 8, BLACK, align="center")
    draw_badge(c, REL_X + REL_W/2 - 28, REL_Y + 10, 56, 14, "GPG + SHA256")

    # ── manifest.json badge ──────────────────────────────────────────────────
    MF_X, MF_Y, MF_W, MF_H = 410, 349, 180, 34
    draw_box(c, MF_X, MF_Y, MF_W, MF_H, bg=colors.HexColor("#FFFDE7"),
             border_color=colors.HexColor("#B8860B"), border_w=1, radius=3)
    text(c, MF_X + MF_W/2, MF_Y + 20, "manifest.json",
         "Courier", 8.5, BLACK, align="center")
    text(c, MF_X + MF_W/2, MF_Y + 8, '{ "version": "2.0.3", "url": "..." }',
         "Courier", 6, colors.HexColor("#555500"), align="center")

    # Seta CI → Releases
    draw_arrow(c, CI_X + CI_W, CI_Y + CI_H/2 + 10,
               REL_X, REL_Y + REL_H/2 + 5,
               label="cria Release", label_offset=(0, 6))
    # Seta CI → manifest.json
    draw_arrow(c, CI_X + CI_W, CI_Y + CI_H/2 - 18,
               MF_X, MF_Y + MF_H/2,
               label="atualiza versão", label_offset=(0, 6))

    # ═══════════════════════════════════════════════════════════════════════════
    # SETA  Developer → GitHub
    # ═══════════════════════════════════════════════════════════════════════════
    draw_arrow(c, DEV_X + DEV_W, DEV_Y + DEV_H/2,
               GH_X, GH_Y + GH_H/2,
               label="git push + tag", label_offset=(0, 7),
               color=NAVY, width=2, head_size=8)

    # ═══════════════════════════════════════════════════════════════════════════
    # ZONA 3 — SENSORES  (y=215-305)
    # ═══════════════════════════════════════════════════════════════════════════
    sensors = [
        ("sensor-1",  "172.16.162.197", "sensor-1",  "20004"),
        ("sensor-2",  "172.16.162.202", "sensor-2",  "20004"),
        ("sensor-3",  "172.16.162.198", "sensor-3",  "20004"),
        ("sensor-04", "172.16.162.136", "sensor-04", "20004"),
    ]
    SEN_W, SEN_H = 148, 92
    SEN_GAP = 11
    SEN_Y = 215
    total_w = len(sensors) * SEN_W + (len(sensors) - 1) * SEN_GAP
    GH_CX = GH_X + GH_W / 2
    sen_start_x = GH_CX - total_w / 2

    sensor_centers = []
    for idx, (name, ip, sid, cid) in enumerate(sensors):
        sx = sen_start_x + idx * (SEN_W + SEN_GAP)
        draw_box(c, sx, SEN_Y, SEN_W, SEN_H, title=name.upper(), bg=WHITE)
        scx = sx + SEN_W / 2
        sensor_centers.append((scx, SEN_Y, SEN_Y + SEN_H))

        # ícone
        draw_icon_circle(c, sx + 20, SEN_Y + SEN_H - 35, 12, "S", bg=NAVY)

        text(c, sx + 36, SEN_Y + SEN_H - 29, ip,
             "Courier", 7.5, BLACK)
        text(c, sx + 36, SEN_Y + SEN_H - 41, "SSH :12222",
             "Courier", 6.5, BLUE)

        # divisor
        c.setStrokeColor(BLUE)
        c.setLineWidth(0.4)
        c.line(sx + 8, SEN_Y + 53, sx + SEN_W - 8, SEN_Y + 53)

        for i, line in enumerate([
            f"sensor_id: {sid}",
            f"client_id: {cid}",
            "updater: /vigilant/...",
        ]):
            yy = SEN_Y + 44 - i * 13
            text(c, sx + 10, yy, line, "Courier", 6.5, BLACK)

    # ═══════════════════════════════════════════════════════════════════════════
    # SETAS  GitHub → Sensores  (bifurcação / distribuição)
    # ═══════════════════════════════════════════════════════════════════════════
    DIST_Y_TOP    = GH_Y          # base do GitHub box
    DIST_Y_MID    = 314           # ponto de bifurcação
    DIST_Y_BOTTOM = SEN_Y + SEN_H # topo dos sensor boxes

    # Linha vertical do GitHub para baixo até ponto de bifurcação (download)
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.5)
    c.setDash()
    c.line(GH_CX, DIST_Y_TOP, GH_CX, DIST_Y_MID)

    # Linha horizontal no ponto de bifurcação
    leftmost  = sensor_centers[0][0]
    rightmost = sensor_centers[-1][0]
    c.line(leftmost, DIST_Y_MID, rightmost, DIST_Y_MID)

    # Linhas verticais para cada sensor (download)
    for scx, sy_bot, sy_top in sensor_centers:
        draw_arrow(c, scx, DIST_Y_MID, scx, sy_top,
                   color=NAVY, width=1.5, head_size=6)

    # Label no ponto de bifurcação
    text(c, GH_CX + 4, DIST_Y_MID + 5,
         "download tar.gz  ·  verificar SHA256 + GPG  ·  aplicar post-install.sh",
         "Helvetica-Oblique", 6.5, BLUE, align="center")

    # Setas de polling manifest (sensors → GitHub manifest) — tracejadas, indo pra cima
    # Apenas das extremidades para não poluir
    POLL_OFFSET = 18
    for i, (scx, sy_bot, sy_top) in enumerate([sensor_centers[0], sensor_centers[-1]]):
        px = scx - POLL_OFFSET if i == 0 else scx + POLL_OFFSET
        draw_arrow(c, px, sy_top, px, DIST_Y_TOP,
                   color=BLUE, width=0.8, dashed=True, head_size=5)
    text(c, leftmost - POLL_OFFSET - 2, (sy_top + DIST_Y_TOP)/2,
         "polling manifest\n(timer)", "Helvetica-Oblique", 6, BLUE, align="right")

    # ═══════════════════════════════════════════════════════════════════════════
    # ZONA 4 — VIGILANT LOGS SERVER  (y=38-150)
    # ═══════════════════════════════════════════════════════════════════════════
    LOG_W, LOG_H = 430, 118
    LOG_X = GH_CX - LOG_W / 2
    LOG_Y = 38
    draw_box(c, LOG_X, LOG_Y, LOG_W, LOG_H,
             title="VIGILANT LOGS SERVER  —  172.16.162.189",
             title_h=20, bg=WHITE)

    # Sub-blocos internos: 4 serviços
    svcs = [
        ("rsyslog", "TCP:514\nrecebe logs"),
        ("Promtail", "coleta\nlogs"),
        ("Loki", "armazena\nlogs"),
        ("Grafana", "dashboard\nhttps://.189"),
    ]
    svc_w = (LOG_W - 50) / 4
    for i, (svc, desc) in enumerate(svcs):
        sx2 = LOG_X + 12 + i * (svc_w + 8)
        sy2 = LOG_Y + 10
        c.setFillColor(LBLUE)
        c.setStrokeColor(BLUE)
        c.setLineWidth(0.7)
        c.roundRect(sx2, sy2, svc_w - 4, 74, 3, fill=1, stroke=1)
        text(c, sx2 + (svc_w - 4)/2, sy2 + 57, svc,
             "Helvetica-Bold", 8, BLUE, align="center")
        c.setStrokeColor(BLUE)
        c.setLineWidth(0.3)
        c.line(sx2 + 6, sy2 + 50, sx2 + svc_w - 10, sy2 + 50)
        for j, dl in enumerate(desc.split("\n")):
            text(c, sx2 + (svc_w - 4)/2, sy2 + 36 - j*13, dl,
                 "Helvetica", 7, BLACK, align="center")

        # seta flow entre serviços
        if i < len(svcs) - 1:
            draw_arrow(c, sx2 + svc_w - 4, sy2 + 37,
                       sx2 + svc_w + 4, sy2 + 37,
                       color=NAVY, width=1, head_size=4)

    # ═══════════════════════════════════════════════════════════════════════════
    # SETAS  Sensores → Logs (rsyslog TCP:514)
    # ═══════════════════════════════════════════════════════════════════════════
    LOG_TOP = LOG_Y + LOG_H
    LOG_CX  = LOG_X + LOG_W / 2

    # Linha de coleta: base de todos os sensores → ponto de convergência → Logs
    CONV_Y = LOG_TOP + 28   # ponto de convergência

    c.setStrokeColor(TEAL)
    c.setLineWidth(1.5)
    c.setDash()
    # Horizontal: da esquerda até a direita na altura CONV_Y
    c.line(sensor_centers[0][0], CONV_Y, sensor_centers[-1][0], CONV_Y)
    # Linhas de cada sensor descendo até CONV_Y
    for scx, sy_bot, sy_top in sensor_centers:
        c.line(scx, sy_bot, scx, CONV_Y)
    # Linha vertical CONV_Y → topo do Logs box
    c.setStrokeColor(TEAL)
    c.line(LOG_CX, CONV_Y, LOG_CX, LOG_TOP)

    # Arrowhead no topo do Logs box
    import math
    hs = 7
    ang = math.pi / 2  # apontando para baixo
    ax1 = LOG_CX - hs * math.cos(math.pi/2 - 0.4)
    ay1 = LOG_TOP - hs * math.sin(math.pi/2 - 0.4)
    ax2 = LOG_CX + hs * math.cos(math.pi/2 + 0.4)
    ay2 = LOG_TOP + hs * math.sin(math.pi/2 + 0.4)
    # Simples: seta manual apontando para baixo (entrando em cima do box)
    c.setFillColor(TEAL)
    p = c.beginPath()
    p.moveTo(LOG_CX, LOG_TOP)
    p.lineTo(LOG_CX - hs/2, LOG_TOP + hs)
    p.lineTo(LOG_CX + hs/2, LOG_TOP + hs)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    text(c, LOG_CX + 6, CONV_Y + 5,
         "rsyslog TCP:514 → logs de update (JSON)",
         "Helvetica-Oblique", 6.5, TEAL, align="left")

    # ═══════════════════════════════════════════════════════════════════════════
    # LEGENDA  (canto inferior direito)
    # ═══════════════════════════════════════════════════════════════════════════
    LG_X, LG_Y, LG_W, LG_H = PW - 160, 28, 145, 100
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(LG_X, LG_Y, LG_W, LG_H, 3, fill=1, stroke=1)
    text(c, LG_X + LG_W/2, LG_Y + LG_H - 13, "LEGENDA",
         "Helvetica-Bold", 7.5, NAVY, align="center")
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.4)
    c.line(LG_X + 8, LG_Y + LG_H - 18, LG_X + LG_W - 8, LG_Y + LG_H - 18)

    legend_items = [
        (NAVY,  False, "Fluxo de atualização"),
        (BLUE,  True,  "Polling (timer)"),
        (TEAL,  False, "Envio de logs (rsyslog)"),
        (BLUE,  False, "Fluxo interno CI/CD"),
    ]
    for i, (col, dash, label) in enumerate(legend_items):
        yy = LG_Y + LG_H - 32 - i * 17
        c.setStrokeColor(col)
        c.setLineWidth(1.5)
        if dash:
            c.setDash([4, 3])
        else:
            c.setDash()
        c.line(LG_X + 10, yy + 4, LG_X + 42, yy + 4)
        c.setDash()
        # mini arrowhead
        c.setFillColor(col)
        p = c.beginPath()
        p.moveTo(LG_X + 42, yy + 4)
        p.lineTo(LG_X + 37, yy + 1)
        p.lineTo(LG_X + 37, yy + 7)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
        text(c, LG_X + 48, yy, label, "Helvetica", 7, BLACK)

    # ═══════════════════════════════════════════════════════════════════════════
    # NOTA  de fluxo de atualização no sensor (canto superior direito)
    # ═══════════════════════════════════════════════════════════════════════════
    NOTE_X, NOTE_Y, NOTE_W, NOTE_H = PW - 160, 148, 145, 160
    c.setFillColor(colors.HexColor("#FFFDE7"))
    c.setStrokeColor(colors.HexColor("#B8860B"))
    c.setLineWidth(0.8)
    c.roundRect(NOTE_X, NOTE_Y, NOTE_W, NOTE_H, 3, fill=1, stroke=1)
    text(c, NOTE_X + NOTE_W/2, NOTE_Y + NOTE_H - 13, "FLUXO NO SENSOR",
         "Helvetica-Bold", 7.5, colors.HexColor("#7A5500"), align="center")
    c.setStrokeColor(colors.HexColor("#B8860B"))
    c.setLineWidth(0.4)
    c.line(NOTE_X + 8, NOTE_Y + NOTE_H - 18, NOTE_X + NOTE_W - 8, NOTE_Y + NOTE_H - 18)

    steps = [
        "1. Consulta manifest.json",
        "2. Compara versão local",
        "3. Download tar.gz",
        "4. Verifica SHA256 + GPG",
        "5. Extrai release",
        "6. Executa post-install.sh",
        "7. Atualiza VERSION",
        "8. Envia log JSON",
    ]
    for i, step in enumerate(steps):
        yy = NOTE_Y + NOTE_H - 32 - i * 16
        c.setFillColor(colors.HexColor("#B8860B"))
        c.circle(NOTE_X + 12, yy + 3, 2, fill=1, stroke=0)
        text(c, NOTE_X + 20, yy, step, "Helvetica", 6.5, BLACK)


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    dst = "/Users/senna/WORK/Sensores-Updates/ARQUITETURA-VIGILANT.pdf"
    c = canvas.Canvas(dst, pagesize=landscape(A4))
    c.setTitle("Arquitetura — Vigilant Sensor Update System")
    c.setAuthor("Vigilant NDR")
    c.setSubject("Diagrama de Arquitetura")
    draw_diagram(c)
    c.save()
    print(f"PDF gerado: {dst}")


if __name__ == "__main__":
    main()

"""Painted artwork for the dark 'SecureBank AI' login page (background, shield logo, field icons).
Everything is drawn in code, so it stays sharp at any window size. Used only by main.LoginWindow."""
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)

CYAN = QColor("#19b7ff")
CYAN_SOFT = QColor(25, 183, 255, 110)


def _glow_pen(p, path, color=CYAN, width=1.6):
    """Draw a path with a soft glow (wide faint stroke + thin bright stroke)."""
    glow = QColor(color)
    glow.setAlpha(34)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(glow, width * 4.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(path)
    core = QColor(color)
    core.setAlpha(150)
    p.setPen(QPen(core, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPath(path)


def _circuit(p, pts, dot_end=True):
    path = QPainterPath(QPointF(*pts[0]))
    for x, y in pts[1:]:
        path.lineTo(x, y)
    _glow_pen(p, path)
    if dot_end:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(60, 180, 255, 230))
        x, y = pts[-1]
        p.drawEllipse(QPointF(x, y), 3.6, 3.6)


def paint_login_background(p, w, h):
    """Full-window dark-blue tech background (matches the reference design)."""
    p.setRenderHint(QPainter.Antialiasing, True)
    base = QLinearGradient(0, 0, w, h)
    base.setColorAt(0.0, QColor("#020a22"))
    base.setColorAt(0.55, QColor("#04143c"))
    base.setColorAt(1.0, QColor("#020b26"))
    p.fillRect(0, 0, w, h, base)

    for cx, cy, r, a in ((0.23, 0.42, 0.40, 80), (0.74, 0.50, 0.38, 55), (0.62, 1.02, 0.30, 70)):
        g = QRadialGradient(QPointF(w * cx, h * cy), w * r)
        g.setColorAt(0.0, QColor(20, 100, 235, a))
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, w, h, g)

    rnd = random.Random(7)
    gx, gy, gr = w * 0.19, h * 1.18, h * 0.58
    clip = QPainterPath()
    clip.addEllipse(QPointF(gx, gy), gr, gr)
    p.save()
    p.setClipPath(clip)
    step = max(9, int(h / 70))
    p.setPen(Qt.NoPen)
    y = gy - gr
    while y < h:
        x = gx - gr
        while x < gx + gr:
            if rnd.random() < 0.55:
                p.setBrush(QColor(40, 150, 255, rnd.randint(40, 170)))
                p.drawEllipse(QPointF(x, y), 1.6, 1.6)
            x += step
        y += step
    p.restore()
    rim = QPainterPath()
    rim.addEllipse(QPointF(gx, gy), gr, gr)
    _glow_pen(p, rim, QColor(40, 150, 255), 1.2)

    p.setPen(Qt.NoPen)
    p.setBrush(QColor(60, 150, 255, 120))
    for i in range(6):
        for j in range(3):
            p.drawEllipse(QPointF(w * 0.02 + i * 22, h * 0.03 + j * 22), 2.0, 2.0)

    _circuit(p, [(0, h * 0.28), (w * 0.05, h * 0.28), (w * 0.09, h * 0.20), (w * 0.14, h * 0.20)])
    _circuit(p, [(0, h * 0.20), (w * 0.04, h * 0.20), (w * 0.08, h * 0.13), (w * 0.15, h * 0.13), (w * 0.17, h * 0.10)])
    _circuit(p, [(w * 0.72, h * 0.07), (w * 0.80, h * 0.07), (w * 0.84, h * 0.02), (w * 0.93, h * 0.02)])
    _circuit(p, [(w * 0.94, h * 0.12), (w * 0.94, h * 0.20), (w * 0.965, h * 0.25), (w * 0.965, h * 0.36)])
    _circuit(p, [(w, h * 0.78), (w * 0.965, h * 0.78), (w * 0.94, h * 0.84), (w * 0.94, h * 0.93), (w * 0.91, h)])
    _circuit(p, [(w * 0.80, h), (w * 0.84, h * 0.95), (w * 0.93, h * 0.95)])

    d = QPainterPath(QPointF(w * 0.455, 0))
    d.cubicTo(QPointF(w * 0.405, h * 0.33), QPointF(w * 0.46, h * 0.58), QPointF(w * 0.39, h))
    _glow_pen(p, d, QColor(70, 170, 255), 1.8)


def shield_pixmap(size=280):
    """Glowing blue shield with a bank building inside and an orbit ring."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    s = float(size)

    def P(x, y):
        return QPointF(s * x, s * y)

    g = QRadialGradient(P(.5, .5), s * .5)
    g.setColorAt(0.0, QColor(30, 130, 255, 90))
    g.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.fillRect(0, 0, size, size, g)

    ring = QPainterPath()
    ring.addEllipse(QRectF(s * .08, s * .50, s * .84, s * .26))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(60, 170, 255, 150), s * .012))
    p.drawPath(ring)

    sh = QPainterPath(P(.5, .06))
    sh.lineTo(P(.84, .17))
    sh.lineTo(P(.84, .50))
    sh.cubicTo(P(.84, .70), P(.66, .84), P(.5, .94))
    sh.cubicTo(P(.34, .84), P(.16, .70), P(.16, .50))
    sh.lineTo(P(.16, .17))
    sh.closeSubpath()
    fill = QLinearGradient(P(.2, .1), P(.8, .9))
    fill.setColorAt(0.0, QColor("#4db8ff"))
    fill.setColorAt(1.0, QColor("#0a56c8"))
    p.setBrush(QBrush(fill))
    p.setPen(Qt.NoPen)
    p.drawPath(sh)

    inner = QPainterPath(P(.5, .12))
    inner.lineTo(P(.78, .21))
    inner.lineTo(P(.78, .50))
    inner.cubicTo(P(.78, .66), P(.63, .78), P(.5, .86))
    inner.cubicTo(P(.37, .78), P(.22, .66), P(.22, .50))
    inner.lineTo(P(.22, .21))
    inner.closeSubpath()
    p.setBrush(QColor("#061a45"))
    p.drawPath(inner)

    light = QColor("#8fd8ff")
    p.setBrush(light)
    roof = QPainterPath(P(.5, .27))
    roof.lineTo(P(.70, .40))
    roof.lineTo(P(.30, .40))
    roof.closeSubpath()
    p.drawPath(roof)
    p.drawRect(QRectF(s * .31, s * .41, s * .38, s * .025))          # architrave
    for x in (.345, .465, .585):                                     # pillars
        p.drawRect(QRectF(s * x, s * .45, s * .07, s * .20))
    p.drawRect(QRectF(s * .29, s * .66, s * .42, s * .025))          # steps
    p.drawRect(QRectF(s * .26, s * .69, s * .48, s * .022))

    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(120, 205, 255, 200), s * .012))
    p.drawArc(QRectF(s * .08, s * .50, s * .84, s * .26), 180 * 16, 180 * 16)
    p.end()
    return pm


def field_icon(kind, color="#7fb4ff", size=22):
    """Small line icons: 'user', 'lock', 'eye', 'eye_off'."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    s = float(size)
    p.setPen(QPen(QColor(color), s * .08, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if kind == "user":
        p.drawEllipse(QPointF(s * .5, s * .32), s * .17, s * .17)
        body = QPainterPath(QPointF(s * .16, s * .88))
        body.cubicTo(QPointF(s * .16, s * .55), QPointF(s * .84, s * .55), QPointF(s * .84, s * .88))
        body.closeSubpath()
        p.drawPath(body)
    elif kind == "lock":
        p.drawRoundedRect(QRectF(s * .2, s * .45, s * .6, s * .42), s * .08, s * .08)
        sh = QPainterPath(QPointF(s * .32, s * .45))
        sh.lineTo(s * .32, s * .33)
        sh.cubicTo(QPointF(s * .32, s * .08), QPointF(s * .68, s * .08), QPointF(s * .68, s * .33))
        sh.lineTo(s * .68, s * .45)
        p.drawPath(sh)
        p.drawPoint(QPointF(s * .5, s * .66))
    else:  # eye / eye_off
        eye = QPainterPath(QPointF(s * .08, s * .5))
        eye.quadTo(QPointF(s * .5, s * .12), QPointF(s * .92, s * .5))
        eye.quadTo(QPointF(s * .5, s * .88), QPointF(s * .08, s * .5))
        p.drawPath(eye)
        p.drawEllipse(QPointF(s * .5, s * .5), s * .13, s * .13)
        if kind == "eye_off":
            p.drawLine(QPointF(s * .18, s * .86), QPointF(s * .82, s * .14))
    p.end()
    return QIcon(pm)

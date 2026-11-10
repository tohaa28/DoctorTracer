"""Consistent original vector illustrations for tracing wizard choices."""
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPixmap,QPainter,QPen,QColor,QPainterPath,QPolygonF,QFont,QLinearGradient
from math import sin,cos,pi

def icon(kind):
    im=QPixmap(100,90);im.fill(Qt.white);p=QPainter(im);p.setRenderHint(QPainter.Antialiasing)
    ink=QColor('#255478');blue=QColor('#d8ecfa');green=QColor('#239b67')
    p.setPen(QPen(ink,3,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(blue)
    def line(a,b):p.drawLine(QPointF(*a),QPointF(*b))
    def arrow(x,y):
        line((x,y+26),(x,y));line((x,y),(x-9,y+10));line((x,y),(x+9,y+10))
    if kind=='folder':
        path=QPainterPath();path.moveTo(10,26);path.lineTo(10,17);path.lineTo(39,17);path.lineTo(47,26);path.lineTo(88,26);path.lineTo(83,75);path.lineTo(10,75);path.closeSubpath();p.drawPath(path);arrow(51,37)
    elif kind=='clipboard':
        p.drawRoundedRect(QRectF(22,15,58,63),5,5);p.setBrush(Qt.white);p.drawRoundedRect(QRectF(35,10,31,14),3,3)
        for y in [37,49,61]:line((35,y),(65,y))
    elif kind=='gears':
        for x,y,r in [(35,51,27),(72,27,18)]:
            points=[]
            for i in range(48):
                radius=r if i%4 in (1,2) else r*.80
                angle=2*pi*i/48
                points.append(QPointF(x+radius*cos(angle),y+radius*sin(angle)))
            p.setBrush(blue);p.drawPolygon(QPolygonF(points))
            p.setBrush(Qt.white);p.drawEllipse(QRectF(x-r*.3,y-r*.3,r*.6,r*.6))
    elif kind in ('basic','advanced'):
        for x,y in [(25,32),(50,58),(75,40)]:
            line((x,15),(x,76));p.drawRoundedRect(QRectF(x-8,y-6,16,12),3,3)
        if kind=='advanced':p.setPen(QPen(green,3));p.drawEllipse(QRectF(65,5,21,21));line((75,10),(75,21));line((70,16),(80,16))
    elif kind=='auto':
        p.setBrush(ink);p.drawRoundedRect(QRectF(20,46,58,11),3,3)
        for x,y,r in [(72,22,10),(35,20,6),(83,62,6)]:
            p.setBrush(QColor('#ffc857'));p.drawPolygon(QPolygonF([QPointF(x,y-r),QPointF(x+3,y-3),QPointF(x+r,y),QPointF(x+3,y+3),QPointF(x,y+r),QPointF(x-3,y+3),QPointF(x-r,y),QPointF(x-3,y-3)]))
    elif kind=='review':
        p.setPen(QPen(green,4));p.setBrush(QColor('#e0f3e8'));p.drawEllipse(QRectF(18,11,64,64));p.setPen(QPen(green,7,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.drawPolyline(QPolygonF([QPointF(32,44),QPointF(45,57),QPointF(68,30)]))
    elif kind=='photo':
        p.drawRoundedRect(QRectF(10,13,80,63),5,5);p.setBrush(QColor('#ffc857'));p.drawEllipse(QRectF(62,23,13,13));p.setBrush(QColor('#5baf8c'));p.drawPolygon(QPolygonF([QPointF(15,69),QPointF(39,37),QPointF(56,58),QPointF(67,45),QPointF(86,69)]))
    elif kind=='flex':
        g=QLinearGradient(12,0,88,0)
        for j,c in enumerate(['#e76059','#ffc857','#4db68a','#4b9cd3','#8b75be']):g.setColorAt(j/4,QColor(c))
        p.setPen(Qt.NoPen);p.setBrush(g);p.drawRoundedRect(QRectF(12,20,76,50),8,8)
        p.setPen(QPen(Qt.white,4));p.setBrush(Qt.NoBrush);path=QPainterPath();path.moveTo(50,45);path.cubicTo(25,20,20,70,50,45);path.cubicTo(80,20,75,70,50,45);p.drawPath(path)
    elif kind=='fixed':
        colors=['#e76059','#ffc857','#4db68a','#4b9cd3','#8b75be','#36495b']
        for i,c in enumerate(colors):
            p.setBrush(QColor(c));p.setPen(Qt.NoPen);p.drawRoundedRect(QRectF(14+(i%3)*25,18+(i//3)*28,20,23),3,3)
    elif kind=='two':
        p.setBrush(Qt.white);p.drawEllipse(QRectF(18,12,64,64));p.setBrush(ink);p.drawPie(QRectF(18,12,64,64),90*16,180*16)
    elif kind=='save':
        p.drawRoundedRect(QRectF(20,10,60,68),4,4);p.setBrush(Qt.white);p.drawRect(QRectF(32,10,34,22));p.drawRect(QRectF(31,48,38,30));line((39,57),(61,57));line((39,66),(61,66))
    elif kind=='batch':
        for x,y in [(13,12),(26,23),(39,34)]:p.drawRoundedRect(QRectF(x,y,43,43),4,4)
        p.setPen(QPen(green,3));arrow(61,43)
    elif kind in ('aa','hard'):
        p.setBrush(Qt.NoBrush);path=QPainterPath();path.moveTo(15,73)
        if kind=='aa':path.cubicTo(60,73,25,18,85,18)
        else:
            for x,y in [(40,73),(40,49),(63,49),(63,18),(85,18)]:path.lineTo(x,y)
        p.setPen(QPen(ink,6,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.drawPath(path)
    elif kind in ('high','medium','low'):
        level={'high':3,'medium':2,'low':1}[kind]
        for j in range(3):
            p.setBrush(green if j<level else QColor('#dbe2e7'));p.setPen(Qt.NoPen);p.drawRoundedRect(QRectF(20+j*22,66-j*16,14,13+j*16),3,3)
    else:
        p.drawEllipse(QRectF(20,14,60,60));line((36,44),(64,44));line((50,30),(50,58))
    p.end();return im

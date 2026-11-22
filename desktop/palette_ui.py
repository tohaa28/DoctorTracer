"""Shared palette display helpers. Transparent slots are not RGB inks."""
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap,QPainter,QColor
from PySide6.QtCore import Qt

def transparency_slot(owner):
    source=getattr(owner,'source_has_transparency',owner.analysis.get('transparent',False))
    return bool(source and getattr(owner,'flatten_mode','preserve')=='preserve')

def transparent_swatch(width=18,height=19):
    label=QLabel();label.setObjectName('transparentSwatch');label.setProperty('paletteTransparent',True)
    label.setAccessibleName('Прозрачный цвет');label.setToolTip('Прозрачный цвет — фон сохраняется')
    label.setFixedSize(width,height);pix=QPixmap(width,height);pix.fill(Qt.white);p=QPainter(pix)
    for y in range(0,height,4):
        for x in range(0,width,4):
            if (x//4+y//4)%2:p.fillRect(x,y,4,4,QColor('#bcbcbc'))
    p.setPen(Qt.black);p.drawRect(0,0,width-1,height-1);p.end();label.setPixmap(pix);return label

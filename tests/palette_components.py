"""Detailed fixed-palette masks must retain every component in Qt SVG."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
import engine
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtSvg import QSvgRenderer

app = QApplication.instance() or QApplication([])
mask = np.zeros((600, 600), dtype=bool)
for y in range(2, 594, 8):
    for x in range(2, 594, 8):
        mask[y:y+5, x:x+5] = True
# A ring also checks that grouping preserves holes.
mask[240:280, 240:280] = True
mask[250:270, 250:270] = False
paths = engine.native_trace(mask, {'detail': 2, 'mode': 'polygon'})
assert len(paths) > 5000, len(paths)
svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600">' + ''.join(
    f'<path d="{d}" fill="#5092b9" fill-rule="nonzero"/>' for d in paths) + '</svg>'
im = QImage(600, 600, QImage.Format_RGBA8888)
im.fill(Qt.transparent)
painter = QPainter(im)
QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, 600, 600))
painter.end()
pixels = np.frombuffer(im.bits(), np.uint8).reshape(600, 600, 4)
assert pixels[260, 260, 3] == 0
assert pixels[245, 245, 3] > 250
coverage = (pixels[:, :, 3] > 127).sum() / mask.sum()
assert .95 < coverage < 1.05, coverage
print({'ok': True, 'components': len(paths), 'coverage': float(coverage)})

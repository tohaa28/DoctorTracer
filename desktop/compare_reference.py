"""Compare two local SVG files at identical raster dimensions."""
import argparse,json
from pathlib import Path
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import QByteArray,QRectF,Qt
from PySide6.QtSvg import QSvgRenderer
parser=argparse.ArgumentParser();parser.add_argument('reference',type=Path);parser.add_argument('candidate',type=Path);parser.add_argument('--width',type=int,required=True);parser.add_argument('--height',type=int,required=True);args=parser.parse_args();app=QApplication([])
def render(path):
 renderer=QSvgRenderer(QByteArray(path.read_bytes()))
 if not renderer.isValid():raise ValueError('Invalid SVG: '+path.name)
 image=QImage(args.width,args.height,QImage.Format_RGBA8888);image.fill(Qt.transparent);painter=QPainter(image);renderer.render(painter,QRectF(0,0,args.width,args.height));painter.end();return np.frombuffer(image.bits(),np.uint8).reshape(args.height,args.width,4).copy()
def composite(a,bg):
 alpha=a[:,:,3:4].astype(np.float32)/255;return a[:,:,:3]*alpha+bg*(1-alpha)
ref=render(args.reference);candidate=render(args.candidate);union=(ref[:,:,3]>127)|(candidate[:,:,3]>127);intersection=(ref[:,:,3]>127)&(candidate[:,:,3]>127)
print(json.dumps({'white_mae_0_255':float(np.abs(composite(ref,255)-composite(candidate,255)).mean()),'dark_mae_0_255':float(np.abs(composite(ref,40)-composite(candidate,40)).mean()),'alpha_iou':float(intersection.sum()/union.sum()) if union.any() else 1.},indent=2))

"""Prepare and hit-test individual regions of a traced SVG."""
import re
from functools import lru_cache
import xml.etree.ElementTree as ET

from PySide6.QtCore import Qt
from color_objects import connected_paths
from photo_curves import qpath
from vector_partition import NS

PATH = f'{{{NS}}}path'
TRANSLATE = re.compile(r'translate\(\s*([-+\d.eE]+)[,\s]+([-+\d.eE]+)\s*\)')


def split_regions(svg):
    root = ET.fromstring(svg)
    for parent in list(root.iter()):
        for index, path in reversed(list(enumerate(parent))):
            if path.tag != PATH:
                continue
            parts = connected_paths(path.get('d', ''))
            if len(parts) < 2:
                continue
            parent.remove(path)
            for data in reversed(parts):
                element = ET.Element(path.tag, path.attrib)
                element.set('d', data)
                parent.insert(index, element)
    return ET.tostring(root, encoding='unicode')


@lru_cache(maxsize=1)
def hit_paths(svg):
    root = ET.fromstring(svg)
    view = tuple(map(float, re.split(r'[,\s]+', root.get(
        'viewBox', f"0 0 {root.get('width')} {root.get('height')}").strip())))
    paths = []

    def visit(element, x=0, y=0, rule='nonzero'):
        match = TRANSLATE.fullmatch(element.get('transform', ''))
        if match:
            x += float(match[1])
            y += float(match[2])
        rule = element.get('fill-rule', rule)
        if element.tag == PATH:
            path = qpath(element.get('d', ''))
            path.translate(x, y)
            path.setFillRule(Qt.OddEvenFill if rule == 'evenodd' else Qt.WindingFill)
            paths.append((path.boundingRect(), path))
        for child in element:
            visit(child, x, y, rule)

    visit(root)
    return view, paths


def filter_regions(svg, removed, outline=False):
    root = ET.fromstring(svg)
    if outline:
        root.attrib.pop('data-color-objects', None)
    indices = {path: index for index, path in enumerate(root.iter(PATH))}
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag != PATH:
                continue
            selected = indices[child] in removed
            if selected != outline:
                parent.remove(child)
            elif outline:
                child.attrib.update(fill='none', stroke='#df3030', **{
                    'stroke-width': '1', 'stroke-dasharray': '4 3'})
    return ET.tostring(root, encoding='unicode')

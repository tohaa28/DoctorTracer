"""Picking one connected area must preserve its same-color neighbors."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from PySide6.QtCore import QPointF
from background_regions import filter_regions, hit_paths, split_regions

svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80" viewBox="10 20 200 160">
<g fill="#ff0000" transform="translate(10 20)">
<path d="M0 0 L40 0 L40 40 L0 40 Z M10 10 L10 30 L30 30 L30 10 Z M50 0 L80 0 L80 30 L50 30 Z"/>
</g></svg>'''
split = split_regions(svg)
view, paths = hit_paths(split)
assert view == (10, 20, 200, 160)
assert len(paths) == 2
assert paths[0][1].contains(QPointF(15, 25))
assert not paths[0][1].contains(QPointF(30, 40))
assert paths[1][1].contains(QPointF(65, 25))
remaining = hit_paths(filter_regions(split, {0}))[1]
assert len(remaining) == 1 and remaining[0][1].contains(QPointF(65, 25))
overlay = hit_paths(filter_regions(split, {0}, outline=True))[1]
assert len(overlay) == 1 and overlay[0][1].contains(QPointF(15, 25))
print('PASS: split same-color regions, preserve holes and translated hit geometry')

"""Decode the first raster frame or PDF page into the tracing color space."""
from pathlib import Path
from PIL import Image, ImageOps


def open_raster(path):
    if Path(path).suffix.lower() != '.pdf':
        with Image.open(path) as source:
            return ImageOps.exif_transpose(source).convert('RGBA')

    from PySide6.QtCore import QCoreApplication, QSize
    from PySide6.QtGui import QImage
    from PySide6.QtPdf import QPdfDocument

    app = QCoreApplication.instance() or QCoreApplication([])
    document = QPdfDocument(app)
    try:
        error = document.load(str(path))
        if error != QPdfDocument.Error.None_ or document.pageCount() < 1:
            raise ValueError(f'Не удалось прочитать PDF: {error.name}')
        page = document.pagePointSize(0)
        if page.isEmpty():
            raise ValueError('Первая страница PDF имеет неверный размер')
        scale = min(3, 2400 / max(page.width(), page.height()))
        size = QSize(max(1, round(page.width() * scale)), max(1, round(page.height() * scale)))
        rendered = document.render(0, size)
        if rendered.isNull():
            raise ValueError('Не удалось отрисовать первую страницу PDF')
        image = rendered.convertToFormat(QImage.Format_RGBA8888)
        return Image.frombytes('RGBA', (image.width(), image.height()), bytes(image.constBits()),
                               'raw', 'RGBA', image.bytesPerLine())
    finally:
        document.close()
        document.setParent(None)

"""Decode the first raster frame or PDF page into the tracing color space."""
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from threading import RLock
import os
import ctypes
MAX_INPUT_BYTES = 150_000_000
_decode_lock = RLock()

def validate_input_file(path):
    size=Path(path).stat().st_size
    if size>MAX_INPUT_BYTES:
        raise ValueError('Файл превышает 150 МБ (150 000 000 байт).')
    return size

def available_memory():
    if os.name=='nt':
        class MemoryStatus(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total_phys',ctypes.c_ulonglong),('avail_phys',ctypes.c_ulonglong),('total_page',ctypes.c_ulonglong),('avail_page',ctypes.c_ulonglong),('total_virtual',ctypes.c_ulonglong),('avail_virtual',ctypes.c_ulonglong),('avail_extended',ctypes.c_ulonglong)]
        status=MemoryStatus();status.length=ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return min(status.avail_phys,status.avail_virtual)
    try:return os.sysconf('SC_AVPHYS_PAGES')*os.sysconf('SC_PAGE_SIZE')
    except (AttributeError,ValueError,OSError):return None

def require_raster_memory(width,height,bytes_per_pixel=12):
    if width<1 or height<1:raise ValueError('Некорректные размеры растра')
    need=width*height*bytes_per_pixel
    available=available_memory()
    if available is not None and need>available:
        raise MemoryError(f'Недостаточно доступной памяти для исходного растра {width}×{height}. Изображение не уменьшено.')
    return need

def cmyka_tiff(path):
    # Pillow does not open chunky 8-bit separated CMYK with a fifth alpha sample.
    # Decode this explicit format without downsampling or silently dropping alpha.
    import tifffile
    import numpy as np
    with tifffile.TiffFile(path) as tif:
        page=tif.pages[0]
        if (int(page.photometric)!=5 or page.samplesperpixel!=5 or int(page.planarconfig)!=1
            or page.dtype!=np.dtype('uint8') or tuple(map(int,page.extrasamples))!=(2,)):
            raise ValueError('Не поддерживается данный вариант TIFF CMYK + Alpha')
        require_raster_memory(page.imagewidth,page.imagelength,20)
        pixels=page.asarray()
        if pixels.shape!=(page.imagelength,page.imagewidth,5):raise ValueError('Неверная форма CMYK TIFF')
        im=Image.fromarray(np.ascontiguousarray(pixels[:,:,:4]),'CMYK').convert('RGBA')
        im.putalpha(Image.fromarray(pixels[:,:,4]))
        orientation=page.tags.get('Orientation')
        if orientation:
            im.getexif()[274]=int(orientation.value)
            im=ImageOps.exif_transpose(im)
        xr=page.tags.get('XResolution');yr=page.tags.get('YResolution');unit=page.tags.get('ResolutionUnit')
        if xr and yr and unit and int(unit.value) in (2,3):
            factor=2.54 if int(unit.value)==3 else 1
            im.info['dpi']=(xr.value[0]/xr.value[1]*factor,yr.value[0]/yr.value[1]*factor)
        return im

def open_raster(path):
    validate_input_file(path)
    if Path(path).suffix.lower() != '.pdf':
        # Pillow's default fixed decompression-bomb pixel cap is replaced by
        # a header-based available-memory check before decoding.
        with _decode_lock:
            previous=Image.MAX_IMAGE_PIXELS
            try:
                Image.MAX_IMAGE_PIXELS=None
                try:
                    with Image.open(path) as source:
                        require_raster_memory(*source.size)
                        return ImageOps.exif_transpose(source).convert('RGBA')
                except UnidentifiedImageError:
                    if Path(path).suffix.lower() not in ('.tif','.tiff'):raise
                    return cmyka_tiff(path)
            finally:
                Image.MAX_IMAGE_PIXELS=previous

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
        scale = 3
        size = QSize(max(1, round(page.width() * scale)), max(1, round(page.height() * scale)))
        require_raster_memory(size.width(),size.height())
        rendered = document.render(0, size)
        if rendered.isNull():
            raise ValueError('Не удалось отрисовать первую страницу PDF')
        image = rendered.convertToFormat(QImage.Format_RGBA8888)
        return Image.frombytes('RGBA', (image.width(), image.height()), bytes(image.constBits()),
                               'raw', 'RGBA', image.bytesPerLine())
    finally:
        document.close()
        document.setParent(None)

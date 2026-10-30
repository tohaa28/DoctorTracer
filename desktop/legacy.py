import sys
import os
import io
import json
import shutil
import tempfile
import re
from pathlib import Path

if '--worker' in sys.argv:
    from engine import worker
    sys.exit(worker(sys.argv[sys.argv.index('--worker')+1]))

from PySide6.QtCore import Qt, QRectF, QSize, QProcess, QTimer, QByteArray, Signal
from PySide6.QtGui import (QColor, QPainter, QPixmap, QImage, QFont, QAction, QKeySequence,
                            QIcon, QPen, QPainterPath)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QSlider, QCheckBox, QFileDialog, QMessageBox,
    QFrame, QProgressBar, QScrollArea, QButtonGroup, QColorDialog)
from vector_render import QSvgRenderer
from PIL import Image, ImageOps, ImageDraw
from engine import to_eps

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


class Canvas(QWidget):
    request_open = Signal()
    zoom_changed = Signal(float)

    def __init__(self):
        super().__init__()
        self.pix = None
        self.svg = None
        self.image_size = QSize(800,600)
        self.mode = 'Сравнение'
        self.zoom = 1.
        self.pan = [0.,0.]
        self.drag_start = None
        self.split = .5
        self.drag_split = False
        self.setMinimumSize(380,300)
        self.setMouseTracking(True)

    def load(self, path):
        # Decode through Pillow for EXIF orientation and uniform TIFF/WebP support.
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert('RGBA')
            self.image_size = QSize(*im.size)
            data = im.tobytes()
            self.pix = QPixmap.fromImage(QImage(data, im.width, im.height, im.width*4, QImage.Format_RGBA8888).copy())
        self.svg = None
        self.fit()

    def fit(self):
        self.zoom = 1.
        self.pan = [0.,0.]
        self.zoom_changed.emit(self.zoom)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor('#eceef3'))
        if self.pix is None:
            box = QRectF(self.width()/2-210,self.height()/2-155,420,310)
            p.setPen(QPen(QColor('#c2bed8'), 2, Qt.DashLine))
            p.setBrush(QColor('#f7f6fc'))
            p.drawRoundedRect(box, 24,24)
            p.setPen(QColor('#7357d6'))
            p.setFont(QFont('Segoe UI',42))
            p.drawText(box.adjusted(0,35,0,-170),Qt.AlignCenter,'↥')
            p.setPen(QColor('#242638'))
            p.setFont(QFont('Segoe UI',18,QFont.DemiBold))
            p.drawText(box.adjusted(0,130,0,-90),Qt.AlignCenter,'Перетащите изображение')
            p.setFont(QFont('Segoe UI',11))
            p.setPen(QColor('#737587'))
            p.drawText(box.adjusted(0,195,0,-30),Qt.AlignCenter,'или нажмите, чтобы выбрать файл\nPNG · JPG · BMP · TIFF · WebP')
            return
        iw, ih = self.image_size.width(), self.image_size.height()
        scale = min((self.width()-80)/iw,(self.height()-80)/ih)*self.zoom
        w,h = iw*scale,ih*scale
        r = QRectF((self.width()-w)/2+self.pan[0],(self.height()-h)/2+self.pan[1],w,h)
        p.fillRect(r.adjusted(-1,-1,1,1), QColor('#caced9'))
        p.save(); p.setClipRect(r)
        p.fillRect(r,QColor('white'))
        for y in range(int(r.top()),int(r.bottom())+16,16):
            for x in range(int(r.left()),int(r.right())+16,16):
                if ((x-int(r.left()))//16+(y-int(r.top()))//16)%2==0:
                    p.fillRect(x,y,16,16,QColor('#e8e8ed'))
        p.restore()
        def raster():
            p.setRenderHint(QPainter.SmoothPixmapTransform, scale < 1)
            p.drawPixmap(r, self.pix, QRectF(self.pix.rect()))
        if self.svg and self.mode == 'Вектор':
            self.svg.render(p,r)
        elif self.svg and self.mode == 'Сравнение':
            p.save();p.setClipRect(QRectF(0,0,self.width()*self.split,self.height()))
            raster();p.restore()
            p.save(); p.setClipRect(QRectF(self.width()*self.split,0,self.width(),self.height()))
            self.svg.render(p,r); p.restore()
            x = self.width()*self.split
            p.setPen(QPen(QColor('#7357d6'),2));p.drawLine(int(x),0,int(x),self.height())
            p.setBrush(QColor('#7357d6'));p.drawEllipse(QRectF(x-15,self.height()/2-21,30,42))
            p.setPen(Qt.white);p.setFont(QFont('Segoe UI',12));p.drawText(QRectF(x-15,self.height()/2-21,30,42),Qt.AlignCenter,'↔')
        else: raster()
        p.setFont(QFont('Segoe UI',9,QFont.DemiBold))
        labels = [('ОРИГИНАЛ',16)] if self.mode=='Оригинал' or not self.svg else [('ВЕКТОР',16)] if self.mode=='Вектор' else [('ОРИГИНАЛ',16),('ВЕКТОР',self.width()-100)]
        for txt,x in labels:
            p.setPen(QColor('#626577')); p.drawText(x,26,txt)

    def wheelEvent(self,e):
        self.zoom = max(.1,min(20,self.zoom*(1.15 if e.angleDelta().y()>0 else 1/1.15)))
        self.zoom_changed.emit(self.zoom);self.update()

    def mousePressEvent(self,e):
        if self.pix is None:
            self.request_open.emit();return
        self.drag_split = bool(self.svg and self.mode=='Сравнение' and abs(e.position().x()-self.width()*self.split)<22)
        self.drag_start=e.position()
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self,e):
        if self.drag_start is not None:
            if self.drag_split: self.split=max(.03,min(.97,e.position().x()/self.width()))
            else:
                d=e.position()-self.drag_start
                self.pan[0]+=d.x();self.pan[1]+=d.y()
            self.drag_start=e.position();self.update()
        else:
            self.setCursor(Qt.SplitHCursor if self.svg and self.mode=='Сравнение' and abs(e.position().x()-self.width()*self.split)<22 else Qt.OpenHandCursor)

    def mouseReleaseEvent(self,e):
        self.drag_start=None;self.setCursor(Qt.OpenHandCursor)


STYLE = '''
QWidget {font-family: "Segoe UI"; font-size: 13px; color: #292b3c;}
QMainWindow, #side {background: #fafafd;}
#header {background: white; border-bottom: 1px solid #e3e3ed;}
#brand {font-size: 20px; font-weight: 700; color: #5d42bd;}
#muted {color: #7e8191; font-size: 12px;}
#title {font-size: 19px; font-weight: 600;}
#section {font-size: 12px; font-weight: 700; color: #626579; margin-top: 13px;}
QPushButton {background: white; border: 1px solid #dedee9; border-radius: 7px; padding: 9px 13px;}
QPushButton:hover {border-color: #9d88df; background: #f4f0ff;}
QPushButton:checked {background: #eee8fc; color: #6043bc; border-color: #bdace7;}
QPushButton:disabled {color: #aaaabc; background: #efeff5; border-color: #e7e7ef;}
#primary {background: #7051cf; color: white; font-weight: 600; border: none; padding: 13px;}
#primary:hover {background: #6142bc;}
#primary:disabled {background: #c3b5e8;}
QComboBox,QSpinBox {background: white; border: 1px solid #dcdce7; border-radius: 6px; padding: 7px;}
QComboBox::drop-down {border: none; width: 24px;}
QSlider::groove:horizontal {height: 5px; background: #e1dcec; border-radius: 2px;}
QSlider::handle:horizontal {background: #7957d4; width: 15px; margin: -5px 0; border-radius: 7px;}
QCheckBox {spacing: 9px; padding: 5px 0;}
QProgressBar {background: #ece7f7; border: none; border-radius: 3px; height: 6px;}
QProgressBar::chunk {background: #8060d6; border-radius: 3px;}
QStatusBar {background: white; border-top: 1px solid #e4e4ee; color: #737687;}
QToolTip {background: #292b3c; color: white; border: none; padding: 6px;}
'''


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('DoctorTracer — локальная векторизация')
        self.resize(1320,860);self.setMinimumSize(1040,740)
        self.setAcceptDrops(True)
        self.temp = tempfile.TemporaryDirectory(prefix='vectorstudio-')
        self.file = None;self.svg_text = None;self.result_config=None;self.process = None;self.batch_queue=[];self.batch_errors=[]
        self.batch_total=0;self.batch_dir=None;self.cancelled=False
        self.make_ui()
        self.settings_widgets=[self.preset,self.detail,self.colors,self.mode,self.speckle,self.remove_bg,self.tolerance,self.threshold,self.denoise,self.resolution]
        for w in self.settings_widgets:
            if isinstance(w,QComboBox): w.currentIndexChanged.connect(self.invalidate)
            elif isinstance(w,QCheckBox): w.toggled.connect(self.invalidate)
            else: w.valueChanged.connect(self.invalidate)
        self.preset.currentIndexChanged.connect(self.preset_changed)
        for shortcut,fn in [('Ctrl+O',self.open_dialog),('Ctrl+V',self.paste),('Ctrl+S',self.export),('Ctrl+0',self.canvas.fit)]:
            a=QAction(self);a.setShortcut(QKeySequence(shortcut));a.triggered.connect(fn);self.addAction(a)

    def make_ui(self):
        center=QWidget();self.setCentralWidget(center)
        outer=QVBoxLayout(center);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        header=QFrame();header.setObjectName('header');hl=QHBoxLayout(header);hl.setContentsMargins(23,16,23,16)
        brand=QLabel('◈  DoctorTracer');brand.setObjectName('brand');hl.addWidget(brand)
        tag=QLabel('  DESKTOP  /  OFFLINE');tag.setObjectName('muted');hl.addWidget(tag);hl.addStretch()
        for txt,fn in [('Открыть…',self.open_dialog),('Из буфера',self.paste),('Пакетная обработка',self.batch),('?',self.about)]:
            b=QPushButton(txt);b.clicked.connect(fn);hl.addWidget(b)
        outer.addWidget(header)
        body=QHBoxLayout();body.setSpacing(0);outer.addLayout(body,1)
        stage=QWidget();sl=QVBoxLayout(stage);sl.setContentsMargins(0,0,0,0);sl.setSpacing(0)
        bar=QWidget();bl=QHBoxLayout(bar);bl.setContentsMargins(18,10,18,10)
        self.filename=QLabel('Новое изображение');self.filename.setObjectName('muted');bl.addWidget(self.filename,1)
        group=QButtonGroup(self)
        for i,txt in enumerate(['Оригинал','Сравнение','Вектор']):
            b=QPushButton(txt);b.setCheckable(True);group.addButton(b,i);bl.addWidget(b);b.setChecked(i==1)
            b.clicked.connect(lambda checked,t=txt:self.set_view(t))
        sl.addWidget(bar)
        self.canvas=Canvas();self.canvas.request_open.connect(self.open_dialog);sl.addWidget(self.canvas,1)
        self.palette_bar=QWidget();self.palette_layout=QHBoxLayout(self.palette_bar)
        self.palette_layout.setContentsMargins(18,8,18,4);self.palette_bar.hide();sl.addWidget(self.palette_bar)
        foot=QWidget();fl=QHBoxLayout(foot);fl.setContentsMargins(18,10,18,10)
        self.metrics=QLabel('Колесо — масштаб · Перетаскивание — перемещение');self.metrics.setObjectName('muted');fl.addWidget(self.metrics,1)
        self.zoom_label=QLabel('100%');fl.addWidget(self.zoom_label)
        self.canvas.zoom_changed.connect(lambda z:self.zoom_label.setText(f'{z*100:.0f}%'))
        b=QPushButton('Вписать');b.clicked.connect(self.canvas.fit);fl.addWidget(b);sl.addWidget(foot)
        body.addWidget(stage,1)
        side=QWidget();side.setObjectName('side');side.setFixedWidth(310)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(side);scroll.setFixedWidth(326);scroll.setFrameShape(QFrame.NoFrame)
        right=QWidget();right.setFixedWidth(326)
        right_layout=QVBoxLayout(right);right_layout.setContentsMargins(0,0,0,0);right_layout.setSpacing(0)
        right_layout.addWidget(scroll,1);body.addWidget(right)
        self.panel=QVBoxLayout(side);self.panel.setContentsMargins(22,18,22,18);self.panel.setSpacing(10)
        title=QLabel('Параметры векторизации');title.setObjectName('title');self.panel.addWidget(title)
        desc=QLabel('Из пикселей — в редактируемые кривые');desc.setObjectName('muted');self.panel.addWidget(desc)
        self.section('01   ИСХОДНОЕ ИЗОБРАЖЕНИЕ')
        self.preset=self.combo(['Логотип / иллюстрация','Фотография','Чёрно-белое'])
        self.section('02   ДЕТАЛИ И ЦВЕТА')
        self.label('Детализация')
        self.detail=self.combo(['Низкая · проще контуры','Средняя · баланс','Высокая · больше деталей']);self.detail.setCurrentIndex(1)
        self.label('Палитра · 0 = автоматически')
        self.colors=QSpinBox();self.colors.setRange(0,64);self.colors.setValue(12);self.panel.addWidget(self.colors)
        self.label('Кривые')
        self.mode=self.combo(['Плавные кривые Безье','Прямые отрезки','Пиксельные контуры'])
        self.label('Удалять мелкие пятна · пикселей')
        self.speckle=QSpinBox();self.speckle.setRange(0,100);self.speckle.setValue(4);self.panel.addWidget(self.speckle)
        self.denoise=QCheckBox('Подавление шума');self.panel.addWidget(self.denoise)
        self.section('03   ФОН И ОБРАБОТКА')
        self.remove_bg=QCheckBox('Удалить однотонный фон');self.panel.addWidget(self.remove_bg)
        self.remove_bg.setToolTip('Цвет фона определяется по углам. Удаляются только области, связанные с краем.')
        self.label('Допуск цвета фона')
        self.tolerance=QSpinBox();self.tolerance.setRange(0,150);self.tolerance.setValue(24);self.panel.addWidget(self.tolerance)
        self.label('Порог для чёрно-белого режима')
        self.threshold=QSpinBox();self.threshold.setRange(0,255);self.threshold.setValue(160);self.panel.addWidget(self.threshold)
        self.label('Максимальная сторона обработки')
        self.resolution=self.combo(['1600 px · быстро','2400 px · стандарт','4096 px · подробно']);self.resolution.setCurrentIndex(1)
        self.panel.addStretch(1)
        actions=QWidget();al=QVBoxLayout(actions);al.setContentsMargins(22,16,22,18);al.setSpacing(10);right_layout.addWidget(actions)
        self.run_button=QPushButton('Векторизовать');self.run_button.setObjectName('primary');self.run_button.clicked.connect(self.run_or_cancel);self.run_button.setEnabled(False);al.addWidget(self.run_button)
        self.progress=QProgressBar();self.progress.setTextVisible(False);self.progress.hide();al.addWidget(self.progress)
        self.export_button=QPushButton('Экспорт SVG / EPS / PNG…');self.export_button.clicked.connect(self.export);self.export_button.setEnabled(False);al.addWidget(self.export_button)
        self.hint=QLabel('Файлы обрабатываются на этом компьютере.');self.hint.setWordWrap(True);self.hint.setObjectName('muted');al.addWidget(self.hint)
        self.statusBar().showMessage('Готово · Откройте изображение или перетащите его в окно')

    def label(self,text): self.panel.addWidget(QLabel(text))
    def section(self,text):
        l=QLabel(text);l.setObjectName('section');self.panel.addWidget(l)
    def combo(self,items):
        c=QComboBox();c.addItems(items);self.panel.addWidget(c);return c
    def set_view(self,mode): self.canvas.mode=mode;self.canvas.update()
    def about(self):
        QMessageBox.information(self,'О DoctorTracer','DoctorTracer 1.0\nАвтономный аналог основных сценариев Vector Magic.\n\nДвижок: VTracer 0.6.15 (MIT), интерфейс: PySide6 (LGPLv3).\nSVG и EPS содержат векторные пути; PNG — растровый экспорт.\n\nНе является продуктом Vector Magic. Качество алгоритмов может отличаться.\nСведения REA и лицензии включены в папку приложения.')
    def config(self):
        return {'preset':self.preset.currentText(),'detail':self.detail.currentIndex(),'colors':self.colors.value(),
            'mode':['spline','polygon','none'][self.mode.currentIndex()],'speckle':self.speckle.value(),
            'remove_bg':self.remove_bg.isChecked(),'tolerance':self.tolerance.value(),'threshold':self.threshold.value(),
            'denoise':self.denoise.isChecked(),'max_size':[1600,2400,4096][self.resolution.currentIndex()]}
    def preset_changed(self):
        self.colors.setValue([12,0,2][self.preset.currentIndex()])
        self.denoise.setChecked(self.preset.currentIndex()==1)
    def invalidate(self,*args):
        if self.svg_text:
            self.export_button.setEnabled(False)
            self.hint.setText('Параметры изменены. Нажмите «Векторизовать», чтобы обновить результат.')
    def error(self,text): QMessageBox.warning(self,'DoctorTracer',str(text))
    def open_dialog(self):
        if self.process:return
        path,_=QFileDialog.getOpenFileName(self,'Открыть изображение','','Изображения (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif);;Все файлы (*)')
        if path:self.load(path)
    def load(self,path):
        if self.process:return
        try:self.canvas.load(path)
        except Exception as e:self.error(f'Не удалось открыть изображение:\n{e}');return
        self.file=str(path);self.svg_text=None;self.result_config=None;self.palette_bar.hide()
        self.filename.setText(Path(path).name);self.filename.setToolTip(str(path))
        self.run_button.setEnabled(True);self.export_button.setEnabled(False)
        s=self.canvas.image_size;self.metrics.setText(f'{s.width()} × {s.height()} px · Оригинал')
        self.statusBar().showMessage('Изображение открыто · Настройте параметры и запустите векторизацию')
    def paste(self):
        if self.process:return
        image=QApplication.clipboard().image()
        if image.isNull():self.error('В буфере обмена нет изображения.');return
        path=str(Path(self.temp.name)/'Из буфера.png');image.save(path);self.load(path)
    def dragEnterEvent(self,e):
        if e.mimeData().hasUrls() and not self.process:e.acceptProposedAction()
    def dropEvent(self,e):
        paths=[u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:self.load(paths[0])
    def run_or_cancel(self):
        if self.process:self.cancel();return
        if self.file:self.start_job(self.file,self.config())
    def start_job(self,path,config):
        self.cancelled=False
        self.active_config=dict(config)
        self.job_out=Path(self.temp.name)/'result.svg';self.result_file=Path(self.temp.name)/'result.json'
        self.job_out.unlink(missing_ok=True);self.result_file.unlink(missing_ok=True)
        job={'input':path,'output':str(self.job_out),'result':str(self.result_file),'config':config}
        job_path=Path(self.temp.name)/'job.json';job_path.write_text(json.dumps(job),encoding='utf-8')
        self.process=QProcess(self)
        self.process.finished.connect(self.job_finished);self.process.errorOccurred.connect(self.process_error)
        if getattr(sys,'frozen',False):program=sys.executable;args=['--worker',str(job_path)]
        else:program=sys.executable;args=[str(Path(__file__).resolve()),'--worker',str(job_path)]
        self.run_button.setText('Отменить обработку');self.run_button.setEnabled(True)
        self.export_button.setEnabled(False)
        for w in self.settings_widgets:w.setEnabled(False)
        self.progress.setRange(0,0);self.progress.show()
        self.statusBar().showMessage(f'Обработка: {Path(path).name}'+(f' · {self.batch_total-len(self.batch_queue)}/{self.batch_total}' if self.batch_total else ''))
        self.process.start(program,args)
    def process_error(self,err):
        if err==QProcess.FailedToStart:self.job_finished(-1,QProcess.CrashExit)
    def cancel(self):
        self.cancelled=True;self.batch_queue=[]
        if self.process:self.process.kill()
    def job_finished(self,exit_code,status):
        if self.process is None:return
        if self.process is not getattr(self,'resident_worker',None):self.process.deleteLater()
        self.process=None
        self.progress.hide();self.run_button.setText('Векторизовать');self.run_button.setEnabled(bool(self.file))
        for w in self.settings_widgets:w.setEnabled(True)
        result={}
        if self.result_file.exists():
            try:result=json.loads(self.result_file.read_text(encoding='utf-8'))
            except Exception:pass
        ok=result.get('ok',False) and exit_code==0 and self.job_out.exists() and not self.cancelled
        if self.batch_total:
            if ok:
                try:
                    dest=Path(self.batch_dir)/(Path(self.batch_current).stem+'.svg')
                    n=1
                    while dest.exists():dest=Path(self.batch_dir)/(Path(self.batch_current).stem+f'-{n}.svg');n+=1
                    shutil.copyfile(self.job_out,dest)
                except Exception as e:self.batch_errors.append(f'{Path(self.batch_current).name}: {e}')
            elif not self.cancelled:self.batch_errors.append(f'{Path(self.batch_current).name}: '+result.get('error','Сбой обработки'))
            if self.batch_queue:QTimer.singleShot(0,self.batch_next);return
            self.batch_total=0
            self.statusBar().showMessage('Пакетная обработка отменена' if self.cancelled else 'Пакетная обработка завершена')
            if self.batch_errors:self.error('\n'.join(self.batch_errors))
            elif not self.cancelled:QMessageBox.information(self,'Готово',f'SVG сохранены в:\n{self.batch_dir}')
            self.export_button.setEnabled(bool(self.svg_text) and self.config()==self.result_config);return
        if self.cancelled:self.statusBar().showMessage('Обработка отменена');return
        if not ok:self.error(result.get('error','Процесс векторизации завершился с ошибкой.'));return
        self.svg_text=self.job_out.read_text(encoding='utf-8')
        self.canvas.svg=QSvgRenderer(QByteArray(self.svg_text.encode('utf-8')))
        if not self.canvas.svg.isValid():self.error('Получен некорректный SVG.');return
        self.canvas.update();self.export_button.setEnabled(True)
        self.result_config=self.active_config
        self.update_palette()
        self.metrics.setText(f"{result['width']} × {result['height']} px  ·  {result['paths']} контуров  ·  {result['colors']} цветов  ·  {len(self.svg_text.encode())/1024:.1f} КБ")
        self.hint.setText('Готово. Переместите разделитель для сравнения.')
        self.statusBar().showMessage(f"Векторизация завершена за {result['seconds']} с · Ctrl+S — экспорт")
    def update_palette(self):
        while self.palette_layout.count():
            item=self.palette_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        label=QLabel('Цвета:');label.setObjectName('muted');self.palette_layout.addWidget(label)
        colors=list(dict.fromkeys(re.findall(r'fill="(#[0-9A-Fa-f]{6})"',self.svg_text)))
        for color in colors[:12]:
            button=QPushButton();button.setFixedSize(26,26)
            button.setStyleSheet(f'background:{color};border:1px solid #b4b4c0;border-radius:5px;padding:0;')
            button.setToolTip(f'{color} · нажмите, чтобы заменить цвет')
            button.clicked.connect(lambda checked,c=color:self.edit_color(c));self.palette_layout.addWidget(button)
        if len(colors)>12:self.palette_layout.addWidget(QLabel(f'+{len(colors)-12}'))
        self.palette_layout.addStretch();self.palette_bar.show()
    def edit_color(self,old):
        if self.process or not self.export_button.isEnabled():return
        color=QColorDialog.getColor(QColor(old),self,'Заменить цвет во всех контурах')
        if not color.isValid():return
        self.svg_text=self.svg_text.replace(f'fill="{old}"',f'fill="{color.name()}"')
        self.canvas.svg=QSvgRenderer(QByteArray(self.svg_text.encode('utf-8')))
        self.canvas.update();self.update_palette()
        self.statusBar().showMessage('Цвет изменён · Ctrl+S — экспорт результата')
    def batch(self):
        if self.process:return
        paths,_=QFileDialog.getOpenFileNames(self,'Изображения для пакетной обработки','','Изображения (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif)')
        if not paths:return
        folder=QFileDialog.getExistingDirectory(self,'Папка для SVG')
        if not folder:return
        self.batch_queue=paths;self.batch_total=len(paths);self.batch_dir=folder;self.batch_errors=[];self.batch_config=self.config();self.batch_next()
    def batch_next(self):
        self.batch_current=self.batch_queue.pop(0);self.start_job(self.batch_current,self.batch_config)
    def export(self):
        if not self.svg_text or not self.export_button.isEnabled():return
        path,fmt=QFileDialog.getSaveFileName(self,'Экспорт результата',str(Path(self.file).with_suffix('.svg')),'SVG (*.svg);;EPS (*.eps);;PNG (*.png)')
        if not path:return
        ext={'SVG (*.svg)':'.svg','EPS (*.eps)':'.eps','PNG (*.png)':'.png'}[fmt]
        target=Path(path)
        if target.suffix.lower()!=ext:
            target=target.with_suffix(ext)
            if target.exists() and QMessageBox.question(self,'Заменить файл?',str(target))!=QMessageBox.Yes:return
        try:
            if ext=='.svg':target.write_text(self.svg_text,encoding='utf-8')
            elif ext=='.eps':target.write_text(to_eps(self.svg_text),encoding='ascii')
            else:
                size=self.canvas.image_size
                if size.width()*size.height()>80_000_000:raise ValueError('Слишком большой PNG. Сохраните SVG.')
                im=QImage(size,QImage.Format_ARGB32_Premultiplied);im.fill(Qt.transparent)
                p=QPainter(im);self.canvas.svg.render(p,QRectF(0,0,size.width(),size.height()));p.end()
                if not im.save(str(target)):raise OSError('Не удалось записать PNG')
            self.statusBar().showMessage(f'Сохранено: {target}')
        except Exception as e:self.error(e)
    def closeEvent(self,e):
        if self.process:
            self.process.blockSignals(True);self.process.kill();self.process.waitForFinished(3000)
        self.temp.cleanup();e.accept()


def main():
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    window=MainWindow();window.show()
    if len(sys.argv)>1 and Path(sys.argv[1]).is_file():window.load(sys.argv[1])
    sys.exit(app.exec())

if __name__=='__main__': main()

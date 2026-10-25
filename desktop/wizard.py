"""Wizard layout reconstructed from observed Vector Magic Desktop 1.15."""
import sys,re,json,math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image,ImageDraw
from PySide6.QtCore import Qt,QRectF,QSize,QPointF,QByteArray,Signal,QTimer
from PySide6.QtGui import QPainter,QColor,QPen,QFont,QPixmap,QImage,QLinearGradient,QRadialGradient,QPainterPath,QPolygonF,QAction,QKeySequence,QIcon
from PySide6.QtWidgets import QApplication,QWidget,QPushButton,QLabel,QFrame,QVBoxLayout,QHBoxLayout,QGridLayout,QScrollArea,QGroupBox,QComboBox,QSpinBox,QSlider,QCheckBox,QFileDialog,QMessageBox,QColorDialog,QMenu,QListWidget,QListWidgetItem,QProgressBar
from vector_render import QSvgRenderer
from legacy import MainWindow as ServiceWindow,Canvas as BaseCanvas
from engine import analyze_image,segment,find_palette

STYLE='''
QWidget {font-family:Tahoma;font-size:12px;color:#101010;}
QMainWindow {background:#ededed;}
#wizard {background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #f5f5f5,stop:1 #d4d4d4);border:1px solid #999;}
QScrollArea {background:transparent;border:none;}
QScrollArea>QWidget>QWidget {background:transparent;}
#pageHeader {background:#bcbad4;border-radius:3px;}
#pageTitle {font-size:17px;}
QPushButton {padding:2px 7px;border:1px solid #999;border-radius:4px;background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #fff,stop:.45 #ededed,stop:1 #c9c9c9);}
QPushButton:hover {border:1px solid #efa600;}
QPushButton:pressed {background:#d0d0d0;}
QPushButton:checked {background:#ffb400;border:1px solid #9e6c00;}
QPushButton:disabled {color:#999;border-color:#bbb;}
QGroupBox {border:1px solid #999;border-radius:10px;margin-top:10px;padding:12px 8px 8px;}
QGroupBox::title {subcontrol-origin:margin;left:10px;padding:0 6px;}
QComboBox,QSpinBox {background:#fff;border:1px solid #999;padding:2px;border-radius:3px;min-height:18px;}
QListWidget {border:1px solid #aaa;background:white;}
QListWidget::item:selected {background:#a7a1d8;}
QProgressBar {border:1px solid #999;border-radius:3px;background:white;text-align:center;}
QProgressBar::chunk {background:#39cf24;width:9px;margin:1px;}
QStatusBar {background:#eee;border-top:1px solid #aaa;}
QSlider::groove:vertical {background:#aaa;width:4px;}
QSlider::handle:vertical {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #aaa,stop:1 #ddd);border:1px solid #888;height:14px;margin:0 -7px;border-radius:4px;}
'''

from ui_icons import icon


class Choice(QPushButton):
    def __init__(self,title,text,kind,callback,selected=False,recommended=False):
        super().__init__();self.title=title;self.description=text;self.picture=icon(kind);self.selected=selected;self.recommended=recommended;self.setFixedHeight(100);self.setMinimumWidth(300);self.setCursor(Qt.PointingHandCursor);self.setAccessibleName(title);self.clicked.connect(callback)
    def paintEvent(self,e):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);r=QRectF(1,1,self.width()-2,self.height()-2);g=QLinearGradient(r.topLeft(),r.bottomLeft());g.setColorAt(0,QColor('#fafafa'));g.setColorAt(1,QColor('#cecece'));p.setBrush(g);p.setPen(QPen(QColor('#167822' if self.selected else '#f0a900' if self.underMouse() else '#969696'),2 if self.selected or self.underMouse() else 1));p.drawRoundedRect(r,11,11)
        p.setBrush(Qt.white);p.setPen(QPen(QColor('#999'),1));p.drawRoundedRect(QRectF(4,4,101,92),8,8);p.drawPixmap(5,5,99,90,self.picture)
        x=111;p.setPen(Qt.black);p.setFont(QFont('Tahoma',9,QFont.Bold));p.drawText(QRectF(x,4,self.width()-x-5,27),Qt.TextWordWrap,self.title);p.setFont(QFont('Tahoma',8));p.drawText(QRectF(x+5,29,self.width()-x-12,56),Qt.TextWordWrap,self.description);p.setFont(QFont('Tahoma',8,QFont.Bold))
        if self.recommended:p.setPen(QColor('#000066'));p.drawText(x,92,'Рекомендуется')
        if self.selected:p.setPen(QColor('#167822'));p.drawText(QRectF(self.width()-62,80,54,15),Qt.AlignRight,'Выбор')

class ClassicCanvas(BaseCanvas):
    edit_committed=Signal()
    def __init__(self):
        super().__init__();self.setMinimumSize(300,280);self.mode='Оригинал';self.seg_image=None;self.tool='drag';self.brush_color=QColor('#000000');self.brush_size=3;self.undo_stack=[];self.redo_stack=[];self.contour_renderer=None;self.show_contours=False
        self.nav=QWidget(self);grid=QGridLayout(self.nav);grid.setContentsMargins(0,0,0,0);grid.setSpacing(1)
        for txt,row,col,fn in [('^',0,1,lambda:self.nudge(0,40)),('⊙',0,2,self.fit),('<',1,0,lambda:self.nudge(40,0)),('☼',1,1,self.fit),('>',1,2,lambda:self.nudge(-40,0)),('v',2,1,lambda:self.nudge(0,-40))]:
            b=QPushButton(txt);b.setFixedSize(19,19);b.clicked.connect(fn);grid.addWidget(b,row,col)
        self.zoom_slider=QSlider(Qt.Vertical,self);self.zoom_slider.setRange(-20,30);self.zoom_slider.setValue(0);self.zoom_slider.setFixedSize(20,82);self.zoom_slider.valueChanged.connect(lambda n:self.set_zoom(1.12**n))
        self.layers=QWidget(self);self.layers.setStyleSheet('QWidget {background:#d4d4d4;} QPushButton {padding:1px;} QPushButton:checked {background:#ffb400;border:1px solid #9e6c00;}');ll=QVBoxLayout(self.layers);ll.setContentsMargins(3,3,3,3);ll.setSpacing(2);self.layer_buttons={}
        for name,key in [('Bitmap','B'),('Сегменты','S'),('Вектор','V')]:
            b=QPushButton(f'{name} ({key})');b.setCheckable(True);b.setFixedSize(68,22);b.clicked.connect(lambda checked,n=name:self.layer(n));ll.addWidget(b);self.layer_buttons[name]=b
        self.outline_check=QCheckBox('Контуры');self.outline_check.toggled.connect(self.toggle_contours);ll.addWidget(self.outline_check);self.refresh_tools()
    def nudge(self,x,y):self.pan[0]+=x;self.pan[1]+=y;self.update()
    def set_zoom(self,z):self.zoom=z;self.zoom_changed.emit(z);self.update()
    def layer(self,name):self.mode={'Bitmap':'Оригинал','Вектор':'Вектор','Сегменты':'Сегменты'}[name];self.refresh_tools();self.update()
    def toggle_contours(self,v):self.show_contours=v;self.update()
    def refresh_tools(self):
        for w in [self.nav,self.zoom_slider,self.layers]:w.setVisible(self.pix is not None)
        self.layer_buttons['Вектор'].setEnabled(bool(self.svg));self.layer_buttons['Сегменты'].setVisible(self.seg_image is not None)
        for n,m in [('Bitmap','Оригинал'),('Вектор','Вектор'),('Сегменты','Сегменты')]:self.layer_buttons[n].setChecked(self.mode==m)
        self.outline_check.setEnabled(bool(self.svg));self.layers.adjustSize()
    def resizeEvent(self,e):self.nav.move(12,max(18,int(self.height()*.28)));self.nav.adjustSize();self.zoom_slider.move(32,max(85,int(self.height()*.28)+85));self.layers.move(7,max(190,int(self.height()*.58)))
    def load(self,path):super().load(path);self.seg_image=None;self.undo_stack=[];self.redo_stack=[];self.contour_renderer=None;self.mode='Оригинал';self.refresh_tools()
    def image_rect(self):
        iw,ih=self.image_size.width(),self.image_size.height();scale=min((self.width()-2)/iw,(self.height()-2)/ih)*self.zoom
        return QRectF((self.width()-iw*scale)/2+self.pan[0],(self.height()-ih*scale)/2+self.pan[1],iw*scale,ih*scale)
    def paintEvent(self,e):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        if self.pix is None:
            p.fillRect(self.rect(),Qt.white);r=QRectF(self.width()/2-225,self.height()/2-175,450,345)
            if self.width()<470:r=QRectF(25,self.height()/2-155,self.width()-50,310)
            p.setPen(QPen(QColor('#bcbcbc'),3,Qt.DashLine));p.setBrush(Qt.NoBrush);p.drawRoundedRect(r,26,26);p.setPen(QPen(QColor('#bcbcbc'),4));p.drawPolyline(QPolygonF([QPointF(r.center().x()-25,r.top()+55),QPointF(r.center().x()-25,r.top()+115),QPointF(r.center().x()-9,r.top()+101),QPointF(r.center().x()+5,r.top()+126),QPointF(r.center().x()+15,r.top()+119),QPointF(r.center().x(),r.top()+94),QPointF(r.center().x()+20,r.top()+94),QPointF(r.center().x()-25,r.top()+55)]));p.drawRect(QRectF(r.center().x()+15,r.top()+119,35,29));p.drawText(QRectF(r.center().x()+15,r.top()+119,35,29),Qt.AlignCenter,'+');p.setFont(QFont('Tahoma',25));p.drawText(r.adjusted(15,175,-15,-30),Qt.AlignCenter|Qt.TextWordWrap,'Перетащите вашу\nкартинку сюда');return
        tile=QPixmap(16,16);tile.fill(Qt.white);tp=QPainter(tile);tp.fillRect(0,0,8,8,QColor('#bcbcbc'));tp.fillRect(8,8,8,8,QColor('#bcbcbc'));tp.end();p.drawTiledPixmap(self.rect(),tile);r=self.image_rect()
        def raster():p.setRenderHint(QPainter.SmoothPixmapTransform,r.width()<self.image_size.width());p.drawPixmap(r,self.pix,QRectF(self.pix.rect()))
        if self.mode=='Сегменты' and self.seg_image is not None:p.drawImage(r,self.seg_image)
        elif self.mode=='Вектор' and self.svg:self.svg.render(p,r)
        elif self.mode=='Сравнение' and self.svg:
            p.save();p.setClipRect(QRectF(0,0,self.width()*self.split,self.height()));raster();p.restore();p.save();p.setClipRect(QRectF(self.width()*self.split,0,self.width(),self.height()));self.svg.render(p,r);p.restore();p.setPen(QPen(QColor('#678d9d'),1));p.drawLine(int(self.width()*self.split),0,int(self.width()*self.split),self.height())
        else:raster()
        if self.show_contours and self.contour_renderer:self.contour_renderer.render(p,r)
    def coords(self,pos):
        r=self.image_rect()
        if not r.contains(pos):return None
        return QPointF((pos.x()-r.x())/r.width()*self.seg_image.width(),(pos.y()-r.y())/r.height()*self.seg_image.height())
    def mousePressEvent(self,e):
        if self.mode!='Сегменты' or self.seg_image is None or self.tool=='drag':return super().mousePressEvent(e)
        pos=self.coords(e.position())
        if pos is None:return
        if self.tool=='color':self.brush_color=self.seg_image.pixelColor(int(pos.x()),int(pos.y()));self.tool='pencil';return
        self.undo_stack.append(self.seg_image.copy());self.undo_stack=self.undo_stack[-15:];self.redo_stack=[]
        if self.tool=='fill':
            data=self.seg_image.convertToFormat(QImage.Format_RGBA8888);pil=Image.frombytes('RGBA',(data.width(),data.height()),bytes(data.bits()));ImageDraw.floodfill(pil,(int(pos.x()),int(pos.y())),self.brush_color.getRgb());self.seg_image=QImage(pil.tobytes(),pil.width,pil.height,pil.width*4,QImage.Format_RGBA8888).copy();self.update();self.edit_committed.emit()
        else:self.stroke_last=pos;self.draw_stroke(pos,pos)
    def draw_stroke(self,start,end):p=QPainter(self.seg_image);p.setPen(QPen(self.brush_color,self.brush_size,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.drawLine(start,end);p.end();self.update()
    def mouseMoveEvent(self,e):
        if self.mode=='Сегменты' and self.tool=='pencil' and e.buttons()&Qt.LeftButton and hasattr(self,'stroke_last'):
            pos=self.coords(e.position())
            if pos is not None:self.draw_stroke(self.stroke_last,pos);self.stroke_last=pos
        else:super().mouseMoveEvent(e)
    def mouseReleaseEvent(self,e):
        if hasattr(self,'stroke_last'):del self.stroke_last;self.edit_committed.emit()
        super().mouseReleaseEvent(e)

class WizardWindow(ServiceWindow):
    def __init__(self):
        self.page='load';self.history=[];self.wizard_mode='basic';self.category='aa';self.color_mode='fixed';self.manual_palette=None;self.analysis={};self.recent=[];self.curve_tolerance=.12;self.alphamax=1.;self.edit_dirty=False;self.trace_return='review';self.trace_input=None
        super().__init__();self.setWindowTitle('DoctorTracer');self.setWindowIcon(QIcon(str(Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'icon.ico')));self.resize(1200,850);self.setMinimumSize(820,640);self.controls_store.hide();self.render_page();self.canvas.edit_committed.connect(self.edit_changed)
        for key,fn in [('Alt+Left',self.back),('Alt+Right',self.next_page),('Alt+R',self.home),('B',lambda:self.canvas.layer('Bitmap')),('V',lambda:self.canvas.layer('Вектор'))]:
            act=QAction(self);act.setShortcut(QKeySequence(key));act.triggered.connect(fn);self.addAction(act)
    def make_ui(self):
        central=QWidget();self.setCentralWidget(central);layout=QHBoxLayout(central);layout.setContentsMargins(0,0,0,0);layout.setSpacing(4);self.canvas=ClassicCanvas();self.canvas.request_open.connect(self.open_dialog);layout.addWidget(self.canvas,1)
        self.right=QFrame();self.right.setObjectName('wizard');self.right.setFixedWidth(350);rl=QVBoxLayout(self.right);rl.setContentsMargins(4,12,4,4);rl.setSpacing(4);layout.addWidget(self.right)
        header=QFrame();header.setObjectName('pageHeader');hl=QHBoxLayout(header);hl.setContentsMargins(7,4,7,4);self.title=QLabel();self.title.setObjectName('pageTitle');hl.addWidget(self.title,1);help_button=QPushButton('❔ Справка');help_button.setFixedHeight(22);help_button.clicked.connect(self.help_page);hl.addWidget(help_button);rl.addWidget(header)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn);rl.addWidget(self.scroll,1);self.utility=QWidget();ul=QHBoxLayout(self.utility);ul.setContentsMargins(3,0,3,0);updates=QPushButton('О программе');updates.clicked.connect(self.about);ul.addWidget(updates);ul.addStretch();more=QPushButton('Дополнительные Параметры ▾');more.clicked.connect(self.more_menu);ul.addWidget(more);rl.addWidget(self.utility)
        nav=QHBoxLayout();nav.setSpacing(8);self.reset_button=QPushButton('↤  В начало');self.reset_button.clicked.connect(self.home);self.back_button=QPushButton('◀  Назад');self.back_button.clicked.connect(self.back);self.next_button=QPushButton('▶  Вперёд');self.next_button.clicked.connect(self.next_page)
        for b in [self.reset_button,self.back_button,self.next_button]:b.setMinimumHeight(43);nav.addWidget(b,1)
        rl.addLayout(nav);self.zoom_label=QLabel('100%');self.statusBar().addPermanentWidget(self.zoom_label);self.statusBar().addPermanentWidget(QLabel('Локально'));self.statusBar().addPermanentWidget(QLabel('v2.0'));self.canvas.zoom_changed.connect(self.zoom_status)
        self.controls_store=QWidget(self);hidden=QVBoxLayout(self.controls_store);self.preset=QComboBox();self.preset.addItems(['Логотип / иллюстрация','Фотография','Чёрно-белое']);self.detail=QComboBox();self.detail.addItems(['Низкая','Средняя','Высокая']);self.detail.setCurrentIndex(2);self.colors=QSpinBox();self.colors.setRange(0,64);self.colors.setValue(0);self.mode=QComboBox();self.mode.addItems(['Кривые Безье','Полигоны','Пиксели']);self.speckle=QSpinBox();self.speckle.setRange(0,100);self.speckle.setValue(2);self.remove_bg=QCheckBox();self.tolerance=QSpinBox();self.tolerance.setRange(0,150);self.tolerance.setValue(24);self.threshold=QSpinBox();self.threshold.setRange(0,255);self.threshold.setValue(160);self.denoise=QCheckBox();self.resolution=QComboBox();self.resolution.addItems(['1600','2400','4096']);self.resolution.setCurrentIndex(1)
        for w in [self.preset,self.detail,self.colors,self.mode,self.speckle,self.remove_bg,self.tolerance,self.threshold,self.denoise,self.resolution]:hidden.addWidget(w)
        self.filename=QLabel();self.metrics=QLabel();self.hint=QLabel();self.run_button=QPushButton();self.export_button=QPushButton();self.export_button.setEnabled(False);self.progress=QProgressBar();self.palette_bar=QWidget();self.palette_layout=QHBoxLayout(self.palette_bar)
        for w in [self.filename,self.metrics,self.hint,self.run_button,self.export_button,self.progress,self.palette_bar]:hidden.addWidget(w)
    def zoom_status(self,z):
        if self.canvas.pix:self.zoom_label.setText(f'{100*self.canvas.image_rect().width()/self.canvas.image_size.width():.0f}%')
    def config(self):
        cfg=super().config();cfg.update({'category':self.category,'curve_tolerance':self.curve_tolerance*[4,2,1][self.detail.currentIndex()],'alphamax':self.alphamax})
        if self.manual_palette and self.color_mode=='fixed':cfg['palette']=self.manual_palette
        return cfg
    def go(self,page,push=True):
        if self.process:return
        if push and self.page!=page:self.history.append(self.page)
        self.page=page;self.render_page()
    def render_page(self):
        old=self.scroll.takeWidget()
        if old:old.deleteLater()
        content=QWidget();self.page_layout=QVBoxLayout(content);self.page_layout.setContentsMargins(6,3,6,5);self.page_layout.setSpacing(4);self.scroll.setWidget(content)
        names={'load':'Загрузка Изображения','mode':'Режим Мастера','type':'Тип Изображения','transparency':'Прозрачность','quality':'Качество Ввода','color':'Цветовой Режим','palette':'Выбор Палитры','review':'Обзор Результата','export':'Экспорт Результата','segment':'Сегментация Изображения','smooth':'Сглаживание Контуров','edit':'Редактирование Сегментов','background':'Удаление Фона','processing':'Обработка Изображения...'}
        self.title.setText(names[self.page]);self.utility.setVisible(self.page in ('load','mode'));self.reset_button.setText('↶  Сброс' if self.page=='load' else '↤  В начало');self.reset_button.setEnabled(self.page!='load' or bool(self.file));self.back_button.setText('✖  Отмена' if self.page=='processing' else '◀  Назад');self.back_button.setEnabled(self.page=='processing' or bool(self.history));self.next_button.setText('▶  Вперёд');self.next_button.setEnabled(self.page not in ('load','processing'))
        getattr(self,'build_'+self.page)();self.page_layout.addStretch(1);self.canvas.refresh_tools();self.canvas.update();QTimer.singleShot(0,lambda:self.zoom_status(self.canvas.zoom))
    def choice(self,title,text,kind,fn,selected=False,recommended=False):
        c=Choice(title,text,kind,fn,selected,recommended);self.page_layout.addWidget(c);return c
    def group(self,title):g=QGroupBox(title);lay=QVBoxLayout(g);lay.setSpacing(5);self.page_layout.addWidget(g);return lay
    def small_button(self,lay,text,fn,selected=False):
        b=QPushButton(text);b.setCheckable(selected);b.setChecked(selected);b.clicked.connect(fn);lay.addWidget(b,0,Qt.AlignLeft);return b
    def build_load(self):
        self.choice('Импорт из Папки','• Откройте изображение на компьютере.\n• Клавиши быстрого доступа: Ctrl-O.','folder',self.open_dialog);self.choice('Вставить из Буфера Обмена','• Изображение из буфера обмена будет показано слева.','clipboard',self.paste);self.choice('Пакетная Обработка','• Обработка нескольких изображений с одинаковыми параметрами.','batch',self.batch);self.small_button(self.page_layout,'▶ Последние Изображения',self.recent_menu)
    def build_mode(self):
        self.choice('Автоматический','• Векторизация в один клик.','auto',self.automatic);self.choice('Базовый','• Простые вопросы с несколькими вариантами.\n• Пошаговый выбор параметров.','basic',lambda:self.select_mode('basic'),self.wizard_mode=='basic');self.choice('Расширенный','• Тонкие настройки управления.\n• Более сложные варианты.','advanced',lambda:self.select_mode('advanced'),self.wizard_mode=='advanced');self.small_button(self.page_layout,'▶ Последние Основные Настройки',self.load_preset);self.small_button(self.page_layout,'▶ Сохранённые Настройки',self.load_preset)
    def select_mode(self,mode):self.wizard_mode=mode;self.go('type' if mode=='basic' else 'palette')
    def build_type(self):
        recommended=self.analysis.get('category','aa')
        for category,title,description,kind in [('photo','Фотоснимок','• Захват с помощью фото- или веб-камеры.','photo'),('aa','Смешанные Края','• Сглаживание.\n• Наиболее распространённая категория.','aa'),('hard','Чистые Края','• Без сглаживания.\n• Чёткие пиксельные границы.','hard')]:self.choice(title,description,kind,lambda checked=False,c=category:self.choose_type(c),self.category==category,recommended==category)
    def choose_type(self,category):self.category=category;self.preset.setCurrentIndex(1 if category=='photo' else 0);self.colors.setValue(0);self.manual_palette=None;self.go('quality')
    def build_quality(self):
        for n,title,description,kind in [(2,'Высокое Качество','• Большая резкость.\n• Очень мало артефактов сжатия и другого шума.','high'),(1,'Среднее Качество','• Небольшое ухудшение качества.\n• Небольшие артефакты сжатия и другой шум.','medium'),(0,'Низкое Качество','• Размытость.\n• Много артефактов сжатия и другого шума.','low')]:self.choice(title,description,kind,lambda checked=False,value=n:self.choose_quality(value),self.detail.currentIndex()==n,n==2)
    def choose_quality(self,n):self.detail.setCurrentIndex(n);self.denoise.setChecked(n==0);self.go('color')
    def build_color(self):
        for key,title,text,kind in [('two','Два Цвета','• Использование только двух цветов.','two'),('fixed','Настраиваемые Цвета','• Выбор цветов на ваше усмотрение.\n• Используются только указанные вами цвета.','fixed'),('flex','Цвета Без Ограничений','• Используются имеющиеся цвета.\n• Подбор градиентов.','flex')]:self.choice(title,text,kind,lambda checked=False,m=key:self.choose_color(m),self.color_mode==key,(key=='flex')==(self.category=='photo') and key!='two')
    def choose_color(self,mode):
        self.color_mode=mode;self.manual_palette=None;self.colors.setValue(2 if mode=='two' else 0)
        self.go('palette') if mode=='fixed' else self.begin_trace()
    def palette_for(self,n):
        if n==len(self.analysis.get('palette',[])):return list(self.analysis['palette'])
        with Image.open(self.file) as im:im=im.convert('RGBA');im.thumbnail((500,500));arr=np.array(im)
        return ['#%02x%02x%02x'%tuple(c) for c in find_palette(arr,n)]
    def build_palette(self):
        candidates=self.group('Предлагаемые Палитры');lst=QListWidget();lst.setMinimumHeight(255);candidates.addWidget(lst);recommended=max(2,min(24,len(self.analysis.get('palette',[]))));self.palette_candidates=[]
        for n in range(2,min(13,max(7,recommended+2))):
            palette=self.palette_for(n);self.palette_candidates.append(palette);item=QListWidgetItem();item.setSizeHint(QSize(275,27));lst.addItem(item);row=QWidget();rl=QHBoxLayout(row);rl.setContentsMargins(3,3,3,3);rl.setSpacing(2);arrow=QLabel('▶▶' if n==recommended else '');arrow.setFixedWidth(23);arrow.setStyleSheet('color:#318b98;');rl.addWidget(arrow)
            for color in palette[:15]:sw=QLabel();sw.setFixedSize(18,19);sw.setStyleSheet(f'background:{color};border:1px solid black;');rl.addWidget(sw)
            rl.addStretch();lst.setItemWidget(item,row)
            if self.manual_palette==palette or self.manual_palette is None and n==recommended:lst.setCurrentRow(n-2)
        lst.currentRowChanged.connect(self.select_palette_row);lst.itemDoubleClicked.connect(lambda _:self.palette_next());candidates.addWidget(QLabel('Для выбора кликните по палитре дважды.'))
        if self.manual_palette is None:self.manual_palette=list(self.analysis.get('palette') or self.palette_candidates[max(0,lst.currentRow())])
        box=self.group('Пользовательские Палитры');self.palette_swatch_widget=QWidget();self.palette_swatches=QHBoxLayout(self.palette_swatch_widget);self.palette_swatches.setContentsMargins(0,0,0,0);self.palette_swatches.setSpacing(2);box.addWidget(self.palette_swatch_widget);self.draw_palette();tools=QHBoxLayout();add=QPushButton('＋');add.clicked.connect(self.add_color);tools.addWidget(add);remove=QPushButton('−');remove.clicked.connect(self.remove_color);tools.addWidget(remove);box.addLayout(tools)
        if self.wizard_mode=='advanced':box.addWidget(QLabel('Число цветов:'));spin=QSpinBox();spin.setRange(2,24);spin.setValue(len(self.manual_palette));spin.valueChanged.connect(self.generate_palette);box.addWidget(spin)
    def select_palette_row(self,index):
        if index>=0:self.manual_palette=list(self.palette_candidates[index]);self.draw_palette();self.invalidate()
    def draw_palette(self):
        while self.palette_swatches.count():
            item=self.palette_swatches.takeAt(0)
            if item.widget():item.widget().deleteLater()
        for i,color in enumerate(self.manual_palette or []):
            b=QPushButton();b.setFixedSize(23,28);b.setStyleSheet(f'background:{color};border:1px solid black;');b.setToolTip(color);b.clicked.connect(lambda checked,j=i:self.change_palette_color(j));self.palette_swatches.addWidget(b)
        self.palette_swatches.addStretch()
    def change_palette_color(self,index):
        col=QColorDialog.getColor(QColor(self.manual_palette[index]),self,'Цвет палитры')
        if col.isValid():self.manual_palette[index]=col.name();self.draw_palette();self.invalidate()
    def add_color(self):
        col=QColorDialog.getColor(Qt.black,self,'Добавить цвет')
        if col.isValid() and len(self.manual_palette)<24:self.manual_palette.append(col.name());self.draw_palette();self.invalidate()
    def remove_color(self):
        if len(self.manual_palette)>2:self.manual_palette.pop();self.draw_palette();self.invalidate()
    def generate_palette(self,n):self.manual_palette=self.palette_for(n);self.draw_palette();self.invalidate()
    def palette_next(self):
        self.color_mode='fixed'
        if self.wizard_mode=='advanced':self.prepare_segmentation();self.go('segment')
        else:self.begin_trace()
    def build_review(self):
        self.choice('Рецензия Сделанного','• Кликните здесь для продолжения.\n• Далее можно сохранить результат.','review',lambda:self.go('export'),True);improve=self.group('Улучшение Результата');improve.addWidget(QLabel('Уровень Детализации'))
        for n,name in [(2,'Высокое Качество'),(1,'Среднее Качество'),(0,'Низкое Качество')]:self.small_button(improve,'↪ '+name,lambda checked=False,j=n:self.retrace_detail(j),self.detail.currentIndex()==n)
        self.line(improve);improve.addWidget(QLabel('Цвета'));self.small_button(improve,'🌈 Цвета Без Ограничений',lambda:self.choose_color('flex'),self.color_mode=='flex');self.small_button(improve,'🎨 Настраиваемые Цвета',lambda:self.go('palette'),self.color_mode=='fixed');
        if self.color_mode=='fixed':
            improve.addWidget(QLabel('Текущая Палитра (изменить):'));row=QWidget();sw=QHBoxLayout(row);sw.setContentsMargins(0,0,0,0);sw.setSpacing(2)
            for color in list(dict.fromkeys(re.findall(r'fill="(#[0-9A-Fa-f]{6})"',self.svg_text or '')))[:12]:
                b=QPushButton();b.setFixedSize(19,20);b.setStyleSheet(f'background:{color};border:1px solid black;');b.clicked.connect(lambda checked,c=color:self.edit_result_color(c));sw.addWidget(b)
            sw.addStretch();improve.addWidget(row);
        self.line(improve);improve.addWidget(QLabel('Расширенный'));self.small_button(improve,'✂ Удаление Фона',lambda:self.go('background'));self.small_button(improve,'✎ Редактирование Результата',self.open_editor);self.small_button(improve,'↩ Вернуться к Настройкам',lambda:self.go('mode'));self.small_button(improve,'◧ Сравнить Bitmap / Вектор',self.compare_view)
    def line(self,lay):f=QFrame();f.setFrameShape(QFrame.HLine);lay.addWidget(f)
    def retrace_detail(self,n):self.detail.setCurrentIndex(n);self.denoise.setChecked(n==0);self.begin_trace()
    def compare_view(self):self.canvas.mode='Сравнение' if self.canvas.mode!='Сравнение' else 'Вектор';self.canvas.update()
    def edit_result_color(self,old):super().edit_color(old);self.set_contours();self.render_page()
    def build_export(self):
        self.choice('Сохранение Результата','• Сохраните изображение в нужном вам месте.\n• Клавиши быстрого доступа: Ctrl-S.','save',self.export);quick=self.group('Быстрое Сохранение');quick.addWidget(QLabel(Path(self.file).name if self.file else ''));self.small_button(quick,'Сохранить SVG / EPS / PNG...',self.export);options=self.group('Параметры экспорта');note=QLabel('SVG / EPS: редактируемые векторные контуры.\nPNG: растровый экспорт.');note.setWordWrap(True);options.addWidget(note);self.small_button(options,'Экспорт Bitmap',self.export);saved=self.group('Настройки');self.small_button(saved,'Сохранить Настройки...',self.save_preset)
    def build_segment(self):
        self.canvas.layer('Сегменты');g=self.group('Параметры Сегментации');g.addWidget(QLabel('Минимальное число пикселей области'));sp=QSpinBox();sp.setRange(0,100);sp.setValue(self.speckle.value());sp.valueChanged.connect(self.speckle.setValue);g.addWidget(sp);noise=QCheckBox('Подавление шума');noise.setChecked(self.denoise.isChecked());noise.toggled.connect(self.denoise.setChecked);g.addWidget(noise);self.small_button(g,'Обновить Сегментацию',self.update_segmentation);self.small_button(g,'Редактировать Сегментацию',self.open_editor);note=QLabel('Сегментация определяет форму и цвет областей.\nСледующий шаг — сглаживание контуров.');note.setWordWrap(True);g.addWidget(note)
    def prepare_segmentation(self):
        a,labels,palette,original=segment(self.file,self.config());out=np.zeros_like(a);out[:,:,:3]=255
        for i,color in enumerate(palette):out[labels==i,:3]=color;out[labels==i,3]=255
        self.canvas.seg_image=QImage(out.tobytes(),out.shape[1],out.shape[0],out.shape[1]*4,QImage.Format_RGBA8888).copy();self.canvas.undo_stack=[];self.canvas.redo_stack=[];self.edit_dirty=False
    def update_segmentation(self):self.trace_input=None;self.prepare_segmentation();self.canvas.layer('Сегменты')
    def build_smooth(self):
        g=self.group('Сглаживание Контуров');g.addWidget(QLabel('Допуск аппроксимации кривых'));slider=QSlider(Qt.Horizontal);slider.setRange(1,100);slider.setValue(round(self.curve_tolerance*100));slider.valueChanged.connect(self.set_curve_tolerance);g.addWidget(slider);note=QLabel('Меньше — точнее, больше — проще контуры.');note.setWordWrap(True);g.addWidget(note);g.addWidget(QLabel('Обнаружение Острых Углов'));combo=QComboBox();combo.addItems(['Сохранять острые углы','Сбалансированно','Плавные контуры']);combo.setCurrentIndex(1);combo.currentIndexChanged.connect(self.set_corners);g.addWidget(combo);mode=QComboBox();mode.addItems(['Кривые Безье','Прямые отрезки','Пиксельные контуры']);mode.setCurrentIndex(self.mode.currentIndex());mode.currentIndexChanged.connect(self.mode.setCurrentIndex);g.addWidget(mode);self.small_button(g,'Обновить Результат',lambda:self.begin_trace('smooth'));self.small_button(g,'Обзор Результата',lambda:self.go('review'));self.next_button.setEnabled(bool(self.svg_text) and self.export_button.isEnabled())
    def set_curve_tolerance(self,n):self.curve_tolerance=n/100;self.invalidate()
    def set_corners(self,n):self.alphamax=[.65,1.,1.3][n];self.invalidate()
    def build_background(self):
        g=self.group('Удаление Фона');c=QCheckBox('Удалить однотонный фон');c.setChecked(self.remove_bg.isChecked());c.toggled.connect(self.remove_bg.setChecked);g.addWidget(c);g.addWidget(QLabel('Допуск цвета фона'));s=QSpinBox();s.setRange(0,150);s.setValue(self.tolerance.value());s.valueChanged.connect(self.tolerance.setValue);g.addWidget(s);t=QLabel('Удаляются области, соединённые с краем изображения. Замкнутые белые детали сохраняются.');t.setWordWrap(True);g.addWidget(t);self.small_button(g,'Обновить Результат',self.begin_trace)
    def build_edit(self):
        self.canvas.layer('Сегменты');g=self.group('Инструменты Редактора')
        for name,tool in [('Перемещение','drag'),('Заливка','fill'),('Карандаш','pencil'),('Цвет / пипетка','color')]:self.small_button(g,name,lambda checked=False,t=tool:self.set_tool(t),self.canvas.tool==tool)
        size=QSpinBox();size.setRange(1,40);size.setValue(self.canvas.brush_size);size.valueChanged.connect(lambda v:setattr(self.canvas,'brush_size',v));g.addWidget(QLabel('Размер карандаша'));g.addWidget(size);self.small_button(g,'Выбрать Цвет...',self.brush_color_dialog);self.small_button(g,'↶ Отменить',self.undo_edit);self.small_button(g,'↷ Повторить',self.redo_edit);self.small_button(g,'Вернуть Исходные Сегменты',self.update_segmentation);self.small_button(g,'Векторизовать Изменения',self.trace_edits);self.next_button.setText('▶  Обновить' if self.edit_dirty else '▶  Вперёд')
    def open_editor(self):
        if self.canvas.seg_image is None:self.prepare_segmentation()
        self.canvas.tool='pencil';self.go('edit')
    def set_tool(self,t):self.canvas.tool=t;self.render_page()
    def brush_color_dialog(self):
        c=QColorDialog.getColor(self.canvas.brush_color,self,'Цвет Рисования')
        if c.isValid():self.canvas.brush_color=c
    def undo_edit(self):
        if self.canvas.undo_stack:self.canvas.redo_stack.append(self.canvas.seg_image.copy());self.canvas.seg_image=self.canvas.undo_stack.pop();self.edit_changed();self.canvas.update()
    def redo_edit(self):
        if self.canvas.redo_stack:self.canvas.undo_stack.append(self.canvas.seg_image.copy());self.canvas.seg_image=self.canvas.redo_stack.pop();self.edit_changed();self.canvas.update()
    def edit_changed(self):
        self.edit_dirty=True;self.export_button.setEnabled(False)
        if self.page=='edit':self.next_button.setText('▶  Обновить')
    def trace_edits(self):
        if self.canvas.seg_image is None:return
        path=Path(self.temp.name)/'edited-segmentation.png'
        # Editing may use a reduced working bitmap; preserve original document dimensions.
        self.canvas.seg_image.scaled(self.canvas.image_size,Qt.IgnoreAspectRatio,Qt.FastTransformation).save(str(path))
        self.trace_input=str(path)
        rgba=self.canvas.seg_image.convertToFormat(QImage.Format_RGBA8888)
        pixels=np.frombuffer(rgba.bits(),dtype=np.uint8).reshape(rgba.height(),rgba.width(),4)
        inks=np.unique(pixels[pixels[:,:,3]>127,:3],axis=0)
        self.manual_palette=['#%02x%02x%02x'%tuple(c) for c in inks[:64]];self.color_mode='fixed'
        cfg=self.config();cfg['colors']=0;cfg['remove_bg']=False;self.trace_return='review';self.history.append('edit');self.page='processing';self.render_page();self.start_job(str(path),cfg)
    def build_processing(self):
        label=QLabel();label.setPixmap(icon('gears').scaled(200,180,Qt.KeepAspectRatio,Qt.SmoothTransformation));label.setAlignment(Qt.AlignCenter);self.page_layout.addWidget(label);self.page_layout.addSpacing(20);self.page_layout.addWidget(QLabel('Обработка Изображения...'));progress=QProgressBar();progress.setRange(0,0);self.page_layout.addWidget(progress)
    def begin_trace(self,target='review'):
        if self.process or not self.file:return
        if isinstance(target,bool):target='review'
        self.trace_return=target;self.history.append(self.page);self.page='processing';self.render_page();self.start_job(self.trace_input or self.file,self.config())
    def automatic(self):
        self.category=self.analysis.get('category','aa');self.manual_palette=None;self.colors.setValue(0);self.detail.setCurrentIndex(2);self.denoise.setChecked(False);self.color_mode='flex' if self.category=='photo' else 'fixed';self.preset.setCurrentIndex(1 if self.category=='photo' else 0);self.colors.setValue(0);self.begin_trace()
    def job_finished(self,exit_code,status):
        was_batch=bool(self.batch_total);super().job_finished(exit_code,status)
        if was_batch:
            if not self.batch_total:self.page='mode' if self.file else 'load';self.render_page()
            return
        if self.cancelled or not self.svg_text or exit_code:self.page=self.history.pop() if self.history else 'mode'
        else:self.page=self.trace_return;self.canvas.mode='Вектор';self.set_contours();self.edit_dirty=False
        self.render_page()
    def set_contours(self):
        if not self.svg_text:return
        root=ET.fromstring(self.svg_text)
        for el in root.iter():
            if el.tag.endswith('path'):el.set('fill','none');el.set('stroke','#1766a0');el.set('stroke-width','.6')
        self.canvas.contour_renderer=QSvgRenderer(QByteArray(ET.tostring(root)))
    def update_palette(self):pass
    def invalidate(self,*args):
        if self.svg_text:self.export_button.setEnabled(False)
        if self.page=='smooth':self.next_button.setEnabled(False)
    def load(self,path):
        super().load(path)
        if self.file!=str(path):return
        self.manual_palette=None;self.trace_input=None;self.edit_dirty=False;self.color_mode='fixed';self.colors.setValue(0);self.detail.setCurrentIndex(2);self.analysis=analyze_image(path);self.category=self.analysis['category'];self.recent=[str(path)]+[p for p in self.recent if p!=str(path)];self.history=['load'];self.page='mode';self.setWindowTitle(Path(path).name+' - DoctorTracer');self.render_page()
    def home(self):
        if self.process:self.cancel();return
        if self.page=='load':self.file=None;self.svg_text=None;self.canvas.pix=None;self.canvas.svg=None;self.canvas.seg_image=None;self.canvas.refresh_tools();self.canvas.update()
        self.history=[];self.page='load';self.render_page()
    def back(self):
        if self.process:self.cancel();return
        if self.history:self.page=self.history.pop();self.render_page()
    def next_page(self):
        if self.process:return
        if self.page=='mode':self.select_mode(self.wizard_mode)
        elif self.page=='type':self.choose_type(self.category)
        elif self.page=='quality':self.choose_quality(self.detail.currentIndex())
        elif self.page=='color':self.choose_color(self.color_mode)
        elif self.page=='palette':self.palette_next()
        elif self.page=='review':self.go('export')
        elif self.page=='segment':self.go('smooth');self.begin_trace('smooth')
        elif self.page=='smooth':self.go('export')
        elif self.page=='edit':self.trace_edits() if self.edit_dirty else self.go('review')
        elif self.page=='background':self.begin_trace()
        elif self.page=='export':self.export()
    def recent_menu(self):
        menu=QMenu(self)
        for p in self.recent:menu.addAction(Path(p).name,lambda checked=False,path=p:self.load(path))
        if not self.recent:menu.addAction('Нет недавних изображений').setEnabled(False)
        menu.exec(self.mapToGlobal(self.right.pos()))
    def more_menu(self):
        menu=QMenu(self);menu.addAction('Сохранить Настройки...',self.save_preset);menu.addAction('Загрузить Настройки...',self.load_preset);menu.addAction('Пакетная Обработка...',self.batch)
        if self.file:menu.addAction('Расширенный режим',lambda:self.select_mode('advanced'))
        menu.addSeparator();menu.addAction('О программе',self.about);menu.exec(self.mapToGlobal(self.right.pos()))
    def save_preset(self):
        p,_=QFileDialog.getSaveFileName(self,'Сохранить Настройки','vector-settings.json','Настройки (*.json)')
        if p:Path(p).write_text(json.dumps(self.config(),ensure_ascii=False,indent=2),encoding='utf-8')
    def load_preset(self):
        p,_=QFileDialog.getOpenFileName(self,'Загрузить Настройки','','Настройки (*.json)')
        if not p:return
        try:
            cfg=json.loads(Path(p).read_text(encoding='utf-8'));self.category=cfg.get('category','aa');self.manual_palette=cfg.get('palette');self.color_mode='fixed' if self.manual_palette else 'flex';self.detail.setCurrentIndex(int(cfg.get('detail',2)));self.colors.setValue(int(cfg.get('colors',0)));self.speckle.setValue(int(cfg.get('speckle',2)));self.remove_bg.setChecked(bool(cfg.get('remove_bg')));self.curve_tolerance=float(cfg.get('curve_tolerance',.12));self.alphamax=float(cfg.get('alphamax',1.));self.tolerance.setValue(int(cfg.get('tolerance',24)))
            if self.file:self.go('mode')
        except Exception as e:self.error(e)
    def help_page(self):QMessageBox.information(self,'Справка — '+self.title.text(),'Выберите вариант, чтобы перейти к следующему шагу.\n\nВекторизация: палитра → сегментация → сглаживание.\n\nКолесо — масштаб; перетаскивание — перемещение.\nBitmap (B) / Вектор (V) — смена слоя.\nКонтуры — границы полученных фигур.\n\nВ расширенном режиме можно редактировать сегменты и настраивать кривые.')
    def about(self):QMessageBox.information(self,'О DoctorTracer','DoctorTracer 2.0\nМастер построен по исследованию Vector Magic 1.15 через REA.\n\nЛоготипы: анализ палитры, сегментация и Potrace 1.16.\nФотографии: VTracer.\n\nАлгоритм и все результаты не идентичны оригиналу.\nОтчёт REA, сравнения и исходники прилагаются.')

def main():
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE);app.setFont(QFont('Tahoma',9));window=WizardWindow();window.show()
    if len(sys.argv)>1 and Path(sys.argv[1]).is_file():window.load(sys.argv[1])
    sys.exit(app.exec())

"""UI corrections from the step-by-step Desktop 1.15 walkthrough."""
import sys, math, json, copy
import xml.etree.ElementTree as ET
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QSizeF, QRectF, QByteArray, QTimer, QMimeData, QUrl, QMarginsF, QProcess
from PySide6.QtGui import QPainter, QImage, QColor, QDrag, QPdfWriter, QPageSize, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
    QPushButton,QCheckBox,QRadioButton,QButtonGroup,QSpinBox,QSlider,QLineEdit,
    QComboBox,QFileDialog,QMessageBox,QMenu,QFrame,QListWidget,QListWidgetItem,QSizePolicy)
from vector_render import QSvgRenderer
import wizard
from engine import to_eps

def arrow_icon(direction,color='#269cab'):
    paths={'next':'M9 4 L23 16 L9 28 Z','back':'M23 4 L9 16 L23 28 Z','home':'M5 5 H9 V27 H5 Z M24 4 L11 16 L24 28 Z','reset':'M24 9 A11 11 0 1 0 26 22 L22 20 A7 7 0 1 1 21 12 L16 16 H29 V3 Z','cancel':'M8 5 L16 13 L24 5 L27 8 L19 16 L27 24 L24 27 L16 19 L8 27 L5 24 L13 16 L5 8 Z'}
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path d="{paths[direction]}" fill="{color}" stroke="#54747a" stroke-width=".7"/></svg>'
    im=QPixmap(28,28);im.fill(Qt.transparent);p=QPainter(im);QSvgRenderer(QByteArray(svg.encode())).render(p);p.end();return QIcon(im)


class Canvas(wizard.ClassicCanvas):
    def paintEvent(self,e):
        owner=getattr(self,'owner',None)
        if owner and owner.page in ('batchfiles','batchsettings'):
            p=QPainter(self);p.fillRect(self.rect(),Qt.white)
            for i,path in enumerate(owner.batch_files):
                x=8+(i%max(1,self.width()//120))*120;y=8+(i//max(1,self.width()//120))*145;im=wizard.QPixmap(path);p.drawPixmap(x,y,im.scaled(100,100,Qt.KeepAspectRatio,Qt.SmoothTransformation));p.drawText(QRectF(x,y+102,112,38),Qt.AlignCenter|Qt.TextWordWrap,Path(path).name)
            if not owner.batch_files:p.setPen(QColor('#aaa'));p.drawText(self.rect(),Qt.AlignCenter,'Перетащите сюда ваши картинки')
            return
        super().paintEvent(e)
        if owner and owner.page=='background' and getattr(owner,'removed_shapes',None):
            doc=ET.fromstring(owner.background_original);paths=[p for p in doc.iter() if p.tag.endswith('path')]
            for parent in doc.iter():
                for child in list(parent):
                    if child in paths:
                        if paths.index(child) not in owner.removed_shapes:parent.remove(child)
                        else:child.set('fill','none');child.set('stroke','#df3030');child.set('stroke-width','1');child.set('stroke-dasharray','4 3')
            renderer=QSvgRenderer(QByteArray(ET.tostring(doc)));p=QPainter(self);renderer.render(p,self.image_rect());p.end()
    def dropEvent(self,e):
        owner=getattr(self,'owner',None)
        if owner and owner.page=='batchfiles' and e.mimeData().hasUrls():
            files=[u.toLocalFile() for u in e.mimeData().urls() if Path(u.toLocalFile()).is_file()];owner.batch_files=list(dict.fromkeys(owner.batch_files+files));owner.render_page();e.acceptProposedAction();return
        super().dropEvent(e)
    def mousePressEvent(self,e):
        owner=getattr(self,'owner',None)
        if owner and owner.page=='background' and getattr(owner,'background_tool','cut')=='cut':
            owner.toggle_shape(e.position());return
        if owner and owner.page=='palette' and owner.manual_palette:
            r=self.image_rect()
            if r.contains(e.position()):
                x=int((e.position().x()-r.x())/r.width()*self.pix.width());y=int((e.position().y()-r.y())/r.height()*self.pix.height());im=self.pix.toImage()
                if e.modifiers()&Qt.ControlModifier:
                    colors=[im.pixelColor(xx,yy) for xx in range(max(0,x-2),min(im.width(),x+3)) for yy in range(max(0,y-2),min(im.height(),y+3))];color=QColor(*[sum(getattr(c,k)() for c in colors)//len(colors) for k in ['red','green','blue']])
                else:color=im.pixelColor(x,y)
                owner.palette_auto=False;owner.manual_palette[min(owner.selected_color,len(owner.manual_palette)-1)]=color.name();owner.draw_palette();owner.invalidate();return
        if self.mode=='Сегменты' and self.tool=='adapt' and self.seg_image is not None:
            pos=self.coords(e.position())
            if pos is not None:
                import cv2,numpy as np
                im=self.seg_image.convertToFormat(QImage.Format_RGBA8888);a=np.frombuffer(im.bits(),dtype=np.uint8).reshape(im.height(),im.width(),4).copy();x,y=int(pos.x()),int(pos.y());mask=np.all(a==a[y,x],axis=2).astype('uint8');_,labels=cv2.connectedComponents(mask,8);area=labels==labels[y,x];edge=(cv2.dilate(area.astype('uint8'),np.ones((3,3),np.uint8))>0)&~area
                if edge.any():
                    colors,counts=np.unique(a[edge],axis=0,return_counts=True);self.undo_stack.append(self.seg_image.copy());self.redo_stack=[];a[area]=colors[counts.argmax()];self.seg_image=QImage(a.tobytes(),im.width(),im.height(),im.width()*4,QImage.Format_RGBA8888).copy();self.update();self.edit_committed.emit()
            return
        return super().mousePressEvent(e)
    def fit(self):
        self.fit_scale=min((self.width()-2)/self.image_size.width(),(self.height()-2)/self.image_size.height())
        super().fit()
    def image_rect(self):
        iw,ih=self.image_size.width(),self.image_size.height()
        scale=getattr(self,'fit_scale',1)*self.zoom
        return QRectF((self.width()-iw*scale)/2+self.pan[0],(self.height()-ih*scale)/2+self.pan[1],iw*scale,ih*scale)
    def resizeEvent(self,e):
        # Original tools are one vertically centered stack, independent of zoom.
        y=max(10,self.height()//2-130)
        self.nav.adjustSize();self.nav.move(12,y)
        self.zoom_slider.move(32,y+83);self.layers.move(7,y+184)
        if hasattr(self,'editor_tools'):self.editor_tools.move(max(90,self.width()-116),max(20,self.height()//2-130))
    def wheelEvent(self,e):
        if self.pix is None:
            e.ignore();return
        delta=e.pixelDelta().y() if not e.pixelDelta().isNull() else e.angleDelta().y()
        old=self.zoom
        target=max(1.12**-20,min(1.12**30,old*math.exp(delta*.001)))
        ratio=target/old
        x=e.position().x()-self.width()/2;y=e.position().y()-self.height()/2
        self.pan=[x-(x-self.pan[0])*ratio,y-(y-self.pan[1])*ratio]
        self.zoom=target
        self.zoom_slider.blockSignals(True);self.zoom_slider.setValue(round(math.log(self.zoom,1.12)));self.zoom_slider.blockSignals(False)
        self.zoom_changed.emit(self.zoom);self.update();e.accept()


wizard.ClassicCanvas=Canvas


class DragFile(QPushButton):
    def __init__(self,owner,fmt,minimize):
        super().__init__('▱\nПеретащите');self.owner=owner;self.fmt=fmt;self.minimize=minimize;self.setFixedSize(70,78)
    def mousePressEvent(self,e):self.start=e.position();super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        if not e.buttons()&Qt.LeftButton or (e.position()-self.start).manhattanLength()<QApplication.startDragDistance():return
        ext=self.fmt.currentText();p=Path(self.owner.temp.name)/(Path(self.owner.file).stem+ext)
        try:self.owner.write_export(p)
        except Exception as exc:self.owner.error(exc);return
        drag=QDrag(self);mime=QMimeData();mime.setUrls([QUrl.fromLocalFile(str(p))]);drag.setMimeData(mime)
        if self.minimize.isChecked():self.owner.showMinimized()
        drag.exec(Qt.CopyAction)


class Window(wizard.WizardWindow):
    def __init__(self):
        self.adv={'complexity':5,'smoothness':6,'nodes':6,'corners':True,'palette_aa':True,'contour_aa':True,'color_threshold':1,'artifact':2,'auto_palette':True,'auto_segment':True,'auto_trace':True}
        self.default_adv=dict(self.adv)
        self.palette_auto=True;self.compute_backend='gpu';self.photo_spatial=True;self.photo_regions=True;self.flatten_mode='preserve';self.flatten_color='#ffffff';self.palette_cache={}
        self.selected_color=0;self.skip_review=False;self.quick_dir='';self.quick_name='';self.png_scale=100;self.batch_files=[];self.recent_settings=[]
        super().__init__()
        self.canvas.owner=self
        self.canvas.layer_buttons['Сегменты'].setText('Сегменты')
        for button in self.canvas.nav.findChildren(QPushButton):button.setStyleSheet('padding:0px;');button.setFixedSize(19,19)
        for label in self.statusBar().findChildren(QLabel):
            if label.text()=='v2.0':label.setText('v0.18.1 preview')
        self.auto_timer=QTimer(self);self.auto_timer.setSingleShot(True);self.auto_timer.timeout.connect(self.apply_pending)
        for key,fn in [('A',lambda:self.set_background_tool('drag') if self.page=='background' else self.set_tool('drag')),('D',lambda:self.set_background_tool('cut') if self.page=='background' else self.set_tool('adapt')),('F',lambda:self.set_tool('fill')),('X',lambda:self.set_tool('pencil')),('C',lambda:self.set_tool('color')),('Z',lambda:self.undo_background() if self.page=='background' else self.undo_edit()),('Y',lambda:self.redo_background() if self.page=='background' else self.redo_edit()),('T',lambda:self.reset_background() if self.page=='background' else self.update_segmentation())]:
            action=wizard.QAction(self);action.setShortcut(key);action.triggered.connect(fn);self.addAction(action)
    def paragraph(self,lay,text):
        w=QLabel(text);w.setWordWrap(True);lay.addWidget(w);return w
    def small_button(self,lay,text,fn,selected=False):
        b=super().small_button(lay,text,fn,selected);b.setFixedHeight(23)
        if self.page=='review' and ('Качество' in text or 'Цвета' in text or 'Настраиваемые' in text):b.setFixedWidth(205)
        if self.page=='review':
            b.setStyleSheet('text-align:left;padding-left:5px;')
            if any(word in text for word in ['Удаление Фона','Редактирование Результата','Вернуться к Настройкам']):b.setFixedWidth(190)
            if 'Качество' in text:
                b.setText(text.removeprefix('↪ '));kind='high' if 'Высокое' in text else 'medium' if 'Среднее' in text else 'low';b.setIcon(QIcon(wizard.icon(kind)));b.setIconSize(QSize(16,16))
            elif 'Цвета Без Ограничений' in text or 'Настраиваемые Цвета' in text:
                b.setText(text.removeprefix('🌈 ').removeprefix('🎨 '));b.setIcon(QIcon(wizard.icon('flex' if 'Без Ограничений' in text else 'fixed')));b.setIconSize(QSize(16,16))
        return b
    def choose_type(self,category):
        super().choose_type(category)
        if getattr(self,'source_has_transparency',self.analysis.get('transparent')):
            self.page='transparency';self.render_page()
    def build_transparency(self):
        self.paragraph(self.page_layout,'Иногда границы прозрачных регионов смешиваются с цветом фона. Выберите, оставить прозрачность или свести изображение с цветом.')
        for mode,title,text,kind in [('preserve','Оставить Прозрачность','• Подходит для изображений PNG.','fixed'),('white','Свести в Белый Цвет','• Если изображение было сглажено в белый цвет.','two'),('custom','Пользовательские Цвета','• Сведение с выбранным вами цветом.','flex')]:
            self.choice(title,text,kind,lambda checked=False,m=mode:self.choose_transparency(m),self.flatten_mode==mode,mode=='preserve')
        g=self.group('Изменение Настраиваемых Цветов');self.small_button(g,'Выбор Цвета',self.choose_flatten_color);self.paragraph(g,self.flatten_color)
    def choose_flatten_color(self):
        color=wizard.QColorDialog.getColor(QColor(self.flatten_color),self,'Цвет фона')
        if color.isValid():self.flatten_color=color.name();self.render_page()
    def choose_transparency(self,mode):
        self.flatten_mode=mode;self.manual_palette=None
        from engine import analyze_image
        self.analysis=analyze_image(self.file,{'flatten':mode!='preserve','flatten_color':'#ffffff' if mode=='white' else self.flatten_color})
        self.go('quality')
    def collapsible(self,title):
        button=QPushButton('▶ '+title);button.setCheckable(True);self.page_layout.addWidget(button,0,Qt.AlignLeft)
        body=QFrame();body.setStyleSheet('QFrame {border:1px solid #aaa;border-radius:8px;} QFrame QWidget {border:none;}')
        lay=QVBoxLayout(body);lay.setContentsMargins(7,7,7,7);self.page_layout.addWidget(body);body.hide()
        def toggle(on):body.setVisible(on);button.setText(('▼ ' if on else '▶ ')+title)
        button.toggled.connect(toggle);return lay
    def build_load(self):
        super().build_load()
        # Place the folders entry before the images entry.
        b=QPushButton('▶ Последние Папки');b.clicked.connect(self.recent_folders);self.page_layout.insertWidget(3,b,0,Qt.AlignLeft)
    def build_mode(self):
        super().build_mode()
        for b in self.scroll.widget().findChildren(QPushButton):
            if 'Последние Основные' in b.text():b.clicked.disconnect();b.clicked.connect(self.settings_history)
    def settings_history(self):
        menu=QMenu(self)
        for cfg in self.recent_settings:
            title=f"{cfg.get('category','aa')} / {['Низкое','Среднее','Высокое'][cfg.get('detail',2)]} / {len(cfg.get('palette',[])) or cfg.get('colors',0) or 'Авто'} цветов"
            menu.addAction(title,lambda checked=False,c=cfg:self.apply_settings(c))
        if not self.recent_settings:menu.addAction('Нет недавних настроек').setEnabled(False)
        menu.exec(self.mapToGlobal(self.right.pos()))
    def apply_settings(self,cfg):
        self.photo_spatial=bool(cfg.get('photo_spatial',True));self.photo_regions=bool(cfg.get('photo_regions',True))
        if cfg.get('compute') in ('auto','cpu','gpu'):self.compute_backend=cfg['compute']
        self.category=cfg.get('category','aa');self.manual_palette=cfg.get('palette');self.palette_auto=cfg.get('palette_generated',False);self.color_mode='fixed' if self.manual_palette else 'flex';self.detail.setCurrentIndex(int(cfg.get('detail',2)));self.colors.setValue(int(cfg.get('colors',0)));self.speckle.setValue(int(cfg.get('speckle',2)));self.curve_tolerance=float(cfg.get('curve_tolerance',.12));self.adv.update(cfg.get('advanced_ui',{}));self.invalidate();self.render_page()
    def save_preset(self):
        p,_=QFileDialog.getSaveFileName(self,'Сохранение Настроек','vector-settings.json','Настройки (*.json)')
        if p:Path(p).write_text(json.dumps({**self.config(),'advanced_ui':self.adv},ensure_ascii=False,indent=2),encoding='utf-8')
    def load_preset(self):
        p,_=QFileDialog.getOpenFileName(self,'Сохранённые Настройки','','Настройки (*.json)')
        if p:
            try:self.apply_settings(json.loads(Path(p).read_text(encoding='utf-8')))
            except Exception as exc:self.error(exc)
    def more_menu(self):
        menu=QMenu(self);menu.addAction('Паспорт DoctorTracer',self.about);menu.addAction('Восстановить Настройки по Умолчанию',self.restore_defaults);menu.addAction('Изменить Язык',lambda:QMessageBox.information(self,'Язык интерфейса','Русский'));compute=menu.addMenu('Вычисления')
        for title,key in [('Автоматически (GPU при наличии)','auto'),('CPU','cpu'),('OpenCL GPU','gpu')]:
            action=compute.addAction(title);action.setCheckable(True);action.setChecked(self.compute_backend==key);action.triggered.connect(lambda checked=False,k=key:setattr(self,'compute_backend',k))
        action=menu.addAction('Экспериментальная сегментация фото с палитрой')
        action.setCheckable(True);action.setChecked(self.photo_spatial)
        action.setToolTip('Для фотографий с ограниченной палитрой; может менять мелкие детали. После переключения пересчитайте результат.')
        action.toggled.connect(self.set_photo_spatial)
        menu.exec(self.mapToGlobal(self.right.pos()))
    def set_photo_spatial(self,enabled):
        self.photo_spatial=enabled
        self.invalidate()
        self.statusBar().showMessage('Сегментация изменена. Пересчитайте результат с выбранными настройками.')
    def restore_defaults(self):
        self.adv=dict(self.default_adv);self.skip_review=False
        self.compute_backend='gpu';self.photo_spatial=True;self.photo_regions=True;self.flatten_mode='preserve';self.flatten_color='#ffffff'
        self.category='aa';self.color_mode='fixed';self.manual_palette=None;self.detail.setCurrentIndex(2);self.colors.setValue(0);self.speckle.setValue(2);self.denoise.setChecked(False);self.curve_tolerance=.12;self.alphamax=1.;self.remove_bg.setChecked(False);self.invalidate();self.render_page()
    def batch(self):self.go('batchfiles')
    def build_batchfiles(self):
        self.title.setText('Пакетная Обработка');self.choice('Добавление Изображений','• Выберите одно или несколько изображений.','folder',self.add_batch_files)
        self.small_button(self.page_layout,'▶ Последние Папки',self.recent_folders);g=self.group('Файлы Для Обработки');lst=QListWidget();lst.setSelectionMode(QListWidget.ExtendedSelection);lst.setMinimumHeight(310)
        for p in self.batch_files:lst.addItem(p)
        g.addWidget(lst);row=QHBoxLayout()
        def clear():self.batch_files=[];self.render_page()
        def remove():
            selected={item.text() for item in lst.selectedItems()};self.batch_files=[p for p in self.batch_files if p not in selected];self.render_page()
        for label,fn in [('Очистить всё',clear),('Удалить выбранное',remove)]:b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        g.addLayout(row);self.next_button.setEnabled(bool(self.batch_files))
    def add_batch_files(self):
        files,_=QFileDialog.getOpenFileNames(self,'Добавление Изображений','','Изображения (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.gif *.webp)')
        self.batch_files=list(dict.fromkeys(self.batch_files+files));self.render_page()
    def build_batchsettings(self):
        self.title.setText('Настройки Обработки');g=self.group('Настройки Векторизации');self.batch_options={}
        for key,label,items in [('category','Тип Изображения:',['Автоопределение','Смешанные Края','Чистые Края','Фотоснимок']),('quality','Качество Изображения:',['Автоопределение','Высокое','Среднее','Низкое']),('colors','Цветовой Режим:',['Автоопределение','Два Цвета','Настраиваемые Цвета','Цвета Без Ограничений'])]:
            row=QHBoxLayout();row.addWidget(QLabel(label));combo=QComboBox();combo.addItems(items);row.addWidget(combo);g.addLayout(row);self.batch_options[key]=combo
        row=QHBoxLayout();row.addWidget(QLabel('Количество Цветов:'));count=QSpinBox();count.setRange(2,64);count.setValue(3);row.addWidget(count);g.addLayout(row);self.batch_options['count']=count
        g=self.group('Экспорт Папок и Файловых Форматов');self.batch_folder=QLineEdit(self.quick_dir or str(Path(self.batch_files[0]).parent));g.addWidget(self.batch_folder);self.small_button(g,'Обзор...',self.choose_batch_folder);self.batch_format=QComboBox();self.batch_format.addItem('.svg');g.addWidget(self.batch_format);self.paragraph(g,'Файлы с совпадающими именами сохраняются с новым номером.');self.next_button.setText('▶  Начать')
    def choose_batch_folder(self):
        p=QFileDialog.getExistingDirectory(self,'Экспорт Папки',self.batch_folder.text())
        if p:self.batch_folder.setText(p)
    def start_batch(self):
        if not Path(self.batch_folder.text()).is_dir():self.error(ValueError('Выберите существующую папку.'));return
        cfg=self.config();cfg.pop('palette',None);cfg['colors']=0
        category=self.batch_options['category'].currentIndex();quality=self.batch_options['quality'].currentIndex();colors=self.batch_options['colors'].currentIndex()
        if category:cfg['category']=['','aa','hard','photo'][category];cfg['preset']='Фотография' if category==3 else 'Логотип / иллюстрация'
        if quality:cfg['detail']=[0,2,1,0][quality]
        if colors in (1,2):cfg['colors']=2 if colors==1 else self.batch_options['count'].value()
        self.batch_config=cfg;self.batch_queue=list(self.batch_files);self.batch_total=len(self.batch_queue);self.batch_dir=self.batch_folder.text();self.batch_errors=[];self.page='processing';self.render_page();self.batch_next()
    def recent_folders(self):
        menu=QMenu(self)
        for folder in dict.fromkeys(str(Path(p).parent) for p in self.recent):menu.addAction(folder,lambda checked=False,p=folder:self.open_folder(p))
        if not self.recent:menu.addAction('Нет недавних папок').setEnabled(False)
        menu.exec(self.mapToGlobal(self.right.pos()))
    def open_folder(self,folder):
        p,_=QFileDialog.getOpenFileName(self,'Импорт из Папки',folder,'Изображения (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)')
        if p:self.load(p)
    def build_palette(self):
        if self.manual_palette is None:self.palette_auto=True
        if self.wizard_mode!='advanced':
            super().build_palette();return
        g=self.group('Цветовой Режим');self.radios(g,[('Подбор Цветов','fixed'),('Гибкие Цвета','flex')],self.color_mode,lambda v:self.set_palette_mode(v))
        if self.color_mode=='fixed':
            if not self.manual_palette:self.manual_palette=list(self.analysis.get('palette',[])) or self.palette_for(3)
            g=self.group('Выбор Палитры');row=QHBoxLayout();self.palette_swatch_widget=QWidget();self.palette_swatches=QHBoxLayout(self.palette_swatch_widget);self.palette_swatches.setContentsMargins(2,2,2,2);row.addWidget(self.palette_swatch_widget,1);tools=QVBoxLayout()
            for label,fn in [('＋',self.add_color),('×',self.remove_color),('▥',lambda:self.change_palette_color(min(self.selected_color,len(self.manual_palette)-1)))]:
                b=QPushButton(label);b.setFixedSize(24,24);b.clicked.connect(fn);tools.addWidget(b)
            row.addLayout(tools);g.addLayout(row);self.draw_palette();self.paragraph(g,'Выберите сверху цвет для его изменения.\nДля установки цвета — клик на изображении.');self.small_button(g,'Сравнить',self.compare_view)
            g=self.group('Создание Палитры');row=QHBoxLayout();row.addWidget(QLabel('Количество Цветов:'));spin=QSpinBox();spin.setFixedWidth(52);spin.setRange(2,24);spin.setValue(len(self.manual_palette)+int(self.palette_has_transparency()));spin.valueChanged.connect(self.palette_count);row.addWidget(spin);row.addStretch();g.addLayout(row)
            self.paragraph(g,'Высокий порог цвета скрывает мелкие цветовые различия, но более склонен к ошибкам.')
            self.radios(g,[('Низкий',0),('Средний',1),('Высокий',2)],self.adv['color_threshold'],lambda v:self.change_advanced('color_threshold',v,'palette'))
            self.paragraph(g,'Включайте сглаживание при смешанном цветовом крае изображения. Этот факт имеет огромное влияние на определение цвета.')
            self.check(g,'Использовать Сглаживание','palette_aa','palette')
        g=self.group('Авто Обновление');self.check(g,'Авто Обновление Палитры','auto_palette')
        if not self.adv['auto_palette']:self.small_button(g,'Обновить Палитру',lambda:self.palette_count(getattr(self,'pending_count',len(self.manual_palette or [0,0,0])+int(self.palette_has_transparency())),True))
    def radios(self,lay,items,value,callback):
        row=QHBoxLayout();group=QButtonGroup(self)
        for text,key in items:
            b=QRadioButton(text);b.setChecked(key==value);group.addButton(b);b.toggled.connect(lambda on,k=key:callback(k) if on else None);row.addWidget(b)
        lay.addLayout(row)
    def check(self,lay,text,key,pending=None):
        b=QCheckBox(text);b.setChecked(self.adv[key]);b.toggled.connect(lambda v:self.change_advanced(key,v,pending));lay.addWidget(b);return b
    def change_advanced(self,key,value,pending=None):
        self.adv[key]=value
        if key.startswith('auto_'):self.render_page();return
        if pending:self.invalidate();self.pending=pending;self.auto_timer.start(450)
    def apply_pending(self):
        if self.process:return
        p=getattr(self,'pending',None)
        if p=='segment' and self.page=='segment' and self.adv['auto_segment']:self.update_segmentation()
        elif p=='smooth' and self.page=='smooth' and self.adv['auto_trace']:self.begin_trace('smooth')
        elif p=='palette' and self.page=='palette' and self.adv['auto_palette']:self.generate_palette(len(self.manual_palette or [0,0,0])+int(self.palette_has_transparency()))
    def generate_palette(self,n):
        super().generate_palette(n);self.palette_auto=True
    def select_palette_row(self,index):
        super().select_palette_row(index)
        if index>=0:self.palette_auto=True
    def change_palette_color(self,index):
        super().change_palette_color(index);self.palette_auto=False
    def add_color(self):
        super().add_color();self.palette_auto=False
    def palette_count(self,n,force=False):
        self.pending_count=n
        if force or self.adv['auto_palette']:self.generate_palette(n)
    def palette_for(self,n):
        from engine import find_palette
        import numpy as np
        from PIL import Image
        key=(self.file,Path(self.file).stat().st_mtime_ns,n,self.adv['color_threshold'],self.flatten_mode,self.flatten_color)
        if key in self.palette_cache:return list(self.palette_cache[key])
        with Image.open(self.file) as im:
            im=im.convert('RGBA');im.thumbnail((500,500));a=np.array(im)
        if self.flatten_mode!='preserve':
            color=QColor('#ffffff' if self.flatten_mode=='white' else self.flatten_color);bg=np.array([color.red(),color.green(),color.blue()]);alpha=a[:,:,3:4]/255.;a[:,:,:3]=np.round(a[:,:,:3]*alpha+bg*(1-alpha));a[:,:,3]=255
        threshold=[14,24,42][self.adv['color_threshold']] if self.wizard_mode=='advanced' else 24
        result=['#%02x%02x%02x'%tuple(c) for c in find_palette(a,max(1,n-int(self.palette_has_transparency())),merge_distance=threshold)];self.palette_cache[key]=result;return list(result)
    def set_palette_mode(self,v):self.color_mode=v;self.invalidate();self.render_page()
    def draw_palette(self):
        super().draw_palette()
        for i in range(self.palette_swatches.count()):
            b=self.palette_swatches.itemAt(i).widget()
            if isinstance(b,QPushButton):
                i=int(b.property('paletteIndex'))
                b.clicked.disconnect();b.clicked.connect(lambda checked=False,j=i:self.select_swatch(j));b.setStyleSheet(b.styleSheet()+('border:3px solid #7066b4;' if i==self.selected_color else ''))
                b.mouseDoubleClickEvent=lambda e,j=i:self.change_palette_color(j)
    def select_swatch(self,i):self.selected_color=i;self.draw_palette()
    def remove_color(self):
        self.palette_auto=False
        if len(self.manual_palette or [])>2-int(self.palette_has_transparency()):self.manual_palette.pop(min(self.selected_color,len(self.manual_palette)-1));self.selected_color=max(0,min(self.selected_color,len(self.manual_palette)-1));self.draw_palette();self.invalidate()
    def build_segment(self):
        self.canvas.layer('Сегменты');self.paragraph(self.page_layout,'Сегментация — это разбиение изображения на мелкие части, которые затем послужат для создания векторной графики.')
        g=self.group('Настройка Сегментации');self.level_slider(g,'complexity','Меньше Сегментов','Больше Сегментов','segment')
        g=self.group('Установка Минимального Количества Пикселей');self.paragraph(g,'При числе больше 10 возможна потеря качества.');row=QHBoxLayout();label=QLabel('Минимальное Количество Пикселей:');label.setWordWrap(True);row.addWidget(label,1);sp=QSpinBox();sp.setFixedWidth(52);sp.setRange(0,100);sp.setSuffix(' px');sp.setValue(self.speckle.value());sp.valueChanged.connect(lambda v:(self.speckle.setValue(v),self.change_advanced('min_pixels',v,'segment')));row.addWidget(sp);g.addLayout(row)
        g=self.group('Умное Сглаживание Артефактов');self.paragraph(g,'Простое сглаживание может привести к нежелательным сегментам между формами. Умное сглаживание артефактов удаляет такие сегменты.');self.radios(g,[('Без',0),('Умеренное',1),('Сильное',2)],self.adv['artifact'],lambda v:self.change_advanced('artifact',v,'segment'))
        g=self.group('Авто Обновление');self.check(g,'Авто Обновление Сегментации','auto_segment');self.small_button(g,'Обновить',self.update_segmentation)
    def level_slider(self,g,key,left,right,pending):
        slider=QSlider(Qt.Horizontal);slider.setRange(1,11);slider.setTickPosition(QSlider.TicksBelow);slider.setTickInterval(1);slider.setValue(self.adv[key]);g.addWidget(slider);value=QLabel(f'{left}      ({slider.value()})      {right}');value.setStyleSheet('font-size:10px');g.addWidget(value)
        slider.valueChanged.connect(lambda v:(value.setText(f'{left}      ({v})      {right}'),self.change_advanced(key,v,pending)))
    def build_smooth(self):
        self.title.setText('Настройка Сглаживания');g=self.group('Сила Сглаживания');self.level_slider(g,'smoothness','Слабое Сглаживание','Сильное Сглаживание','smooth')
        g=self.group('Выявление Острых Углов');self.paragraph(g,'Даёт более чёткие результаты для изображений, содержащих формы с острыми углами.');self.check(g,'Выявление Острых Углов','corners','smooth')
        g=self.group('Применение Сглаживания');self.paragraph(g,'Включайте сглаживание при смешанном цветовом крае изображения. Этот факт имеет огромное влияние на конечные формы.');self.check(g,'Использовать Сглаживание','contour_aa','smooth')
        g=self.group('Количество Узлов');self.level_slider(g,'nodes','Меньше Узлов','Больше Узлов','smooth');g=self.group('Авто Обновление');self.check(g,'Авто Обновление Векторизации','auto_trace');self.small_button(g,'Обновить',lambda:self.begin_trace('smooth'));self.next_button.setEnabled(bool(self.svg_text) and self.export_button.isEnabled())
    def config(self):
        cfg=super().config();cfg['palette_generated']=bool(getattr(self,'palette_auto',False))
        cfg.update({'compute':self.compute_backend,'photo_spatial':self.photo_spatial,'photo_regions':self.photo_regions,'flatten':self.flatten_mode!='preserve','flatten_color':'#ffffff' if self.flatten_mode=='white' else self.flatten_color})
        if self.wizard_mode=='advanced':
            cfg['curve_tolerance']=.12*2**((6-self.adv['nodes'])/2)*2**((self.adv['smoothness']-6)/4)
            cfg['alphamax']=1. if self.adv['corners'] else 1.34
            cfg['denoise']=self.adv['artifact']>0;cfg['artifact_strength']=self.adv['artifact'];cfg['segmentation_complexity']=self.adv['complexity'];cfg['color_threshold']=self.adv['color_threshold']
            if self.category!='photo':cfg['category']='aa' if self.adv['contour_aa'] else 'hard'
            cfg['palette_aa']=self.adv['palette_aa']
        return cfg
    def post_smooth_tools(self):
        row=QHBoxLayout();b=self.small_button(row,'Сглаживание результата…',self.open_post_smooth);b.setFixedWidth(190)
        undo=self.small_button(row,'Отменить',self.undo_post_smooth);undo.setFixedWidth(80);undo.setEnabled(bool(getattr(self,'post_smooth_undo',[])));self.page_layout.addLayout(row)
        self.small_button(self.page_layout,'Очистка и упрощение…',self.open_post_clean).setFixedWidth(190)
        self.small_button(self.page_layout,'Выравнивание контуров…',self.open_regularizer).setFixedWidth(190)
    def open_regularizer(self):
        from regularize_dialog import open_regularizer
        open_regularizer(self);self.render_page()
    def open_post_clean(self):
        from post_smooth_dialog import open_cleaner
        open_cleaner(self);self.render_page()
    def open_post_smooth(self):
        from post_smooth_dialog import open_smoother
        open_smoother(self);self.render_page()
    def undo_post_smooth(self):
        history=getattr(self,'post_smooth_undo',[])
        if history:
            self.svg_text=history.pop();self.background_original=self.svg_text;self.removed_shapes=set();self.background_undo=[];self.background_redo=[]
            self.canvas.svg=QSvgRenderer(QByteArray(self.svg_text.encode('utf8')));self.set_contours();self.canvas.update();self.render_page()
    def build_review(self):
        super().build_review()
        self.post_smooth_tools()
        # The original has no extra Compare button in this group.
        for b in self.scroll.widget().findChildren(QPushButton):
            if 'Сравнить Bitmap' in b.text():b.hide()
        for label in self.scroll.widget().findChildren(QLabel):
            if label.text() in ['Уровень Детализации','Цвета','Расширенный']:label.setStyleSheet('font-weight:bold;color:#000066;')
            elif label.text()=='Текущая Палитра (изменить):':label.setText('<a href="palette">Текущая Палитра (изменить):</a>');label.linkActivated.connect(lambda _:self.go('palette'))
        self.page_layout.addStretch(1);c=QCheckBox('Пропускать эту страницу в следующий раз');c.setChecked(self.skip_review);c.toggled.connect(lambda v:setattr(self,'skip_review',v));self.page_layout.addWidget(c)
    def job_finished(self,code,status):
        super().job_finished(code,status)
        if self.result_file.exists() and not self.process:
            try:
                stats=json.loads(self.result_file.read_text(encoding='utf-8'));compute=stats.get('compute','CPU');compute+=(' · контуры GPU' if stats.get('contour_compute')=='OpenCL GPU FP64' and not stats.get('smoothing_fallback') else '');self.statusBar().showMessage(f"Готово за {float(stats.get('seconds',0)):.2f} с · {compute}"+(f" · {stats['device']}" if stats.get('device') else ''))
            except (ValueError,OSError):pass
        if not self.process and self.page!='processing' and self.svg_text:
            self.background_original=self.svg_text;self.removed_shapes=set();self.background_undo=[];self.background_redo=[];self.post_smooth_undo=[]
        if self.skip_review and self.page=='review':self.go('export')
    def begin_trace(self,target='review'):
        cfg=self.config()
        if cfg not in self.recent_settings:self.recent_settings.insert(0,cfg);self.recent_settings=self.recent_settings[:10]
        super().begin_trace(target)
    def start_job(self,path,config):
        if self.process:return
        self.cancelled=False;self.trace_name=Path(path).name;self.active_config=dict(config)
        self.job_out=Path(self.temp.name)/'result.svg';self.result_file=Path(self.temp.name)/'result.json'
        self.job_out.unlink(missing_ok=True);self.result_file.unlink(missing_ok=True)
        job_path=Path(self.temp.name)/'job.json';job_path.write_text(json.dumps({'input':path,'output':str(self.job_out),'result':str(self.result_file),'config':config}),encoding='utf-8')
        worker=getattr(self,'resident_worker',None)
        if worker is None:
            worker=QProcess(self);self.resident_worker=worker
            worker.readyReadStandardOutput.connect(self.worker_response)
            worker.finished.connect(lambda code,status,p=worker:self.worker_exit(p,code,status))
            worker.errorOccurred.connect(lambda error,p=worker:self.worker_start_error(p,error))
            if getattr(sys,'frozen',False):worker.start(sys.executable,['--worker-server'])
            else:worker.start(sys.executable,[str(Path(__file__).with_name('app.py')),'--worker-server'])
        self.process=worker
        self.run_button.setEnabled(True);self.export_button.setEnabled(False)
        for control in self.settings_widgets:control.setEnabled(False)
        self.progress.setRange(0,100);self.progress.setValue(0);self.progress.show();self.update_trace_progress(0,'Начало обработки')
        worker.write((json.dumps({'job':str(job_path),'progress':True},ensure_ascii=False)+'\n').encode('utf-8'))
    def worker_response(self):
        worker=self.resident_worker
        while worker and worker.canReadLine():
            line=bytes(worker.readLine()).decode('utf-8',errors='replace')
            try:
                message=json.loads(line)
                if 'progress' in message:
                    if self.process is worker:self.update_trace_progress(message['progress'],message.get('stage','Обработка'))
                    continue
                code=int(message['exit_code'])
            except (ValueError,KeyError,TypeError):continue
            if self.process is worker:self.job_finished(code,QProcess.NormalExit)
    def update_trace_progress(self,value,stage):
        value=max(getattr(self,'trace_percent',0),min(100,int(value))) if value else 0
        self.trace_percent=value
        self.progress.setValue(value)
        if self.page=='processing' and hasattr(self,'processing_progress'):
            self.processing_progress.setValue(value)
            self.processing_label.setText(f'{stage}: {value}%')
        self.statusBar().showMessage(f'Обработка: {value}% · {stage} · {self.trace_name}')
    def worker_exit(self,worker,code,status):
        if self.process is worker:self.job_finished(code if code else -1,status)
        if getattr(self,'resident_worker',None) is worker:self.resident_worker=None
        worker.deleteLater()
    def worker_start_error(self,worker,error):
        if error==QProcess.FailedToStart:self.worker_exit(worker,-1,QProcess.CrashExit)
    def closeEvent(self,event):
        worker=getattr(self,'resident_worker',None)
        if worker:
            worker.blockSignals(True);worker.kill();worker.waitForFinished(3000);self.resident_worker=None;self.process=None
        super().closeEvent(event)
    def build_background(self):
        self.canvas.layer('Вектор');self.paragraph(self.page_layout,'С помощью этой страницы можно удалить фоновые формы из результата.\n\nУдалённые формы не будут экспортированы.\n\n✂ Кликните на форму, которую вы бы хотели удалить. Повторный клик по удалённой форме восстанавливает её.\n\nИнструмент «Рука» позволяет перемещать изображение.\n\nКнопки «Отмена» и «Возврат» позволяют исправить случайные ошибки и восстановить исходное изображение.')
        if not hasattr(self,'background_original'):self.background_original=self.svg_text;self.removed_shapes=set();self.background_undo=[];self.background_redo=[]
        old=getattr(self.canvas,'editor_tools',None)
        if old:old.deleteLater()
        box=QFrame(self.canvas);lay=QVBoxLayout(box);lay.setContentsMargins(3,3,3,3);lay.setSpacing(2);box.setStyleSheet('QFrame {background:#aaa;border:1px solid #888;border-radius:4px;} QPushButton {padding:1px;text-align:left;}')
        for text,fn in [('↶ Отмена (Z)',self.undo_background),('↷ Повтор (Y)',self.redo_background),('↺ Возврат (T)',self.reset_background),('☛ Рука (A)',lambda:self.set_background_tool('drag')),('✂ Ножницы (D)',lambda:self.set_background_tool('cut'))]:self.small_button(lay,text,fn)
        self.canvas.editor_tools=box;box.adjustSize();box.move(max(90,self.canvas.width()-116),max(20,self.canvas.height()//2-70));box.show()
    def set_background_tool(self,t):self.background_tool=t;self.canvas.tool='drag'
    def toggle_shape(self,pos):
        r=self.canvas.image_rect()
        if not r.contains(pos) or not self.background_original:return
        root=ET.fromstring(self.background_original);view=list(map(float,root.get('viewBox',f'0 0 {self.canvas.image_size.width()} {self.canvas.image_size.height()}').split()));x=view[0]+(pos.x()-r.x())/r.width()*view[2];y=view[1]+(pos.y()-r.y())/r.height()*view[3]
        paths=[p for p in root.iter() if p.tag.endswith('path')]
        for index in range(len(paths)-1,-1,-1):
            doc=ET.Element(root.tag,dict(root.attrib));doc.set('viewBox',f'{x-1} {y-1} 2 2');doc.append(copy.deepcopy(paths[index]));renderer=QSvgRenderer(QByteArray(ET.tostring(doc)));im=QImage(3,3,QImage.Format_ARGB32_Premultiplied);im.fill(Qt.transparent);p=QPainter(im);renderer.render(p,QRectF(0,0,3,3));p.end()
            if im.pixelColor(1,1).alpha()>127:
                self.background_undo.append(set(self.removed_shapes));self.background_redo=[]
                if index in self.removed_shapes:self.removed_shapes.remove(index)
                else:self.removed_shapes.add(index)
                self.apply_background();break
    def apply_background(self):
        self.post_smooth_undo=[]
        root=ET.fromstring(self.background_original);paths=[p for p in root.iter() if p.tag.endswith('path')]
        for parent in root.iter():
            for child in list(parent):
                if child in paths and paths.index(child) in self.removed_shapes:parent.remove(child)
        self.svg_text=ET.tostring(root,encoding='unicode');self.canvas.svg=QSvgRenderer(QByteArray(self.svg_text.encode()));self.export_button.setEnabled(True);self.set_contours();self.canvas.update()
    def undo_background(self):
        if self.background_undo:self.background_redo.append(set(self.removed_shapes));self.removed_shapes=self.background_undo.pop();self.apply_background()
    def redo_background(self):
        if self.background_redo:self.background_undo.append(set(self.removed_shapes));self.removed_shapes=self.background_redo.pop();self.apply_background()
    def reset_background(self):
        self.background_undo.append(set(self.removed_shapes));self.removed_shapes=set();self.apply_background()
    def build_edit(self):
        self.canvas.layer('Сегменты');self.paragraph(self.page_layout,'На этой странице вы можете вручную исправить ошибки сегментации.\n\nСделайте прыжок между исходным растровым и выходным векторным изображениями, чтобы увидеть, где есть ошибки.\n\nЧасто мелкие детали не восстанавливаются автоматически. Необходимо отредактировать пиксели так, чтобы в нужном месте имелся чёткий путь.\n\nПопробуйте! Вы всегда можете отменить / сбросить изменения.\n\nВнимание! В случае повторной векторизации потеряются сделанные на этой странице изменения.')
        self.editor_toolbar();self.next_button.setText('▶  Вперёд')
    def editor_toolbar(self):
        old=getattr(self.canvas,'editor_tools',None)
        if old:old.deleteLater()
        box=QFrame(self.canvas);box.setStyleSheet('QFrame {background:#aaa;border:1px solid #888;border-radius:4px;} QPushButton {padding:1px;text-align:left;}');lay=QVBoxLayout(box);lay.setContentsMargins(3,3,3,3);lay.setSpacing(2)
        for text,fn in [('↶ Отмена (Z)',self.undo_edit),('↷ Повтор (Y)',self.redo_edit),('↺ Возврат (T)',self.update_segmentation)]:self.small_button(lay,text,fn)
        lay.addSpacing(8)
        for name,tool in [('☛ Рука (A)','drag'),('ϟ Царапка (D)','adapt'),('▧ Заливка (F)','fill'),('✎ Карандаш (X)','pencil'),('╱ Цвет (C)','color')]:self.small_button(lay,name,lambda checked=False,t=tool:self.set_tool(t),self.canvas.tool==tool)
        color=QPushButton();color.setFixedSize(42,20);color.setStyleSheet(f'background:{self.canvas.brush_color.name()}');color.clicked.connect(self.brush_color_dialog);lay.addWidget(color);size=QSpinBox();size.setRange(1,40);size.setValue(self.canvas.brush_size);size.setToolTip('Размер карандаша');size.valueChanged.connect(lambda v:setattr(self.canvas,'brush_size',v));lay.addWidget(size)
        self.canvas.editor_tools=box;box.adjustSize();box.move(max(90,self.canvas.width()-116),max(20,self.canvas.height()//2-130));box.show()
        for button in box.findChildren(QPushButton):
            if '(' in button.text():button.setFixedSize(100,23)
        box.adjustSize()
    def render_page(self):
        if self.page in ('batchfiles','batchsettings'):
            page=self.page;self.page='load';super().render_page();self.page=page
            while self.page_layout.count():
                item=self.page_layout.takeAt(0)
                if item.widget():item.widget().deleteLater()
            self.utility.hide();self.reset_button.setEnabled(True);self.reset_button.setText('↤  В начало');getattr(self,'build_'+page)();self.page_layout.addStretch()
            for child in [self.canvas.nav,self.canvas.zoom_slider,self.canvas.layers]:child.hide()
            self.align_navigation();self.canvas.update();return
        super().render_page()
        if self.page=='review' and self.page_layout.itemAt(self.page_layout.count()-1).spacerItem():self.page_layout.takeAt(self.page_layout.count()-1)
        self.align_navigation()
        if self.page=='load':self.next_button.setEnabled(bool(self.file))
        if hasattr(self.canvas,'editor_tools'):self.canvas.editor_tools.setVisible(self.page in ('edit','background'))
        if self.page=='export':self.next_button.setEnabled(False)
    def align_navigation(self):
        for button,direction,text in [(self.reset_button,'reset' if self.page=='load' else 'home','Сброс' if self.page=='load' else 'В начало'),(self.back_button,'cancel' if self.page=='processing' else 'back','Отмена' if self.page=='processing' else 'Назад'),(self.next_button,'next','Начать' if self.page=='batchsettings' else 'Вперёд')]:
            button.setText(text);button.setIcon(arrow_icon(direction,'#c04040' if direction=='cancel' else '#269cab'));button.setIconSize(QSize(26,26));button.setFixedHeight(43)
    def next_page(self):
        if self.page=='transparency':self.choose_transparency(self.flatten_mode)
        elif self.page=='load' and self.file:self.go('mode')
        elif self.page=='batchfiles':self.go('batchsettings')
        elif self.page=='batchsettings':self.start_batch()
        elif self.page=='palette' and self.wizard_mode=='advanced' and self.color_mode=='flex':self.prepare_segmentation();self.go('segment')
        elif self.page=='segment':self.canvas.tool='drag';self.go('edit')
        elif self.page=='edit' and self.wizard_mode=='advanced':
            if self.edit_dirty:self.trace_edits();self.trace_return='smooth'
            else:self.begin_trace('smooth')
        elif self.page=='smooth':self.go('background')
        elif self.page=='background':self.go('export')
        else:super().next_page()
    def load(self,path):
        self.palette_auto=True
        self.flatten_mode='preserve';self.selected_color=0
        super().load(path)
    def about(self):
        QMessageBox.information(self,'Паспорт DoctorTracer','DoctorTracer 0.18.1 preview\n\nЛокальная трассировка SVG / EPS / PDF / PNG.\nSVG: группы по цветам, устранение наложений геометрии.\n\nGPU ускоряет фильтрацию фотографий, назначение цветов, пространственную сегментацию, сглаживание общих границ, упрощение цепочек и расчёт контрольных точек Безье.\nСвязность графа, объединение областей и проверка геометрии выполняются на CPU.\n\nНастройки находятся в меню «Дополнительные Параметры».')
    def build_export(self):
        self.post_smooth_tools()
        self.choice('Сохранение Результата','• Совет: Попробуйте перетащить изображение в нужное вам место.\n• Клавиши быстрого доступа: Ctrl-S.','save',self.export)
        g=self.group('Перетаскивание Файла');row=QHBoxLayout();fmt=QComboBox();fmt.addItems(['.pdf','.svg','.eps']);mini=QCheckBox('Минимизировать окно');mini.setChecked(True);row.addWidget(DragFile(self,fmt,mini));right=QVBoxLayout();right.addWidget(fmt,0,Qt.AlignLeft);self.paragraph(right,'Перетащите файл в нужную директорию.');row.addLayout(right);g.addLayout(row);g.addWidget(mini)
        q=self.collapsible('Быстрое Сохранение');self.export_fields(q,False)
        q=self.collapsible('Экспорт Bitmap');self.export_fields(q,True)
        q=self.collapsible('Параметры Экспорта');self.paragraph(q,'SVG / EPS / PDF: кривые Безье и составные контуры.\nPNG: прозрачный фон, заданный размер.\nAI, EMF и DXF в этой версии не поддерживаются.')
        q=self.collapsible('Сохранение Настроек');self.small_button(q,'Сохранить Настройки...',self.save_preset)
    def export_fields(self,g,bitmap):
        folder=QLineEdit(self.quick_dir or (str(Path(self.file).parent) if self.file else ''));folder.setMinimumWidth(0);folder.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);row=QHBoxLayout();row.addWidget(folder);browse=QPushButton('Обзор ▾');row.addWidget(browse);g.addLayout(row)
        def choose():
            p=QFileDialog.getExistingDirectory(self,'Папка экспорта',folder.text())
            if p:folder.setText(p)
        browse.clicked.connect(choose);row=QHBoxLayout();row.addWidget(QLabel('Имя:'));name=QLineEdit((self.quick_name or Path(self.file).stem)+('_vectorized' if bitmap else ''));name.setMinimumWidth(0);name.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);row.addWidget(name);fmt=QComboBox();fmt.addItems(['.png'] if bitmap else ['.pdf','.svg','.eps']);row.addWidget(fmt);g.addLayout(row)
        width=height=None
        if bitmap:
            width=QSpinBox();height=QSpinBox()
            for label,spin,value in [('Ширина:',width,self.canvas.image_size.width()),('Высота:',height,self.canvas.image_size.height())]:
                spin.setRange(1,32000);spin.setSuffix(' px');spin.setValue(value);r=QHBoxLayout();r.addWidget(QLabel(label));r.addWidget(spin);g.addLayout(r)
            r=QHBoxLayout();r.addWidget(QLabel('Масштаб:'))
            for n in [1,2,4]:
                b=QPushButton(f'x{n}');b.clicked.connect(lambda checked=False,v=n:(width.setValue(self.canvas.image_size.width()*v),height.setValue(self.canvas.image_size.height()*v)));r.addWidget(b)
            g.addLayout(r)
        b=QPushButton('Сохранить');g.addWidget(b,0,Qt.AlignRight)
        def save():
            if not name.text().strip() or Path(name.text()).name!=name.text():self.error(ValueError('Укажите имя файла без пути.'));return
            target=Path(folder.text())/(name.text()+fmt.currentText())
            if target.exists() and QMessageBox.question(self,'Заменить файл?',str(target))!=QMessageBox.Yes:return
            try:self.write_export(target,QSize(width.value(),height.value()) if bitmap else None);self.quick_dir=folder.text();self.quick_name=name.text() if not bitmap else self.quick_name
            except Exception as exc:self.error(exc)
        b.clicked.connect(save)
    def write_export(self,target,size=None):
        if not self.svg_text or not self.export_button.isEnabled():raise ValueError('Сначала обновите результат.')
        target=Path(target);ext=target.suffix.lower()
        if ext=='.svg':target.write_text(self.svg_text,encoding='utf-8')
        elif ext=='.eps':target.write_text(to_eps(self.svg_text),encoding='ascii')
        elif ext=='.pdf':
            from color_objects import pdf_bytes
            target.write_bytes(pdf_bytes(self.svg_text))
        elif ext=='.png':
            renderer=QSvgRenderer(QByteArray(self.svg_text.encode()))
            size=size or self.canvas.image_size
            if size.width()*size.height()>80_000_000:raise ValueError('Размер PNG превышает 80 миллионов пикселей.')
            im=QImage(size,QImage.Format_ARGB32_Premultiplied);im.fill(Qt.transparent);p=QPainter(im);renderer.render(p,QRectF(0,0,size.width(),size.height()));p.end()
            if not im.save(str(target)):raise OSError('Не удалось сохранить PNG.')
        else:raise ValueError('Неподдерживаемый формат')
        self.statusBar().showMessage(f'Сохранено: {target}')
    def export(self):
        if not self.svg_text or not self.export_button.isEnabled():return
        p,fmt=QFileDialog.getSaveFileName(self,'Сохранение Результата',str(Path(self.file).with_suffix('.pdf')),'PDF (*.pdf);;SVG (*.svg);;EPS (*.eps);;PNG (*.png)')
        if not p:return
        ext={ 'SVG (*.svg)':'.svg','EPS (*.eps)':'.eps','PDF (*.pdf)':'.pdf','PNG (*.png)':'.png'}[fmt];target=Path(p)
        if target.suffix.lower()!=ext:
            target=target.with_suffix(ext)
            if target.exists() and QMessageBox.question(self,'Заменить файл?',str(target))!=QMessageBox.Yes:return
        try:self.write_export(target)
        except Exception as exc:self.error(exc)


def main():
    app=QApplication(sys.argv);app.setStyle('windowsvista');app.setFont(wizard.QFont('Tahoma',9));app.setStyleSheet(wizard.STYLE);window=Window();window.show()
    if len(sys.argv)>1 and Path(sys.argv[1]).is_file():window.load(sys.argv[1])
    sys.exit(app.exec())

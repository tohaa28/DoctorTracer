"""Preview/apply/cancel dialog for an optional finished-vector operation."""
from PySide6.QtCore import Qt,QTimer,QThread,Signal,QByteArray
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QSlider,QCheckBox,QPushButton,QDoubleSpinBox
from vector_render import QSvgRenderer
from post_smooth import smooth
from post_clean import clean
_jobs=set()

class Job(QThread):
    result=Signal(int,object,object)
    def __init__(self,token,svg,strength,sharp,area=None):super().__init__();self.args=(token,svg,strength,sharp,area)
    def run(self):
        token,svg,strength,sharp,area=self.args
        try:self.result.emit(token,(smooth(svg,strength,sharp) if area is None else clean(svg,area,strength/100,sharp)),None)
        except Exception as exc:self.result.emit(token,None,str(exc))

class SmoothDialog(QDialog):
    def __init__(self,owner,cleanup=False):
        super().__init__(owner);self.owner=owner;self.base=owner.svg_text;self.candidate=self.base;self.token=0;self.closed=False;self.cleanup=cleanup
        self.setWindowTitle('Очистка и упрощение результата' if cleanup else 'Сглаживание готового результата');self.setMinimumWidth(440)
        box=QVBoxLayout(self);text=QLabel('Дополнительная обработка готовых векторов.\nОбщие границы цветов изменяются совместно.');text.setWordWrap(True);box.addWidget(text)
        if cleanup:
            box.addWidget(QLabel('Удалять островки площадью до (пкс²):'));self.area=QDoubleSpinBox();self.area.setRange(0,10000);self.area.setDecimals(2);self.area.setValue(4);box.addWidget(self.area)
            note=QLabel('Островки объединяются с окружением. Детали на стыках цветов сохраняются.');note.setWordWrap(True);box.addWidget(note)
        self.value=QLabel();box.addWidget(self.value);self.slider=QSlider(Qt.Horizontal);self.slider.setRange(0,100);self.slider.setValue(25 if cleanup else 35);box.addWidget(self.slider)
        self.sharp=QCheckBox('Защищать углы и тонкие элементы' if cleanup else 'Сохранять острые углы');self.sharp.setChecked(True);box.addWidget(self.sharp)
        self.preview=QCheckBox('Предпросмотр на изображении');self.preview.setChecked(True);box.addWidget(self.preview)
        self.info=QLabel('Подготовка…');self.info.setWordWrap(True);box.addWidget(self.info)
        row=QHBoxLayout();reset=QPushButton('Сброс');row.addWidget(reset);row.addStretch();self.apply=QPushButton('Применить');self.apply.setEnabled(False);row.addWidget(self.apply);cancel=QPushButton('Отмена');row.addWidget(cancel);box.addLayout(row)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(180);self.timer.timeout.connect(self.calculate)
        self.slider.valueChanged.connect(self.schedule);self.sharp.toggled.connect(self.schedule);self.preview.toggled.connect(self.show_preview)
        reset.clicked.connect(self.reset_values);cancel.clicked.connect(self.reject);self.apply.clicked.connect(self.accept)
        if cleanup:self.area.valueChanged.connect(self.schedule)
        self.schedule()
    def reset_values(self):
        self.slider.setValue(0)
        if self.cleanup:self.area.setValue(0)
    def paint(self,value):
        self.owner.svg_text=value;self.owner.canvas.svg=QSvgRenderer(QByteArray(value.encode('utf8')));self.owner.set_contours();self.owner.canvas.update()
    def schedule(self,*args):
        self.token+=1;self.value.setText(f'Допуск упрощения: {self.slider.value()/100:.2f} пкс' if self.cleanup else f'Сила сглаживания: {self.slider.value()}%');self.apply.setEnabled(False);self.info.setText('Расчёт предпросмотра…');self.timer.start()
    def calculate(self):
        job=Job(self.token,self.base,self.slider.value(),self.sharp.isChecked(),self.area.value() if self.cleanup else None);_jobs.add(job);job.result.connect(self.delivered);job.finished.connect(lambda:(_jobs.discard(job),job.deleteLater()));job.start()
    def delivered(self,token,result,error):
        if self.closed or token!=self.token:return
        if error:self.info.setText('Не удалось обработать результат: '+error);return
        self.candidate,stats=result;changed=self.candidate!=self.base;self.apply.setEnabled(changed)
        self.info.setText(('Предпросмотр готов. '+('Сила уменьшена для защиты геометрии.' if stats.get('limited') else 'Границы и мелкие детали защищены.')) if changed else 'Результат не изменён. Попробуйте другую силу или отключите сохранение углов.')
        if self.cleanup:self.info.setText(f"Удалено островков: {stats['removed_elements']}; защищено: {stats['protected_elements']}. Узлов: {stats['nodes_before']} → {stats['nodes_after']}."+(' Допуск уменьшен для защиты геометрии.' if stats.get('limited') else ''))
        self.show_preview()
    def show_preview(self,*args):self.paint(self.candidate if self.preview.isChecked() else self.base)
    def done(self,code):
        self.closed=True;self.timer.stop()
        value=self.candidate if code==QDialog.Accepted else self.base
        if code==QDialog.Accepted and value!=self.base:
            history=getattr(self.owner,'post_smooth_undo',[]);history.append(self.base);self.owner.post_smooth_undo=history[-20:]
            self.owner.background_original=value;self.owner.removed_shapes=set();self.owner.background_undo=[];self.owner.background_redo=[]
        self.paint(value);super().done(code)

def open_smoother(owner):
    if owner.svg_text:SmoothDialog(owner).exec()

def open_cleaner(owner):
    if owner.svg_text:SmoothDialog(owner,cleanup=True).exec()

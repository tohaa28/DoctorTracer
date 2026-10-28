"""Preview/apply/cancel dialog for an optional finished-vector operation."""
from PySide6.QtCore import Qt,QTimer,QThread,Signal,QByteArray
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QSlider,QCheckBox,QPushButton
from vector_render import QSvgRenderer
from post_smooth import smooth
_jobs=set()

class Job(QThread):
    result=Signal(int,object,object)
    def __init__(self,token,svg,strength,sharp):super().__init__();self.args=(token,svg,strength,sharp)
    def run(self):
        token,svg,strength,sharp=self.args
        try:self.result.emit(token,smooth(svg,strength,sharp),None)
        except Exception as exc:self.result.emit(token,None,str(exc))

class SmoothDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.base=owner.svg_text;self.candidate=self.base;self.token=0;self.closed=False
        self.setWindowTitle('Сглаживание готового результата');self.setMinimumWidth(440)
        box=QVBoxLayout(self);text=QLabel('Дополнительная обработка готовых векторов.\nОбщие границы цветов изменяются совместно.');text.setWordWrap(True);box.addWidget(text)
        self.value=QLabel();box.addWidget(self.value);self.slider=QSlider(Qt.Horizontal);self.slider.setRange(0,100);self.slider.setValue(35);box.addWidget(self.slider)
        self.sharp=QCheckBox('Сохранять острые углы');self.sharp.setChecked(True);box.addWidget(self.sharp)
        self.preview=QCheckBox('Предпросмотр на изображении');self.preview.setChecked(True);box.addWidget(self.preview)
        self.info=QLabel('Подготовка…');self.info.setWordWrap(True);box.addWidget(self.info)
        row=QHBoxLayout();reset=QPushButton('Сброс');row.addWidget(reset);row.addStretch();self.apply=QPushButton('Применить');self.apply.setEnabled(False);row.addWidget(self.apply);cancel=QPushButton('Отмена');row.addWidget(cancel);box.addLayout(row)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(180);self.timer.timeout.connect(self.calculate)
        self.slider.valueChanged.connect(self.schedule);self.sharp.toggled.connect(self.schedule);self.preview.toggled.connect(self.show_preview)
        reset.clicked.connect(lambda:self.slider.setValue(0));cancel.clicked.connect(self.reject);self.apply.clicked.connect(self.accept)
        self.schedule()
    def paint(self,value):
        self.owner.svg_text=value;self.owner.canvas.svg=QSvgRenderer(QByteArray(value.encode('utf8')));self.owner.set_contours();self.owner.canvas.update()
    def schedule(self,*args):
        self.token+=1;self.value.setText(f'Сила сглаживания: {self.slider.value()}%');self.apply.setEnabled(False);self.info.setText('Расчёт предпросмотра…');self.timer.start()
    def calculate(self):
        job=Job(self.token,self.base,self.slider.value(),self.sharp.isChecked());_jobs.add(job);job.result.connect(self.delivered);job.finished.connect(lambda:(_jobs.discard(job),job.deleteLater()));job.start()
    def delivered(self,token,result,error):
        if self.closed or token!=self.token:return
        if error:self.info.setText('Не удалось сгладить результат: '+error);return
        self.candidate,stats=result;changed=self.candidate!=self.base;self.apply.setEnabled(changed)
        self.info.setText(('Предпросмотр готов. '+('Сила уменьшена для защиты геометрии.' if stats.get('limited') else 'Границы и мелкие детали защищены.')) if changed else 'Результат не изменён. Попробуйте другую силу или отключите сохранение углов.')
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

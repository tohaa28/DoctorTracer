
from PySide6.QtCore import Qt,QThread,Signal,QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QSlider,QCheckBox,QPushButton
from post_smooth_dialog import SmoothDialog,_jobs
from color_node_tools import intermediate,reduce_nodes
class Job(QThread):
    result=Signal(int,object,object)
    def __init__(self,token,svg,power,color):super().__init__();self.args=(token,svg,power,color)
    def run(self):
        token,svg,power,color=self.args
        try:self.result.emit(token,(intermediate if color else reduce_nodes)(svg,power),None)
        except Exception as exc:self.result.emit(token,None,str(exc))
class Dialog(SmoothDialog):
    def __init__(self,owner,color):
        QDialog.__init__(self,owner);self.owner=owner;self.base=owner.svg_text;self.candidate=self.base;self.token=0;self.closed=False;self.color=color
        self.setWindowTitle('Очистка промежуточных цветов' if color else 'Сокращение узлов кривых');self.setMinimumWidth(460)
        box=QVBoxLayout(self);label=QLabel('Мелкие области цвета-смеси делятся общей границей двух соседей. Неоднозначные и криволинейные области сохраняются.' if color else 'Аппроксимация общих кривых, защита углов. 100% = допуск 2 пикселя, не процент удалённых узлов.');label.setWordWrap(True);box.addWidget(label)
        self.value=QLabel();box.addWidget(self.value);self.slider=QSlider(Qt.Horizontal);self.slider.setRange(0,100);self.slider.setValue(35);box.addWidget(self.slider)
        self.preview=QCheckBox('Предпросмотр на изображении');self.preview.setChecked(True);box.addWidget(self.preview)
        self.info=QLabel();self.info.setWordWrap(True);box.addWidget(self.info)
        row=QHBoxLayout();reset=QPushButton('Сброс');row.addWidget(reset);row.addStretch();self.apply=QPushButton('Применить');self.apply.setEnabled(False);row.addWidget(self.apply);cancel=QPushButton('Отмена');row.addWidget(cancel);box.addLayout(row)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(180);self.timer.timeout.connect(self.calculate)
        self.slider.valueChanged.connect(self.schedule);self.preview.toggled.connect(self.show_preview);reset.clicked.connect(lambda:self.slider.setValue(0));cancel.clicked.connect(self.reject);self.apply.clicked.connect(self.accept);self.schedule()
    def schedule(self,*args):
        self.token+=1;self.value.setText(f'Интенсивность: {self.slider.value()}%');self.apply.setEnabled(False);self.info.setText('Расчёт предпросмотра…');self.timer.start()
    def calculate(self):
        job=Job(self.token,self.base,self.slider.value(),self.color);_jobs.add(job);job.result.connect(self.delivered);job.finished.connect(lambda:(_jobs.discard(job),job.deleteLater()));job.start()
    def delivered(self,token,result,error):
        if self.closed or token!=self.token:return
        if error:self.info.setText('Не удалось обработать: '+error);return
        self.candidate,s=result;self.apply.setEnabled(self.candidate!=self.base)
        self.info.setText(f"Удалено промежуточных областей: {s['removed_elements']}; неоднозначных: {s['protected_elements']}." if self.color else f"Сегментов: {s['nodes_before']} → {s['nodes_after']}; сокращение {s['reduction']:.1f}%. Допуск: {s.get('applied_tolerance',0):.2f} пкс.")
        self.show_preview()
def open_tools(owner,color):
    if owner.svg_text:Dialog(owner,color).exec()

"""Preview UI for the optional shared-chain regularization module."""
from PySide6.QtCore import Qt,QTimer,QThread,Signal
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QDoubleSpinBox,QCheckBox,QPushButton
from post_smooth_dialog import SmoothDialog,_jobs
from regularize import regularize
class Job(QThread):
    result=Signal(int,object,object)
    def __init__(self,token,svg,args):super().__init__();self.token=token;self.svg=svg;self.args=args
    def run(self):
        try:self.result.emit(self.token,regularize(self.svg,**self.args),None)
        except Exception as exc:self.result.emit(self.token,None,str(exc))
class RegularizeDialog(SmoothDialog):
    def __init__(self,owner):
        QDialog.__init__(self,owner);self.owner=owner;self.base=owner.svg_text;self.candidate=self.base;self.token=0;self.closed=False
        self.setWindowTitle('Выравнивание контуров');self.setMinimumWidth(460);box=QVBoxLayout(self)
        label=QLabel('Длинные участки подгоняются целиком.\nОбщие границы цветов изменяются совместно.');label.setWordWrap(True);box.addWidget(label)
        box.addWidget(QLabel('Допуск изменения формы (пкс исходника):'));self.tolerance=QDoubleSpinBox();self.tolerance.setRange(0,2);self.tolerance.setDecimals(2);self.tolerance.setSingleStep(.05);self.tolerance.setValue(.15);box.addWidget(self.tolerance)
        self.straight=QCheckBox('Выпрямлять почти прямые участки');self.straight.setChecked(True);box.addWidget(self.straight)
        self.curved=QCheckBox('Выравнивать плавные кривые');self.curved.setChecked(True);box.addWidget(self.curved)
        self.sharp=QCheckBox('Сохранять углы и мелкие детали');self.sharp.setChecked(True);box.addWidget(self.sharp)
        self.preview=QCheckBox('Предпросмотр на изображении');self.preview.setChecked(True);box.addWidget(self.preview)
        self.info=QLabel('Подготовка…');self.info.setWordWrap(True);box.addWidget(self.info)
        row=QHBoxLayout();reset=QPushButton('Сброс');row.addWidget(reset);row.addStretch();self.apply=QPushButton('Применить');self.apply.setEnabled(False);row.addWidget(self.apply);cancel=QPushButton('Отмена');row.addWidget(cancel);box.addLayout(row)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(180);self.timer.timeout.connect(self.calculate)
        self.tolerance.valueChanged.connect(self.schedule)
        for c in [self.straight,self.curved,self.sharp]:c.toggled.connect(self.schedule)
        self.preview.toggled.connect(self.show_preview);reset.clicked.connect(lambda:self.tolerance.setValue(0));cancel.clicked.connect(self.reject);self.apply.clicked.connect(self.accept);self.schedule()
    def schedule(self,*args):self.token+=1;self.apply.setEnabled(False);self.info.setText('Расчёт предпросмотра…');self.timer.start()
    def calculate(self):
        args={'tolerance':self.tolerance.value(),'straight':self.straight.isChecked(),'curved':self.curved.isChecked(),'protect':self.sharp.isChecked()};job=Job(self.token,self.base,args);_jobs.add(job);job.result.connect(self.delivered);job.finished.connect(lambda:(_jobs.discard(job),job.deleteLater()));job.start()
    def delivered(self,token,result,error):
        if self.closed or token!=self.token:return
        if error:self.info.setText('Не удалось обработать: '+error);return
        self.candidate,stats=result;self.apply.setEnabled(self.candidate!=self.base)
        self.info.setText(f"Прямых участков: {stats['straightened']}; подогнано дуг: {stats['curves_fitted']}. Узлов: {stats['nodes_before']} → {stats['nodes_after']}."+(' Допуск уменьшен для защиты геометрии.'if stats.get('limited')else''));self.show_preview()
def open_regularizer(owner):
    if owner.svg_text:RegularizeDialog(owner).exec()

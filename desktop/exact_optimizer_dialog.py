"""Exact optimization preview; shares the established undo and cancellation contract."""
from PySide6.QtCore import QThread,Signal,QTimer
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QCheckBox,QPushButton
from post_smooth_dialog import SmoothDialog,_jobs
from exact_optimizer import checked_optimize
class Job(QThread):
    result=Signal(int,object,object)
    def __init__(self,svg):super().__init__();self.svg=svg
    def run(self):
        try:self.result.emit(1,checked_optimize(self.svg),None)
        except Exception as exc:self.result.emit(1,None,str(exc))
class ExactDialog(SmoothDialog):
    def __init__(self,owner):
        QDialog.__init__(self,owner);self.owner=owner;self.base=owner.svg_text;self.candidate=self.base;self.closed=False;self.token=1
        self.setWindowTitle('Точная оптимизация узлов');self.setMinimumWidth(460)
        box=QVBoxLayout(self)
        note=QLabel('Удаляются совпадающие узлы, строго прямые промежуточные узлы и точно восстанавливаемые половины кривых Безье. Форма не меняется.');note.setWordWrap(True);box.addWidget(note)
        self.preview=QCheckBox('Предпросмотр после оптимизации');self.preview.setChecked(True);box.addWidget(self.preview)
        self.info=QLabel('Расчёт и проверка геометрии…');self.info.setWordWrap(True);box.addWidget(self.info)
        row=QHBoxLayout();row.addStretch();self.apply=QPushButton('Применить');self.apply.setEnabled(False);row.addWidget(self.apply);cancel=QPushButton('Отмена');row.addWidget(cancel);box.addLayout(row)
        self.timer=QTimer(self);self.preview.toggled.connect(self.show_preview);self.apply.clicked.connect(self.accept);cancel.clicked.connect(self.reject)
        job=Job(self.base);_jobs.add(job);job.result.connect(self.delivered);job.finished.connect(lambda:(_jobs.discard(job),job.deleteLater()));job.start()
    def delivered(self,token,result,error):
        if self.closed or token!=self.token:return
        if error:self.info.setText('Результат не изменён: '+error);return
        self.candidate,stats=result;self.apply.setEnabled(self.candidate!=self.base)
        self.info.setText(f"Сегментов: {stats['before']} → {stats['after']}. Совпадающих: {stats['zero']}; прямых: {stats['straight']}; объединено половин Безье: {stats['cubic']}; пропущено путей: {stats['skipped']}.")
        self.show_preview()
def open_exact_optimizer(owner):
    if owner.svg_text:ExactDialog(owner).exec()

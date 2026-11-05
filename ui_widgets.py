from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget


STYLE = """
* { font-family: 'Segoe UI'; font-size: 13px; color: #242638; }
QWidget { background: transparent; }
QFrame#shell { background: #f7f8fb; border: 1px solid #e1e3ec; border-radius: 22px; }
QFrame#sidebar { background: #f0f1f7; border-radius: 16px; }
QFrame#card { background: white; border: 1px solid #e5e7ef; border-radius: 18px; }
QLabel { border: none; }
QLabel#title { font-size: 28px; font-weight: 650; }
QLabel#subtitle { font-size: 18px; font-weight: 600; }
QLabel#muted { color: #7a8095; }
QLabel#eyebrow { color: #969bb0; font-size: 11px; font-weight: 650; }
QLabel#notice { color: #6353b9; background: #eeebfb; border-radius: 10px; padding: 10px; }
QPushButton { background: #f1f2f7; border: 1px solid transparent; border-radius: 10px;
              padding: 10px 14px; font-weight: 550; }
QPushButton:hover { background: #e9e8f5; }
QPushButton:pressed { background: #ddd9f5; }
QPushButton:focus { border: 1px solid #9c8ce0; }
QPushButton:disabled { color: #a8acba; background: #f0f1f5; }
QPushButton#primary { background: #7660d5; color: white; }
QPushButton#primary:hover { background: #6650c2; }
QPushButton#primary:disabled { background: #cbc5e3; color: #f9f9ff; }
QPushButton#nav { text-align: left; padding: 13px 16px; background: transparent; color: #797f95; }
QPushButton#nav:checked { background: white; color: #6552bd; }
QPushButton#segment:checked { background: #eeeafb; color: #7056c9; border-color: #c9beed; }
QPushButton#danger { color: #c05a67; background: #fcf1f3; }
QPushButton#chip { background: #efedf9; color: #6251a6; padding: 6px 10px; }
QLineEdit, QComboBox { background: #f7f8fb; border: 1px solid #e1e4ee; border-radius: 10px;
                        padding: 10px 12px; min-height: 18px; selection-background-color: #d8d0f5; }
QLineEdit:focus, QComboBox:focus { border-color: #a290e3; }
QComboBox::drop-down { border: none; width: 25px; }
QComboBox::down-arrow { image: url(__ARROW__); width: 12px; height: 8px; }
QComboBox QAbstractItemView { background: white; color: #292b40; border: 1px solid #e3e5ee;
                             selection-background-color: #eeeafb; selection-color: #6652b5; }
QScrollArea { border: none; }
QScrollBar:vertical { background: transparent; width: 7px; margin: 3px; }
QScrollBar::handle:vertical { background: #d6d8e4; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; border-radius: 5px; border: 1px solid #cbc6df; background: white; }
QCheckBox::indicator:checked { background: #8b76db; border-color: #8b76db; }
QToolTip { background: #292d40; color: white; border: none; padding: 7px; }
""".replace('__ARROW__', Path(__file__).with_name('chevron.svg').as_posix())


def label(text, role=None, wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if role:
        widget.setObjectName(role)
    widget.setWordWrap(wrap)
    return widget


def button(text, callback=None, role=None):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if role:
        widget.setObjectName(role)
    if callback:
        widget.clicked.connect(callback)
    return widget


def card():
    widget = QFrame()
    widget.setObjectName('card')
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)
    return widget, layout


class TitleBar(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            window.showNormal() if window.isMaximized() else window.showMaximized()


class CameraPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.image = QImage()
        self.setMinimumSize(300, 225)
        self.setAccessibleName('Live camera preview')

    def sizeHint(self):
        return QSize(640, 430)

    def set_frame(self, rgb):
        height, width, _ = rgb.shape

        self.image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
        self.update()

    def clear(self):
        self.image = QImage()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(bounds, 16, 16)
        painter.setClipPath(clip)
        painter.fillRect(bounds, QColor('#edf0f6'))
        if not self.image.isNull():
            size = self.image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            target = QRectF((self.width() - size.width()) / 2, (self.height() - size.height()) / 2,
                            size.width(), size.height())
            painter.drawImage(target, self.image)
            return
        center = bounds.center()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#e3e0f2'))
        painter.drawEllipse(center.x() - 42, center.y() - 83, 84, 84)
        painter.setPen(QPen(QColor('#8c7bc5'), 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(center.x() - 22, center.y() - 56, 44, 29), 7, 7)
        painter.drawEllipse(center.x() - 8, center.y() - 50, 16, 16)
        painter.setFont(QFont('Segoe UI', 16, QFont.Weight.DemiBold))
        painter.setPen(QColor('#515775'))
        painter.drawText(QRectF(12, center.y() + 15, self.width() - 24, 35), Qt.AlignmentFlag.AlignCenter,
                         'Your next move starts here')
        painter.setFont(QFont('Segoe UI', 10))
        painter.setPen(QColor('#9299ae'))
        painter.drawText(QRectF(12, center.y() + 55, self.width() - 24, 30), Qt.AlignmentFlag.AlignCenter,
                         'Turn on the camera to see your hands.')

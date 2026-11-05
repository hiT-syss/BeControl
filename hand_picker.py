from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget


FINGER_NAMES = ("Index", "Middle", "Ring", "Pinky")


class _HandCanvas(QWidget):
    fingerClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mask = 0
        self.accent = QColor("#e56b72")
        self.setMinimumSize(230, 225)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click the fingers you want to hold open.")
        self.setAccessibleName("Hand gesture preview")

    def drawing_transform(self):
        scale = min(self.width() / 340, self.height() / 290)
        return scale, (self.width() - 340 * scale) / 2, (self.height() - 290 * scale) / 2

    def finger_rect(self, index):
        top = (51, 25, 42, 76)[index]
        return QRectF(88 + index * 40, top, 34, 167 - top)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale, offset_x, offset_y = self.drawing_transform()
        painter.translate(offset_x, offset_y)
        painter.scale(scale, scale)

        
        halo = QColor(self.accent)
        halo.setAlpha(12)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(QRectF(59, 28, 230, 230))

        palm = QPainterPath(QPointF(88, 133))
        palm.cubicTo(91, 124, 104, 123, 116, 124)
        palm.lineTo(224, 124)
        palm.cubicTo(241, 124, 246, 138, 245, 156)
        palm.lineTo(243, 185)
        palm.cubicTo(242, 207, 222, 225, 216, 236)
        palm.lineTo(216, 257)
        palm.quadTo(216, 265, 208, 265)
        palm.lineTo(137, 265)
        palm.quadTo(129, 265, 129, 257)
        palm.lineTo(129, 237)
        palm.cubicTo(113, 227, 96, 213, 86, 194)
        palm.lineTo(58, 147)
        palm.cubicTo(50, 131, 66, 118, 77, 130)
        palm.lineTo(88, 144)
        palm.closeSubpath()

        painter.setBrush(QColor("#eef0f4"))
        painter.setPen(QPen(QColor("#d7dce5"), 1.5))
        painter.drawPath(palm)

        for index in range(4):
            rect = self.finger_rect(index)
            selected = bool(self.mask & (1 << index))
            if selected:
                fill = QColor(self.accent)
                fill.setAlpha(42)
                painter.setBrush(fill)
                painter.setPen(QPen(self.accent, 1.7))
                painter.drawRoundedRect(rect, 17, 17)
                painter.setBrush(self.accent)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(rect.center().x(), rect.top() + 20), 4, 4)
                painter.setPen(QPen(self.accent, 1.2))
                painter.drawLine(QPointF(rect.left() + 10, 118), QPointF(rect.right() - 10, 118))
            else:
                
                painter.setBrush(Qt.BrushStyle.NoBrush)
                guide = QColor("#d7dce5")
                guide.setAlpha(130)
                painter.setPen(QPen(guide, 1, Qt.PenStyle.DashLine))
                painter.drawRoundedRect(rect, 17, 17)
                folded = QRectF(rect.left(), 126, rect.width(), 49)
                painter.setBrush(QColor("#e4e7ed"))
                painter.setPen(QPen(QColor("#c8cfda"), 1.2))
                painter.drawRoundedRect(folded, 15, 15)
                painter.drawLine(QPointF(rect.left() + 9, 150), QPointF(rect.right() - 9, 150))

        painter.setPen(QPen(QColor("#cdd3de"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        crease = QPainterPath(QPointF(114, 190))
        crease.cubicTo(135, 174, 183, 182, 218, 192)
        painter.drawPath(crease)
        painter.drawLine(QPointF(145, 243), QPointF(201, 243))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scale, offset_x, offset_y = self.drawing_transform()
            position = QPointF((event.position().x() - offset_x) / scale,
                               (event.position().y() - offset_y) / scale)
            for index in range(4):
                if self.finger_rect(index).adjusted(-3, -5, 3, 10).contains(position):
                    self.fingerClicked.emit(index)
                    event.accept()
                    return
        super().mousePressEvent(event)


class HandPicker(QWidget):


    maskChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mask = 0
        self._side = "Red"
        self.setAccessibleName("Hand gesture selection")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.canvas = _HandCanvas(self)
        self.canvas.fingerClicked.connect(self._toggle_finger)
        layout.addWidget(self.canvas, 1)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.buttons = []
        for index, name in enumerate(FINGER_NAMES):
            button = QPushButton(name)
            button.setObjectName("fingerToggle")
            button.setCheckable(True)
            button.setMinimumHeight(35)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAccessibleName(f"Open or close the {name} finger")
            button.setToolTip(f"Toggle the {name} finger")
            button.clicked.connect(lambda _checked=False, bit=index: self._toggle_finger(bit))
            row.addWidget(button, 1)
            self.buttons.append(button)
        layout.addLayout(row)
        hint = QLabel("Highlighted fingers are open; the others are closed.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #858d9e; font-size: 11px; background: transparent;")
        layout.addWidget(hint)
        self.setSide(self._side)

    @property
    def mask(self):
        return self._mask

    def setMask(self, mask):
        if not isinstance(mask, int) or not 0 <= mask <= 15:
            raise ValueError("The gesture must be an integer from 0 to 15.")
        changed = self._mask != mask
        self._mask = mask
        self.canvas.mask = mask
        self.canvas.update()
        for index, button in enumerate(self.buttons):
            button.setChecked(bool(mask & (1 << index)))
        if changed:
            self.maskChanged.emit(mask)

    def setSide(self, side):
        if side not in ("Red", "Green"):
            raise ValueError("The hand color must be Red or Green.")
        self._side = side
        accent, tint = ("#d75b68", "#fcecef") if side == "Red" else ("#239777", "#e5f6ef")
        self.canvas.accent = QColor(accent)
        self.canvas.update()
        self.setStyleSheet(f"""
            QPushButton#fingerToggle {{
                color: #747d90; background: #f2f4f7; border: 1px solid transparent;
                border-radius: 10px; padding: 5px 2px; font-size: 12px;
            }}
            QPushButton#fingerToggle:hover {{ background: #e8ecf2; }}
            QPushButton#fingerToggle:checked {{
                color: {accent}; background: {tint}; border: 1px solid {accent};
            }}
            QPushButton#fingerToggle:focus {{ border: 2px solid {accent}; }}
        """)

    def _toggle_finger(self, index):
        self.setMask(self._mask ^ (1 << index))

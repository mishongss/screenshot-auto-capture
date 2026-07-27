from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtWidgets import QWidget, QApplication

class RegionSelector(QWidget):
    """
    화면 전체에 반투명 오버레이를 표시하고, 마우스 드래그로 캡처 영역(ROI)을 선택하는 창.
    """
    region_selected = pyqtSignal(int, int, int, int)  # x, y, width, height

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.begin = None
        self.end = None
        self.is_selecting = False

    def start_selection(self):
        """다중 모니터(듀얼 모니터)를 포함한 전체 가상 화면 좌표 영역 설정 후 오버레이 표시"""
        from PyQt6.QtGui import QGuiApplication
        
        # 주 모니터 및 확장(오른쪽/왼쪽) 모니터를 모두 포함하는 가상 화면 영역
        vgeo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(vgeo)
        self.vgeo = vgeo
        
        self.begin = None
        self.end = None
        self.is_selecting = False
        self.show()
        self.activateWindow()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin = event.pos()
            self.end = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.end = event.pos()
            self.is_selecting = False
            rect = QRect(self.begin, self.end).normalized()
            
            self.hide()
            if rect.width() > 10 and rect.height() > 10:
                # 다중 모니터 전역 가상 좌표계 변환 (오른쪽/왼쪽 모니터 정확 반영)
                global_x = self.vgeo.x() + rect.x()
                global_y = self.vgeo.y() + rect.y()
                
                self.region_selected.emit(
                    global_x,
                    global_y,
                    rect.width(),
                    rect.height()
                )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 어두운 반투명 전체 배경 (모든 모니터 영역)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        if self.begin and self.end:
            rect = QRect(self.begin, self.end).normalized()
            
            # 선택 영역 내부 투명 클리어 (선명하게 보이도록)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # 테두리 강조선 (Cyan/Blue Neon style)
            pen = QPen(QColor(0, 210, 255), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # 사이즈 안내 텍스트 표시
            info_text = f" {rect.width()} x {rect.height()} px "
            painter.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
            
            # 텍스트 배경 박스
            text_rect = QRect(rect.x(), rect.y() - 28 if rect.y() >= 30 else rect.y() + 5, 130, 24)
            painter.fillRect(text_rect, QColor(20, 30, 45, 220))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, info_text)

        # 상단 도움말 안내
        if not self.is_selecting:
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Malgun Gothic", 14, QFont.Weight.Bold))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                "\n\n🖥️ [다중 모니터 지원] 캡처할 영역을 마우스로 드래그하여 지정하세요. (취소: ESC)"
            )

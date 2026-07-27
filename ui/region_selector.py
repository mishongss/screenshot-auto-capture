from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QCursor
from PyQt6.QtWidgets import QWidget, QApplication

class RegionSelector(QWidget):
    """
    화면 전체 반투명 오버레이 ROI 선택기.
    - 드래그로 사각형 생성
    - 사각형 생성 후 8개 조절 핸들(Resizing Handles)로 크기 조절 가능
    - 사각형 내부 마우스 드래그로 위치 이동(Moving) 가능
    - [Enter] 키 또는 더블클릭으로 캡처 영역 확정
    - [ESC] 키로 취소
    """
    region_selected = pyqtSignal(int, int, int, int)  # x, y, width, height
    selection_canceled = pyqtSignal()  # 취소 시그널

    # 핸들 크기 및 위치 정의
    HANDLE_SIZE = 8

    # 상태 정의
    STATE_IDLE = 0
    STATE_CREATING = 1
    STATE_SELECTED = 2
    STATE_RESIZING = 3
    STATE_MOVING = 4

    # 핸들 종류 정의
    HANDLE_NONE = 0
    HANDLE_TOP_LEFT = 1
    HANDLE_TOP = 2
    HANDLE_TOP_RIGHT = 3
    HANDLE_RIGHT = 4
    HANDLE_BOTTOM_RIGHT = 5
    HANDLE_BOTTOM = 6
    HANDLE_BOTTOM_LEFT = 7
    HANDLE_LEFT = 8

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.state = self.STATE_IDLE
        self.selection_rect = QRect()
        self.drag_start = QPoint()
        self.active_handle = self.HANDLE_NONE
        self.initial_rect = QRect()
        self.vgeo = QRect()

    def start_selection(self):
        """다중 모니터를 포함한 전체 가상 화면 좌표 영역 설정 후 오버레이 표시"""
        from PyQt6.QtGui import QGuiApplication
        self.vgeo = QGuiApplication.primaryScreen().virtualGeometry()
        self.setGeometry(self.vgeo)
        
        self.state = self.STATE_IDLE
        self.selection_rect = QRect()
        self.active_handle = self.HANDLE_NONE
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()
        self.activateWindow()

    def _get_handles(self, rect: QRect):
        """8개 리사이즈 핸들의 QRect 구하기"""
        s = self.HANDLE_SIZE
        hs = s // 2
        
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()

        return {
            self.HANDLE_TOP_LEFT: QRect(x - hs, y - hs, s, s),
            self.HANDLE_TOP: QRect(x + w // 2 - hs, y - hs, s, s),
            self.HANDLE_TOP_RIGHT: QRect(x + w - hs, y - hs, s, s),
            self.HANDLE_RIGHT: QRect(x + w - hs, y + h // 2 - hs, s, s),
            self.HANDLE_BOTTOM_RIGHT: QRect(x + w - hs, y + h - hs, s, s),
            self.HANDLE_BOTTOM: QRect(x + w // 2 - hs, y + h - hs, s, s),
            self.HANDLE_BOTTOM_LEFT: QRect(x - hs, y + h - hs, s, s),
            self.HANDLE_LEFT: QRect(x - hs, y + h // 2 - hs, s, s)
        }

    def _hit_test(self, pos: QPoint):
        """마우스 위치가 핸들에 닿았는지 판별"""
        if not self.selection_rect.isValid() or self.selection_rect.isEmpty():
            return self.HANDLE_NONE

        handles = self._get_handles(self.selection_rect)
        for handle_id, handle_rect in handles.items():
            if handle_rect.contains(pos):
                return handle_id
        return self.HANDLE_NONE

    def _update_cursor(self, pos: QPoint):
        """마우스 포인터 위치에 따른 커서 형태 변경"""
        if self.state == self.STATE_CREATING:
            self.setCursor(Qt.CursorShape.CrossCursor)
            return

        handle = self._hit_test(pos)
        if handle in (self.HANDLE_TOP_LEFT, self.HANDLE_BOTTOM_RIGHT):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in (self.HANDLE_TOP_RIGHT, self.HANDLE_BOTTOM_LEFT):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle in (self.HANDLE_TOP, self.HANDLE_BOTTOM):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif handle in (self.HANDLE_LEFT, self.HANDLE_RIGHT):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif self.selection_rect.contains(pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            
            if self.state in (self.STATE_IDLE, self.STATE_SELECTED):
                handle = self._hit_test(pos)
                if handle != self.HANDLE_NONE:
                    self.active_handle = handle
                    self.state = self.STATE_RESIZING
                    self.drag_start = pos
                    self.initial_rect = QRect(self.selection_rect)
                elif self.selection_rect.contains(pos):
                    self.state = self.STATE_MOVING
                    self.drag_start = pos
                    self.initial_rect = QRect(self.selection_rect)
                else:
                    self.state = self.STATE_CREATING
                    self.drag_start = pos
                    self.selection_rect = QRect(pos, pos)
            self.update()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        self._update_cursor(pos)

        if event.buttons() & Qt.MouseButton.LeftButton:
            if self.state == self.STATE_CREATING:
                self.selection_rect = QRect(self.drag_start, pos).normalized()
            
            elif self.state == self.STATE_MOVING:
                delta = pos - self.drag_start
                new_rect = QRect(
                    self.initial_rect.x() + delta.x(),
                    self.initial_rect.y() + delta.y(),
                    self.initial_rect.width(),
                    self.initial_rect.height()
                )
                self.selection_rect = new_rect

            elif self.state == self.STATE_RESIZING:
                rect = QRect(self.initial_rect)
                dx = pos.x() - self.drag_start.x()
                dy = pos.y() - self.drag_start.y()

                if self.active_handle == self.HANDLE_TOP_LEFT:
                    rect.setTopLeft(rect.topLeft() + QPoint(dx, dy))
                elif self.active_handle == self.HANDLE_TOP:
                    rect.setTop(rect.top() + dy)
                elif self.active_handle == self.HANDLE_TOP_RIGHT:
                    rect.setTopRight(rect.topRight() + QPoint(dx, dy))
                elif self.active_handle == self.HANDLE_RIGHT:
                    rect.setRight(rect.right() + dx)
                elif self.active_handle == self.HANDLE_BOTTOM_RIGHT:
                    rect.setBottomRight(rect.bottomRight() + QPoint(dx, dy))
                elif self.active_handle == self.HANDLE_BOTTOM:
                    rect.setBottom(rect.bottom() + dy)
                elif self.active_handle == self.HANDLE_BOTTOM_LEFT:
                    rect.setBottomLeft(rect.bottomLeft() + QPoint(dx, dy))
                elif self.active_handle == self.HANDLE_LEFT:
                    rect.setLeft(rect.left() + dx)

                self.selection_rect = rect.normalized()

            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.state in (self.STATE_CREATING, self.STATE_RESIZING, self.STATE_MOVING):
                self.state = self.STATE_SELECTED
                self.active_handle = self.HANDLE_NONE
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.selection_rect.contains(event.pos()):
                self._confirm_selection()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._confirm_selection()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.selection_canceled.emit()

    def _get_confirm_button_rect(self, rect: QRect):
        """[선택 완료] 버튼의 QRect 위치 구하기"""
        btn_w, btn_h = 140, 32
        x = rect.x() + (rect.width() - btn_w) // 2
        y = rect.y() + rect.height() + 10
        # 화면 아래로 벗어나는 경우 사각형 위쪽에 배치
        if y + btn_h > self.height() - 10:
            y = rect.y() - btn_h - 10
        return QRect(x, y, btn_w, btn_h)

    def _confirm_selection(self):
        """선택 확정 처리 후 시그널 발신"""
        if self.selection_rect.isValid() and self.selection_rect.width() > 10 and self.selection_rect.height() > 10:
            global_x = self.vgeo.x() + self.selection_rect.x()
            global_y = self.vgeo.y() + self.selection_rect.y()
            
            self.hide()
            self.region_selected.emit(
                global_x,
                global_y,
                self.selection_rect.width(),
                self.selection_rect.height()
            )
        else:
            self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 어두운 반투명 전체 배경
        painter.fillRect(self.rect(), QColor(0, 0, 0, 110))

        if self.selection_rect.isValid() and not self.selection_rect.isEmpty():
            rect = self.selection_rect

            # 선택 영역 내부 투명 클리어
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # 테두리 선 (Neon Cyan)
            pen = QPen(QColor(0, 210, 255), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            # 8개 크기 조절 핸들 그리기
            handles = self._get_handles(rect)
            painter.setBrush(QColor(255, 255, 255))
            painter.setPen(QPen(QColor(0, 150, 255), 1.5))
            for h_rect in handles.values():
                painter.drawRect(h_rect)

            # 크기 및 위치 안내 텍스트 표시
            info_text = f" {rect.width()} x {rect.height()} px "
            painter.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
            
            text_rect = QRect(rect.x(), rect.y() - 28 if rect.y() >= 30 else rect.y() + 5, 140, 24)
            painter.fillRect(text_rect, QColor(20, 30, 45, 220))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, info_text)

            # [ ✅ 영역 선택 완료 ] 플로팅 버튼 렌더링
            btn_rect = self._get_confirm_button_rect(rect)
            painter.setBrush(QColor(0, 180, 120))
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.drawRoundedRect(btn_rect, 6, 6)
            painter.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
            painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, "✅ 영역 선택 완료")

        # 상단 안내 문구
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Malgun Gothic", 13, QFont.Weight.Bold))
        guide_msg = (
            "\n\n🖱️ 마우스로 사각형을 그리세요." if self.state == self.STATE_IDLE else
            "\n\n📐 모서리 핸들로 크기 조절 | 사각형 안을 잡고 이동 | [Enter 키] 또는 [아래 버튼 클릭] 선택 완료 | [ESC] 취소"
        )
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            guide_msg
        )

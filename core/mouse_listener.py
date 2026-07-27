import time
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from pynput import mouse

class GlobalMouseListener(QObject):
    """
    pynput 기반 전역 마우스 좌클릭 감지 서비스.
    - 클릭 캡처 모드가 활성화(is_active=True)되어 있을 때 좌클릭 이벤트를 감지하여 PyQt Signal을 발신합니다.
    """
    left_clicked = pyqtSignal(int, int)  # x, y 좌표 전달
    log_message = pyqtSignal(str)

    def __init__(self, cooldown_sec: float = 0.2):
        super().__init__()
        self.is_active = False
        self.cooldown_sec = cooldown_sec
        self.last_click_time = 0
        self._listener = None

    def start_listening(self):
        """마우스 리스너 스레드 시작"""
        if self._listener is None:
            self._listener = mouse.Listener(on_click=self._on_click)
            self._listener.start()
            self.log_message.emit("전역 마우스 감지 서비스가 시작되었습니다.")

    def stop_listening(self):
        """마우스 리스너 스레드 중지"""
        if self._listener:
            self._listener.stop()
            self._listener = None
            self.log_message.emit("전역 마우스 감지 서비스가 중지되었습니다.")

    def set_active(self, active: bool):
        """클릭 캡처 활성화 여부 설정"""
        self.is_active = active

    def _on_click(self, x, y, button, pressed):
        """pynput 콜백 함수"""
        if not self.is_active:
            return

        # 마우스 좌클릭이 눌렸을 때 (pressed=True)
        if button == mouse.Button.left and pressed:
            now = time.time()
            if now - self.last_click_time >= self.cooldown_sec:
                self.last_click_time = now
                self.left_clicked.emit(int(x), int(y))

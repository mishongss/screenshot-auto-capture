import os
from PyQt6.QtCore import Qt, pyqtSlot, QSize, QRect, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QGroupBox, QSplitter,
    QCheckBox, QTextEdit, QMessageBox, QFrame, QSizePolicy, QComboBox,
    QFileDialog
)

from core.capture_engine import CaptureEngine
from core.mouse_listener import GlobalMouseListener
from ui.region_selector import RegionSelector
from automation.pipeline import AutomationPipeline

DARK_STYLE = """
QMainWindow {
    background-color: #12151c;
    color: #e1e4ea;
}
QWidget {
    font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
    color: #e1e4ea;
}
QGroupBox {
    background-color: #1a1e28;
    border: 1px solid #2e3545;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    font-size: 13px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #00d2ff;
}
QLineEdit {
    background-color: #0d1017;
    border: 1px solid #2e3545;
    border-radius: 6px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #00d2ff;
}
QPushButton {
    background-color: #242b3b;
    border: 1px solid #3a455d;
    border-radius: 6px;
    padding: 10px 16px;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2d364a;
    border-color: #00d2ff;
}
QPushButton:pressed {
    background-color: #1d2330;
}
QPushButton#btnCaptureToggle {
    background-color: #1a3c34;
    border: 1px solid #2b6355;
    color: #52ecbe;
}
QPushButton#btnCaptureToggle:checked {
    background-color: #701c23;
    border: 1px solid #a82e38;
    color: #ff7682;
}
QPushButton#btnSetRegion {
    background-color: #1f334a;
    border: 1px solid #2e537d;
    color: #4da6ff;
}
QListWidget {
    background-color: #0d1017;
    border: 1px solid #2e3545;
    border-radius: 6px;
    padding: 4px;
}
QListWidget::item {
    background-color: #171b26;
    border-radius: 4px;
    margin: 4px;
    padding: 6px;
}
QListWidget::item:hover {
    background-color: #222838;
}
QTextEdit {
    background-color: #0d1017;
    border: 1px solid #2e3545;
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    color: #a0aec0;
}
QLabel#statusBanner {
    background-color: #171b26;
    border: 1px solid #2e3545;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 12px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("연속 화면 캡처 및 자동화 시스템 (Antigravity Capture)")
        self.resize(1000, 680)
        self.setStyleSheet(DARK_STYLE)

        # 자동 타이머 초기화 (2초 간격 캡처)
        self.auto_timer = QTimer(self)
        self.auto_timer.setInterval(2000)
        self.auto_timer.timeout.connect(self._do_capture)

        # F9 캡처 단축키 설정
        self.shortcut_f9 = QShortcut(QKeySequence("F9"), self)
        self.shortcut_f9.activated.connect(self._do_capture)

        # 코어 엔진 및 인스턴스 초기화
        self.capture_engine = CaptureEngine(title="스크린샷")
        self.mouse_listener = GlobalMouseListener(cooldown_sec=0.25)
        self.region_selector = RegionSelector()
        self.automation_pipeline = AutomationPipeline()

        # UI 구성
        self._init_ui()

        # 이벤트 시그널 연결
        self.region_selector.region_selected.connect(self._on_region_selected)
        self.mouse_listener.left_clicked.connect(self._on_left_click_triggered)
        self.mouse_listener.log_message.connect(self.log)

        # 마우스 리스너 시작
        self.mouse_listener.start_listening()

        # 초기 상태 업데이트
        self._update_folder_info()
        self.log(f"초기화 완료: 저장 폴더 -> {self.capture_engine.current_dir}")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # 스플리터 (좌 측 컨트롤 패널 / 우 측 갤러리 및 자동화 모듈 패널)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # ----------------------------------------------------
        # 1. 좌측 컨트롤 패널
        # ----------------------------------------------------
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)

        # (1) 저장 제목 및 위치 설정 그룹
        grp_title = QGroupBox("1. 저장 제목 및 저장 위치(폴더) 지정")
        layout_title = QVBoxLayout(grp_title)
        
        lbl_dir_desc = QLabel("① 저장할 상위 위치(폴더)를 선택하세요:")
        lbl_dir_desc.setStyleSheet("color: #a0aec0; font-size: 12px;")
        layout_title.addWidget(lbl_dir_desc)

        layout_base_dir = QHBoxLayout()
        self.txt_base_dir = QLineEdit(r"D:\77_Antigravity\screenshot")
        self.txt_base_dir.setPlaceholderText("저장될 상위 디렉토리 경로 입력 또는 선택")
        self.txt_base_dir.editingFinished.connect(self._on_base_dir_apply)
        layout_base_dir.addWidget(self.txt_base_dir)

        self.btn_select_dir = QPushButton("📁 폴더 선택")
        self.btn_select_dir.setStyleSheet("background-color: #1f334a; border: 1px solid #00d2ff; color: #00d2ff;")
        self.btn_select_dir.clicked.connect(self._browse_base_directory)
        layout_base_dir.addWidget(self.btn_select_dir)
        layout_title.addLayout(layout_base_dir)

        lbl_title_desc = QLabel("② 프로젝트/캡처 제목을 입력하세요 (하위 폴더명):")
        lbl_title_desc.setStyleSheet("color: #a0aec0; font-size: 12px; margin-top: 6px;")
        layout_title.addWidget(lbl_title_desc)

        layout_title_input = QHBoxLayout()
        self.txt_title = QLineEdit("스크린샷")
        self.txt_title.setPlaceholderText("제목 입력 후 엔터를 누르세요")
        self.txt_title.editingFinished.connect(self._on_title_apply)
        layout_title_input.addWidget(self.txt_title)

        self.btn_apply_title = QPushButton("적용")
        self.btn_apply_title.setFixedWidth(60)
        self.btn_apply_title.clicked.connect(self._on_title_apply)
        layout_title_input.addWidget(self.btn_apply_title)

        layout_title.addLayout(layout_title_input)

        self.lbl_path = QLabel()
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setStyleSheet("color: #00d2ff; font-size: 11px; font-weight: normal; margin-top: 4px;")
        layout_title.addWidget(self.lbl_path)

        self.btn_open_folder = QPushButton("📂 최종 저장 폴더 열기 (탐색기)")
        self.btn_open_folder.clicked.connect(self._open_target_folder)
        layout_title.addWidget(self.btn_open_folder)

        left_layout.addWidget(grp_title)

        # (2) 캡처 영역 지정 그룹
        grp_region = QGroupBox("2. 캡처 영역 지정")
        layout_region = QVBoxLayout(grp_region)

        self.btn_set_region = QPushButton("🎯 캡처 영역 지정 (Drag & Drop)")
        self.btn_set_region.setObjectName("btnSetRegion")
        self.btn_set_region.clicked.connect(self._open_region_selector)
        layout_region.addWidget(self.btn_set_region)

        self.lbl_region_info = QLabel("현재 영역: 지정되지 않음")
        self.lbl_region_info.setStyleSheet("color: #e2e8f0; font-size: 12px;")
        layout_region.addWidget(self.lbl_region_info)

        left_layout.addWidget(grp_region)

        # (3) 캡처 실행 & 2페이지 자동 분할 및 캡처 모드 그룹
        grp_capture = QGroupBox("3. 캡처 실행 & 보안 뷰어 감지 회피 캡처 모드")
        layout_capture = QVBoxLayout(grp_capture)

        lbl_split_desc = QLabel("📄 페이지 분할 설정 (2면으로 된 화면 캡처 시):")
        lbl_split_desc.setStyleSheet("color: #a0aec0; font-size: 11px;")
        layout_capture.addWidget(lbl_split_desc)

        self.cbo_split_mode = QComboBox()
        self.cbo_split_mode.addItem("1페이지 단일 캡처 (분할 없음)", "none")
        self.cbo_split_mode.addItem("↔️ 좌/우 2페이지 자동 분할 (Left/Right 50%)", "horizontal")
        self.cbo_split_mode.addItem("↕️ 상/하 2페이지 자동 분할 (Top/Bottom 50%)", "vertical")
        self.cbo_split_mode.currentIndexChanged.connect(self._on_split_mode_changed)
        self.cbo_split_mode.setStyleSheet("""
            QComboBox {
                background-color: #0d1017;
                border: 1px solid #00d2ff;
                border-radius: 6px;
                padding: 6px 12px;
                color: #52ecbe;
                font-weight: bold;
            }
            QComboBox QAbstractItemView {
                background-color: #171b26;
                color: #ffffff;
                selection-background-color: #00d2ff;
            }
        """)
        layout_capture.addWidget(self.cbo_split_mode)

        # 캡처 방식 선택 (마우스 클릭 / 타이머 자동 캡처 / 단축키 캡처)
        lbl_mode_desc = QLabel("🔒 보안 뷰어(E-book Reader) 차단 회피 캡처 방식:")
        lbl_mode_desc.setStyleSheet("color: #ffb86c; font-size: 11px; font-weight: bold; margin-top: 8px;")
        layout_capture.addWidget(lbl_mode_desc)

        layout_modes = QHBoxLayout()
        self.btn_capture_toggle = QPushButton("🖱️ 마우스 좌클릭 캡처")
        self.btn_capture_toggle.setObjectName("btnCaptureToggle")
        self.btn_capture_toggle.setCheckable(True)
        self.btn_capture_toggle.toggled.connect(self._toggle_click_capture)
        layout_modes.addWidget(self.btn_capture_toggle)

        self.btn_timer_capture = QPushButton("⏱️ 2초 간격 자동 연속 캡처 (추천)")
        self.btn_timer_capture.setCheckable(True)
        self.btn_timer_capture.setStyleSheet("background-color: #1f334a; border: 1px solid #00d2ff; color: #00d2ff;")
        self.btn_timer_capture.toggled.connect(self._toggle_timer_capture)
        layout_modes.addWidget(self.btn_timer_capture)

        layout_capture.addLayout(layout_modes)

        layout_btns = QHBoxLayout()
        self.btn_single_capture = QPushButton("📸 1회 즉시 캡처 (F9 단축키)")
        self.btn_single_capture.clicked.connect(self._do_capture)
        layout_btns.addWidget(self.btn_single_capture)

        self.btn_split_existing = QPushButton("✂️ 기존 2페이지 이미지 일괄 분할")
        self.btn_split_existing.setStyleSheet("background-color: #3b2818; border: 1px solid #7c4c23; color: #ffb86c;")
        self.btn_split_existing.clicked.connect(self._split_existing_images)
        layout_btns.addWidget(self.btn_split_existing)

        layout_capture.addLayout(layout_btns)

        left_layout.addWidget(grp_capture)

        # (4) 상태 배너
        self.lbl_status = QLabel("대기 중... 영역 지정 후 캡처를 시작하세요.")
        self.lbl_status.setObjectName("statusBanner")
        left_layout.addWidget(self.lbl_status)

        left_layout.addStretch()
        splitter.addWidget(left_panel)

        # ----------------------------------------------------
        # 2. 우측 갤러리 & 자동화 개발 구역 패널
        # ----------------------------------------------------
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        # (1) 최근 캡처 갤러리
        grp_gallery = QGroupBox("캡처된 화면 갤러리 (저장 포맷: 제목_001.png)")
        layout_gallery = QVBoxLayout(grp_gallery)

        self.list_gallery = QListWidget()
        self.list_gallery.setIconSize(QSize(160, 100))
        self.list_gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_gallery.setMovement(QListWidget.Movement.Static)
        self.list_gallery.setSpacing(8)
        self.list_gallery.itemDoubleClicked.connect(self._open_file)
        layout_gallery.addWidget(self.list_gallery)

        right_layout.addWidget(grp_gallery, stretch=3)

        # (2) 추후 자동화 확장 개발 구역 (Automation Layer & Log)
        grp_automation = QGroupBox("🤖 자동화 모듈 & 개발 구역 (Automation Pipeline)")
        layout_auto = QVBoxLayout(grp_automation)

        layout_hooks = QHBoxLayout()
        self.chk_json_hook = QCheckBox("자동 메타데이터 JSON 기록 (hooks.py)")
        self.chk_json_hook.setChecked(True)
        self.chk_json_hook.toggled.connect(self._toggle_json_hook)
        layout_hooks.addWidget(self.chk_json_hook)

        self.chk_ocr_hook = QCheckBox("추후 OCR/AI 분석 훅 사용 설정 (SampleOCRHook)")
        self.chk_ocr_hook.setChecked(False)
        self.chk_ocr_hook.toggled.connect(self._toggle_ocr_hook)
        layout_hooks.addWidget(self.chk_ocr_hook)
        layout_auto.addLayout(layout_hooks)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        layout_auto.addWidget(self.txt_log)

        right_layout.addWidget(grp_automation, stretch=2)

        splitter.addWidget(right_panel)
        splitter.setSizes([380, 620])

    def log(self, text: str):
        """실시간 시스템 로그 기록"""
        self.txt_log.append(f"[{os.path.basename(self.capture_engine.current_dir)}] {text}")
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _browse_base_directory(self):
        """파일 탐색기를 통해 저장 상위 디렉토리를 사용자가 직접 선택"""
        current = self.txt_base_dir.text().strip()
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "캡처 파일이 저장될 상위 폴더 선택",
            current if os.path.exists(current) else r"D:\77_Antigravity\screenshot"
        )
        if selected_dir:
            self.txt_base_dir.setText(selected_dir)
            self._on_base_dir_apply()

    def _on_base_dir_apply(self):
        path = self.txt_base_dir.text().strip()
        if not path:
            path = r"D:\77_Antigravity\screenshot"
            self.txt_base_dir.setText(path)
        self.capture_engine.set_base_directory(path)
        self._update_folder_info()
        self.log(f"저장 상위 폴더 변경 완료 -> {path}")

    def _on_title_apply(self):
        text = self.txt_title.text().strip()
        if not text:
            text = "스크린샷"
            self.txt_title.setText(text)
        self.capture_engine.update_target_directory(text)
        self._update_folder_info()
        self.log(f"저장 제목/폴더 변경 완료: {text}")

    def _open_target_folder(self):
        folder_path = self.capture_engine.current_dir
        if os.path.exists(folder_path):
            os.startfile(folder_path)
            self.log(f"저장 폴더 열기 -> {folder_path}")
        else:
            QMessageBox.information(self, "안내", "저장 폴더가 아직 생성되지 않았습니다.")

    def _update_folder_info(self):
        self.lbl_path.setText(f"📂 저장 경로:\n{self.capture_engine.current_dir}")
        self.lbl_status.setText(f"다음 저장 파일: {self.capture_engine.title}_{self.capture_engine.current_index:03d}.png")

    def _open_region_selector(self):
        self.hide()
        self.region_selector.start_selection()

    @pyqtSlot(int, int, int, int)
    def _on_region_selected(self, x, y, width, height):
        self.show()
        self.capture_engine.set_region(x, y, width, height)
        self.lbl_region_info.setText(f"현재 영역: X={x}, Y={y}, W={width}, H={height}")
        self.log(f"캡처 영역 설정됨 -> X:{x}, Y:{y}, W:{width}, H:{height}")
        self.lbl_status.setText("캡처 영역 설정 완료. 좌클릭 캡처를 활성화하세요.")

    def _toggle_click_capture(self, checked: bool):
        if checked:
            if not self.capture_engine.region:
                QMessageBox.warning(self, "경고", "먼저 캡처 영역을 지정해 주세요!")
                self.btn_capture_toggle.setChecked(False)
                return
            
            # 타이머 캡처가 켜져 있으면 끔
            if self.btn_timer_capture.isChecked():
                self.btn_timer_capture.setChecked(False)

            self.mouse_listener.set_active(True)
            self.btn_capture_toggle.setText("🛑 좌클릭 캡처 중지")
            self.lbl_status.setText("🟢 마우스 좌클릭 캡처 진행 중...")
            self.log("마우스 좌클릭 연속 캡처 활성화됨.")
        else:
            self.mouse_listener.set_active(False)
            self.btn_capture_toggle.setText("🖱️ 마우스 좌클릭 캡처")
            self.lbl_status.setText("🔴 마우스 좌클릭 캡처 중지됨.")
            self.log("마우스 좌클릭 연속 캡처 비활성화됨.")

    def _toggle_timer_capture(self, checked: bool):
        if checked:
            if not self.capture_engine.region:
                QMessageBox.warning(self, "경고", "먼저 캡처 영역을 지정해 주세요!")
                self.btn_timer_capture.setChecked(False)
                return
            
            # 마우스 좌클릭 캡처가 켜져 있으면 끔 (보안 감지 회피)
            if self.btn_capture_toggle.isChecked():
                self.btn_capture_toggle.setChecked(False)

            self.auto_timer.start()
            self.btn_timer_capture.setText("🛑 2초 자동 캡처 중지")
            self.btn_timer_capture.setStyleSheet("background-color: #701c23; border: 1px solid #a82e38; color: #ff7682;")
            self.lbl_status.setText("⏱️ 2초 간격 자동 연속 캡처 진행 중... (보안 뷰어 회피 특화)")
            self.log("⏱️ 2초 간격 자동 연속 캡처 활성화됨.")
        else:
            self.auto_timer.stop()
            self.btn_timer_capture.setText("⏱️ 2초 간격 자동 연속 캡처 (추천)")
            self.btn_timer_capture.setStyleSheet("background-color: #1f334a; border: 1px solid #00d2ff; color: #00d2ff;")
            self.lbl_status.setText("🔴 자동 타이머 캡처 중지됨.")
            self.log("자동 타이머 캡처 비활성화됨.")

    @pyqtSlot(int, int)
    def _on_left_click_triggered(self, click_x: int, click_y: int):
        """마우스 좌클릭 시 호출되는 핸들러"""
        # 만약 클릭 위치가 현재 메인 윈도우 UI 내부라면 조작용 클릭이므로 캡처 제외
        win_geo = self.geometry()
        if self.isVisible() and win_geo.contains(click_x, click_y):
            return

        self._do_capture()

    def _on_split_mode_changed(self, index: int):
        mode = self.cbo_split_mode.currentData()
        self.capture_engine.set_split_mode(mode)
        mode_text = self.cbo_split_mode.currentText()
        self.log(f"페이지 분할 모드 변경 -> {mode_text}")

    def _split_existing_images(self):
        """현재 폴더에 있는 2페이지짜리 캡처 이미지를 1페이지씩 쪼개기"""
        mode = self.cbo_split_mode.currentData()
        direction = "horizontal" if mode != "vertical" else "vertical"
        
        reply = QMessageBox.question(
            self,
            "기존 이미지 분할 확인",
            f"현재 폴더({os.path.basename(self.capture_engine.current_dir)})에 있는 이미지를 1페이지씩 ({'좌/우' if direction == 'horizontal' else '상/하'}) 분할하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            count = self.capture_engine.split_existing_folder_images(split_direction=direction)
            if count > 0:
                self.log(f"기존 이미지 분할 완료! 총 {count}개의 1페이지 이미지로 전환되었습니다.")
                self.list_gallery.clear()
                # 갤러리 목록 새로고침
                for i in range(1, count + 1):
                    fname = f"{self.capture_engine.title}_{i:03d}.png"
                    fpath = os.path.join(self.capture_engine.current_dir, fname)
                    if os.path.exists(fpath):
                        self._add_gallery_item(fpath)
                self._update_folder_info()
                QMessageBox.information(self, "완료", f"총 {count}개의 1페이지 이미지로 분할 완료되었습니다!")
            else:
                QMessageBox.warning(self, "알림", "분할할 이미지를 찾지 못했거나 이미 분할되었습니다.")

    def _do_capture(self):
        """실제 화면 캡처 수행 및 파이프라인/갤러리 연동"""
        try:
            saved_paths = self.capture_engine.capture_screen()
            for saved_path in saved_paths:
                if saved_path and os.path.exists(saved_path):
                    filename = os.path.basename(saved_path)
                    self.log(f"캡처 성공 -> {filename}")
                    self._add_gallery_item(saved_path)

                    # 자동화 파이프라인 훅 실행
                    metadata = {
                        "title": self.capture_engine.title,
                        "index": self.capture_engine.current_index - 1,
                        "region": self.capture_engine.region,
                        "path": saved_path
                    }
                    self.automation_pipeline.trigger_on_capture(saved_path, metadata)

            self._update_folder_info()

        except Exception as e:
            self.log(f"캡처 실패: {e}")
            self.lbl_status.setText(f"❌ 캡처 에러: {e}")

    def _add_gallery_item(self, filepath: str):
        filename = os.path.basename(filepath)
        pixmap = QPixmap(filepath)

        item = QListWidgetItem()
        item.setText(filename)
        item.setIcon(QIcon(pixmap.scaled(160, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
        item.setData(Qt.ItemDataRole.UserRole, filepath)

        self.list_gallery.insertItem(0, item)

    def _open_file(self, item: QListWidgetItem):
        filepath = item.data(Qt.ItemDataRole.UserRole)
        if filepath and os.path.exists(filepath):
            os.startfile(filepath)

    def _toggle_json_hook(self, checked: bool):
        for hook in self.automation_pipeline.hooks:
            if hook.name == "JSON Metadata Logging Hook":
                hook.enabled = checked
                self.log(f"JSON 메타데이터 기록 훅 -> {'활성화' if checked else '비활성화'}")

    def _toggle_ocr_hook(self, checked: bool):
        for hook in self.automation_pipeline.hooks:
            if hook.name == "Future OCR & Image Analysis Extension Point":
                hook.enabled = checked
                self.log(f"추후 OCR/AI 분석 개발 훅 -> {'활성화' if checked else '비활성화'}")

    def closeEvent(self, event):
        self.mouse_listener.stop_listening()
        event.accept()

import os
import re
import mss
from PIL import Image, ImageGrab
from datetime import datetime

class CaptureEngine:
    """
    화면 캡처 엔진 및 파일 저장 관리자.
    - Base Dir: D:\\77_Antigravity\\screenshot
    - Project Dir: D:\\77_Antigravity\\screenshot\\<title>
    - Naming Format: <title>_<index:03d>.png (예: 제목_001.png)
    - 다중 모니터, 2페이지 자동 분할 지원
    - 보안 뷰어(E-book Reader, DRM) 감지 차단 방지 DWM 하드웨어 캡처 엔진
    """

    BASE_DIR = r"D:\77_Antigravity\screenshot"

    def __init__(self, title: str = "Capture"):
        self.title = title.strip() if title.strip() else "Capture"
        self.current_dir = ""
        self.current_index = 1
        self.region = None  # (left, top, width, height)
        self.split_mode = "none"  # "none", "horizontal" (좌/우 분할), "vertical" (상/하 분할)
        self.bypass_drm = False  # 보안 프로그램이 PrintWindow를 감지하여 카메라X를 띄우는 것을 막기 위해 기본값 False로 설정
        self.update_target_directory(self.title)

    def update_target_directory(self, title: str):
        """제목 설정 시 하위 폴더 경로를 설정하고 즉시 생성한 뒤 일련번호 카운터를 갱신합니다."""
        self.title = title.strip() if title.strip() else "Capture"
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', self.title)
        self.current_dir = os.path.join(self.BASE_DIR, safe_title)
        os.makedirs(self.current_dir, exist_ok=True)
        self.sync_current_index()

    def sync_current_index(self):
        """현재 폴더에 기존 파일이 있다면 최고 일련번호 + 1로 자동 설정합니다."""
        if not os.path.exists(self.current_dir):
            self.current_index = 1
            return

        pattern = re.compile(rf"^{re.escape(self.title)}_(\d+)\.png$", re.IGNORECASE)
        max_idx = 0
        for fname in os.listdir(self.current_dir):
            match = pattern.match(fname)
            if match:
                idx = int(match.group(1))
                if idx > max_idx:
                    max_idx = idx
        self.current_index = max_idx + 1

    def set_region(self, left: int, top: int, width: int, height: int):
        """캡처 대상 영역을 설정합니다."""
        self.region = {
            "left": int(left),
            "top": int(top),
            "width": int(width),
            "height": int(height)
        }

    def set_split_mode(self, mode: str):
        """
        페이지 분할 모드 설정:
        - "none": 분할 없음
        - "horizontal": 좌/우 50% 2페이지 분할
        - "vertical": 상/하 50% 2페이지 분할
        """
        self.split_mode = mode

    def set_bypass_drm(self, enabled: bool):
        """보안/캡처 방지 프로그램 자동 우회 모드 설정"""
        self.bypass_drm = enabled

    def capture_screen(self) -> list:
        """
        보안 뷰어가 감지하지 못하는 Windows DWM / PIL 전역 GPU 캡처 방식으로
        원본 화면을 카메라 X 아이콘 없이 깨끗하게 캡처합니다.
        """
        if not self.region or self.region["width"] <= 0 or self.region["height"] <= 0:
            raise ValueError("캡처 영역이 지정되지 않았거나 유효하지 않습니다.")

        os.makedirs(self.current_dir, exist_ok=True)

        left = self.region["left"]
        top = self.region["top"]
        width = self.region["width"]
        height = self.region["height"]
        right = left + width
        bottom = top + height

        full_img = None

        # 1차 시도: PIL ImageGrab (all_screens=True) -> 보안 뷰어가 API 호출을 감지하지 못하는 표준 DWM 디스플레이 복사 방식
        try:
            full_img = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
        except Exception:
            full_img = None

        # 2차 시도: mss 고속 디스플레이 프레임 버퍼 복사
        if full_img is None:
            try:
                with mss.mss() as sct:
                    sct_img = sct.grab(self.region)
                    full_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                full_img = None

        saved_paths = []
        w, h = full_img.size

        if self.split_mode == "horizontal" and w >= 2:
            # 좌/우 2페이지 분할
            half_w = w // 2
            left_img = full_img.crop((0, 0, half_w, h))
            right_img = full_img.crop((half_w, 0, w, h))

            # 1번째 (좌측 페이지) 저장
            path1 = os.path.join(self.current_dir, f"{self.title}_{self.current_index:03d}.png")
            left_img.save(path1, "PNG")
            saved_paths.append(path1)
            self.current_index += 1

            # 2번째 (우측 페이지) 저장
            path2 = os.path.join(self.current_dir, f"{self.title}_{self.current_index:03d}.png")
            right_img.save(path2, "PNG")
            saved_paths.append(path2)
            self.current_index += 1

        elif self.split_mode == "vertical" and h >= 2:
            # 상/하 2페이지 분할
            half_h = h // 2
            top_img = full_img.crop((0, 0, w, half_h))
            bottom_img = full_img.crop((0, half_h, w, h))

            # 1번째 (상단 페이지) 저장
            path1 = os.path.join(self.current_dir, f"{self.title}_{self.current_index:03d}.png")
            top_img.save(path1, "PNG")
            saved_paths.append(path1)
            self.current_index += 1

            # 2번째 (하단 페이지) 저장
            path2 = os.path.join(self.current_dir, f"{self.title}_{self.current_index:03d}.png")
            bottom_img.save(path2, "PNG")
            saved_paths.append(path2)
            self.current_index += 1

        else:
            # 분할 없음 (단일 캡처)
            filepath = os.path.join(self.current_dir, f"{self.title}_{self.current_index:03d}.png")
            full_img.save(filepath, "PNG")
            saved_paths.append(filepath)
            self.current_index += 1

        return saved_paths

    def split_existing_folder_images(self, split_direction: str = "horizontal") -> int:
        """
        현재 폴더에 이미 저장되어 있는 2페이지 캡처 이미지들을 일괄 1페이지씩 쪼개어
        새로운 순차 일련번호로 재정렬 저장하는 유틸리티.
        """
        if not os.path.exists(self.current_dir):
            return 0

        pattern = re.compile(rf"^{re.escape(self.title)}_(\d+)\.png$", re.IGNORECASE)
        files_to_process = []
        
        for fname in sorted(os.listdir(self.current_dir)):
            if pattern.match(fname):
                files_to_process.append(os.path.join(self.current_dir, fname))

        if not files_to_process:
            return 0

        temp_cropped_images = []

        for fpath in files_to_process:
            try:
                with Image.open(fpath) as img:
                    w, h = img.size
                    if split_direction == "horizontal" and w >= 2:
                        half_w = w // 2
                        left_img = img.crop((0, 0, half_w, h)).copy()
                        right_img = img.crop((half_w, 0, w, h)).copy()
                        temp_cropped_images.append(left_img)
                        temp_cropped_images.append(right_img)
                    elif split_direction == "vertical" and h >= 2:
                        half_h = h // 2
                        top_img = img.crop((0, 0, w, half_h)).copy()
                        bottom_img = img.crop((0, half_h, w, h)).copy()
                        temp_cropped_images.append(top_img)
                        temp_cropped_images.append(bottom_img)
                    else:
                        temp_cropped_images.append(img.copy())
            except Exception:
                pass

        if not temp_cropped_images:
            return 0

        for fpath in files_to_process:
            try:
                os.remove(fpath)
            except Exception:
                pass

        idx = 1
        for c_img in temp_cropped_images:
            new_path = os.path.join(self.current_dir, f"{self.title}_{idx:03d}.png")
            c_img.save(new_path, "PNG")
            idx += 1

        self.current_index = idx
        return len(temp_cropped_images)

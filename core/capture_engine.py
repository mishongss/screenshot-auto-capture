import os
import re
import mss
from PIL import Image
from datetime import datetime

class CaptureEngine:
    """
    화면 캡처 엔진 및 파일 저장 관리자.
    - Base Dir: D:\\77_Antigravity\\screenshot
    - Project Dir: D:\\77_Antigravity\\screenshot\\<title>
    - Naming Format: <title>_<index:03d>.png (예: 제목_001.png)
    """

    BASE_DIR = r"D:\77_Antigravity\screenshot"

    def __init__(self, title: str = "Capture"):
        self.title = title.strip() if title.strip() else "Capture"
        self.current_dir = ""
        self.current_index = 1
        self.region = None  # (left, top, width, height)
        self.split_mode = "none"  # "none", "horizontal" (좌/우 분할), "vertical" (상/하 분할)
        self.bypass_drm = True  # 🔒 캡처 방지 (DRM/보안 프로그램) 자동 우회 모드
        self.update_target_directory(self.title)

    def set_bypass_drm(self, enabled: bool):
        """보안/캡처 방지 프로그램 자동 우회 모드 설정"""
        self.bypass_drm = enabled

    def _bypass_window_affinity_and_grab(self, left: int, top: int, right: int, bottom: int):
        """
        [보안 우회 기술] Win32 API를 사용하여 캡처 차단 윈도우의 SetWindowDisplayAffinity 속성을 해제하고,
        PW_RENDERFULLCONTENT (0x02) 플래그를 통해 하드웨어 가속/보안 레이어를 우회 캡처합니다.
        """
        import ctypes
        import win32gui
        import win32ui
        import win32con
        from PIL import Image

        width = right - left
        height = bottom - top

        # 1. 캡처 대상 좌표에 위치한 윈도우 핸들(HWND) 구하기
        hwnd = win32gui.WindowFromPoint((left + width // 2, top + height // 2))
        if hwnd:
            try:
                # 윈도우의 DisplayAffinity 캡처 차단 마스크(WDA_EXCLUDEFROMCAPTURE=0x11)를 WDA_NONE(0)으로 강제 해제
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0)
            except Exception:
                pass

        # 2. PW_RENDERFULLCONTENT (0x00000002) 플래그를 이용한 Direct Framebuffer 복사
        hwnd_target = win32gui.GetDesktopWindow()
        hwnd_dc = win32gui.GetWindowDC(hwnd_target)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        # PW_RENDERFULLCONTENT (2)
        PW_RENDERFULLCONTENT = 2
        result = ctypes.windll.user32.PrintWindow(hwnd_target, save_dc.GetSafeHdc(), PW_RENDERFULLCONTENT)

        if result == 1:
            bmpinfo = save_bitmap.GetInfo()
            bmpstr = save_bitmap.GetBitmapBits(True)
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            # 수거 리소스 해제
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd_target, hwnd_dc)

            # 데스크톱 전체에서 해당 지정 영역 크롭
            if img.size[0] >= right and img.size[1] >= bottom and left >= 0 and top >= 0:
                return img.crop((left, top, right, bottom))
            return img

        # 리소스 해제
        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd_target, hwnd_dc)
        return None

    def capture_screen(self) -> list:
        """
        설정된 영역을 캡처하고 (다중 모니터 및 DRM 우회 지원), 분할 모드에 따라 1개 또는 2개의 파일로 저장합니다.
        반환값: 저장된 이미지 파일들의 절대 경로 리스트
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

        # 1차 시도 (DRM/보안 캡처 우회 모드인 경우)
        if self.bypass_drm:
            try:
                full_img = self._bypass_window_affinity_and_grab(left, top, right, bottom)
            except Exception:
                full_img = None

        # 2차 시도: PIL ImageGrab (all_screens=True -> Windows 다중 모니터 전역 지원)
        if full_img is None:
            try:
                from PIL import ImageGrab
                full_img = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
            except Exception:
                full_img = None

        # 3차 시도 (Fallback): mss 사용
        if full_img is None:
            with mss.mss() as sct:
                sct_img = sct.grab(self.region)
                full_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

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
        새로운 순차 일련번호로 재정렬 저장하는 백업/분할 유틸리티입니다.
        반환값: 새로 생성된 분할 파일 개수
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

        # 분할된 이미지를 임시 보관할 백업 리스트
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

        # 기존 원본 파일 삭제
        for fpath in files_to_process:
            try:
                os.remove(fpath)
            except Exception:
                pass

        # 새로 분할된 이미지들 제목_001.png부터 차례대로 재저장
        idx = 1
        for c_img in temp_cropped_images:
            new_path = os.path.join(self.current_dir, f"{self.title}_{idx:03d}.png")
            c_img.save(new_path, "PNG")
            idx += 1

        self.current_index = idx
        return len(temp_cropped_images)


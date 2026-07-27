import os
import json
from datetime import datetime

class BaseCaptureHook:
    """
    캡처 후 자동 처리를 위한 훅(Hook) 베이스 클래스.
    추후 개발 시 이 클래스를 상속받아 process() 메서드를 구현하면
    자동화 파이프라인에서 캡처 이벤트 직후 자동으로 실행됩니다.
    """
    def __init__(self, name: str = "BaseHook"):
        self.name = name
        self.enabled = True

    def process(self, image_path: str, metadata: dict):
        """
        :param image_path: 캡처 저장된 이미지 파일의 경로
        :param metadata: 캡처 당시의 메타데이터 (title, region, index, timestamp 등)
        """
        raise NotImplementedError("Subclasses must implement process()")


class JSONMetadataHook(BaseCaptureHook):
    """
    [개발 구역 샘플 1] 캡처 시마다 해당 폴더에 메타데이터 log (capture_history.json)를 자동 기록하는 훅.
    """
    def __init__(self):
        super().__init__(name="JSON Metadata Logging Hook")

    def process(self, image_path: str, metadata: dict):
        if not self.enabled:
            return

        target_dir = os.path.dirname(image_path)
        log_file = os.path.join(target_dir, "capture_history.json")

        entry = {
            "file": os.path.basename(image_path),
            "full_path": image_path,
            "timestamp": datetime.now().isoformat(),
            "region": metadata.get("region"),
            "title": metadata.get("title"),
            "index": metadata.get("index")
        }

        history = []
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []

        history.append(entry)

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)


class SampleOCRHook(BaseCaptureHook):
    """
    [개발 구역 샘플 2] 추후 이미지 OCR 분석 또는 텍스트 추출, 이미지 템플릿 매칭을 연동할 수 있는 확장을 위한 개발 영역.
    """
    def __init__(self):
        super().__init__(name="Future OCR & Image Analysis Extension Point")
        self.enabled = False  # 개발 및 테스트 시 True로 전환하여 사용

    def process(self, image_path: str, metadata: dict):
        if not self.enabled:
            return
        
        # =========================================================================
        # [개발 영역] 여기에 OCR (easyocr, pytesseract) 또는 OpenCV 분석 코드를 추가하세요.
        # 예시:
        # text = pytesseract.image_to_string(Image.open(image_path))
        # print(f"[OCR Result for {image_path}]: {text}")
        # =========================================================================
        pass

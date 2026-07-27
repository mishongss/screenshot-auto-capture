# 📸 연속 화면 캡처 및 자동화 확장 데스크톱 앱 (Antigravity Capture)

마우스 좌클릭만으로 설정된 영역을 연속으로 캡처하고 일련번호로 자동 저장하며, 추후 OCR 및 이미지 분석/매크로 등 완전 자동화를 쉽게 연동할 수 있는 Python PyQt6 기반 앱입니다.

---

## ✨ 핵심 기능

1. **제목 입력 기반 자동 폴더 생성**
   - 제목을 입력하면 `D:\77_Antigravity\screenshot\<제목>` 하위에 폴더가 자동으로 생성되고 관리됩니다.
2. **캡처 영역 지정 & 마우스 좌클릭 연속 캡처**
   - `캡처 영역 지정 (Drag & Drop)` 버튼을 눌러 원하는 화면 범위를 반투명 오버레이로 자유롭게 선택합니다.
   - `마우스 좌클릭 캡처 활성화`를 켜면, 작업 창이나 웹페이지 등에서 **마우스 좌클릭을 할 때마다 해당 영역이 연속 캡처**됩니다.
3. **일련번호 순차 자동 저장**
   - `제목_001.png`, `제목_002.png`, `제목_003.png` 포맷으로 자동 번호가 매겨져 저장됩니다.
4. **추후 완전 자동화를 위한 모듈형 개발 구역 (`automation/`)**
   - **`automation/hooks.py`**: 캡처 즉시 호출되는 이벤트 훅 (기본적으로 `capture_history.json` 로그 자동 기록 제공).
   - **`automation/pipeline.py`**: 추후 OCR, AI 분석, 이미지 매크로, 웹훅 전송 등을 확장할 수 있는 인터페이스 제공.

---

## 🚀 실행 방법

### 방법 1: 배치 파일로 실행 (추천)
`start_app.bat` 파일을 더블클릭하여 바로 실행할 수 있습니다.

### 방법 2: 명령 프롬프트(CMD) / 터미널에서 실행
```bash
python main.py
```

---

## 🛠 추후 자동화 확장 방법 (개발 영역 가이드)

### 1. 캡처 후 자동 처리 훅 추가 (`automation/hooks.py`)
`BaseCaptureHook` 클래스를 상속받아 커스텀 로직을 작성할 수 있습니다.

```python
from automation.hooks import BaseCaptureHook

class MyCustomOCRHook(BaseCaptureHook):
    def __init__(self):
        super().__init__(name="EasyOCR Processing Hook")

    def process(self, image_path: str, metadata: dict):
        # 캡처 직후 실행할 코드 작성 (예: OCR 텍스트 추출)
        print(f"새로 캡처된 파일: {image_path}")
```

### 2. 파이프라인 등록 (`automation/pipeline.py`)
작성한 훅을 `AutomationPipeline`에 등록하면 캡처가 이루어질 때마다 자동으로 실행됩니다.

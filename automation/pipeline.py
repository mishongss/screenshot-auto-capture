import logging
from typing import List
from .hooks import BaseCaptureHook, JSONMetadataHook, SampleOCRHook

logger = logging.getLogger("AutomationPipeline")

class AutomationPipeline:
    """
    [완전 자동화 개발 영역 관리자]
    캡처 후 처리 훅(Hook)을 등록하고 실행하며,
    추후 조건부 자동 클릭/매크로, 스케줄링, 외부 API 연동 등의 전 과정 자동화 파이프라인을 관장합니다.
    """

    def __init__(self):
        self.hooks: List[BaseCaptureHook] = []
        self._register_default_hooks()

    def _register_default_hooks(self):
        """기본 설치 개발 훅 등록"""
        self.add_hook(JSONMetadataHook())
        self.add_hook(SampleOCRHook())

    def add_hook(self, hook: BaseCaptureHook):
        """새로운 자동화 훅 추가"""
        self.hooks.append(hook)

    def trigger_on_capture(self, image_path: str, metadata: dict):
        """
        캡처 발생 시 등록된 모든 훅을 순차적으로 호출합니다.
        """
        for hook in self.hooks:
            if getattr(hook, 'enabled', True):
                try:
                    hook.process(image_path, metadata)
                except Exception as e:
                    logger.error(f"Error executing hook '{hook.name}': {e}")

    # =========================================================================
    # [추후 완전 자동화 개발 영역]
    # 아래 공간에 화면 특정 텍스트/이미지 감지 후 자동 클릭 매크로,
    # 주기적 캡처 타이머, 네트워크 서버 전송 등을 자유롭게 구현할 수 있습니다.
    # =========================================================================

    def run_auto_macro_task(self, target_region: tuple, interval_sec: float = 1.0):
        """
        [샘플 개발 인터페이스] 자동 타이머 기반 연속 캡처 또는 매크로 실행 개발 영역
        """
        pass

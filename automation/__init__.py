# automation package initialization
from .pipeline import AutomationPipeline
from .hooks import BaseCaptureHook, JSONMetadataHook, SampleOCRHook
from .epub_builder import OCRToEpubBuilder

__all__ = ["AutomationPipeline", "BaseCaptureHook", "JSONMetadataHook", "SampleOCRHook", "OCRToEpubBuilder"]

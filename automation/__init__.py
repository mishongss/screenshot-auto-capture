# automation package initialization
from .pipeline import AutomationPipeline
from .hooks import BaseCaptureHook, JSONMetadataHook, SampleOCRHook

__all__ = ["AutomationPipeline", "BaseCaptureHook", "JSONMetadataHook", "SampleOCRHook"]

"""Site analysis for auto-detecting torrent site configurations."""

from .analyzer import AnalysisResult, SiteAnalyzer
from .validator import ValidationResult, validate_config, validate_magnet_fetch

__all__ = [
    "SiteAnalyzer",
    "AnalysisResult",
    "ValidationResult",
    "validate_config",
    "validate_magnet_fetch",
]

"""Metric computation logic built on canonical field records."""

from metric_parser.compute.definitions import METRIC_DEFINITION_BY_CODE
from metric_parser.compute.definitions import METRIC_DEFINITIONS
from metric_parser.compute.engine import ComparisonContext
from metric_parser.compute.engine import compute_metrics_bundle

__all__ = [
    "ComparisonContext",
    "METRIC_DEFINITION_BY_CODE",
    "METRIC_DEFINITIONS",
    "compute_metrics_bundle",
]

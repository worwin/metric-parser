from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from metric_parser.models import MetricRecord
from metric_parser.models import MetricWarningRecord
from metric_parser.models import MetricsBundleArtifact
from metric_parser.models import PeriodFieldsArtifact
from metric_parser.pipeline import CompanyMetricBuildResult


def flatten_metric_records(bundles: list[MetricsBundleArtifact]) -> list[dict[str, Any]]:
    """Flatten metric bundle artifacts into metric row dictionaries.
    
    Args:
        bundles: The bundles value.
    
    Returns:
        The computed result.
    """
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        rows.extend(metric.to_dict() for metric in bundle.metrics)
    return rows


def flatten_warning_records(bundles: list[MetricsBundleArtifact]) -> list[dict[str, Any]]:
    """Flatten metric warning artifacts into warning row dictionaries.
    
    Args:
        bundles: The bundles value.
    
    Returns:
        The computed result.
    """
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        rows.extend(warning.to_dict() for warning in bundle.warnings)
    return rows


def flatten_period_fields(artifacts: list[PeriodFieldsArtifact]) -> list[dict[str, Any]]:
    """Flatten period field artifacts into field row dictionaries.
    
    Args:
        artifacts: The artifacts value.
    
    Returns:
        The computed result.
    """
    return [artifact.to_dict() for artifact in artifacts]


def write_company_metric_artifacts(output_dir: str | Path, build: CompanyMetricBuildResult) -> dict[str, str]:
    """Write all metric-parser output artifacts for a company build.
    
    Args:
        output_dir: The output_dir value.
        build: The build value.
    
    Returns:
        The computed result.
    """
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    annual_metrics = flatten_metric_records(build.annual_metrics)
    quarterly_metrics = flatten_metric_records(build.quarterly_metrics)
    warning_rows = flatten_warning_records(build.annual_metrics) + flatten_warning_records(build.quarterly_metrics)

    manifest = {
        "run_id": build.run_id,
        "ticker": build.ticker,
        "cik": build.cik,
        "company_name": build.company_name,
        "created_at": build.created_at,
        "source_catalog_path": build.source_catalog_path,
        "filing_count": len(build.source_filings),
        "annual_period_count": len(build.annual_fields),
        "quarterly_period_count": len(build.quarterly_fields),
        "annual_metric_record_count": len(annual_metrics),
        "quarterly_metric_record_count": len(quarterly_metrics),
        "warning_count": len(warning_rows),
    }

    path_map = {
        "build_manifest": output_root / "build_manifest.json",
        "source_filings": output_root / "source_filings.json",
        "annual_period_fields": output_root / "annual_period_fields.json",
        "quarterly_period_fields": output_root / "quarterly_period_fields.json",
        "annual_metric_bundles": output_root / "annual_metric_bundles.json",
        "quarterly_metric_bundles": output_root / "quarterly_metric_bundles.json",
        "annual_metrics": output_root / "annual_metrics.json",
        "quarterly_metrics": output_root / "quarterly_metrics.json",
        "metric_warnings": output_root / "metric_warnings.json",
    }

    _write_json(path_map["build_manifest"], manifest)
    _write_json(path_map["source_filings"], [asdict(record) for record in build.source_filings])
    _write_json(path_map["annual_period_fields"], flatten_period_fields(build.annual_fields))
    _write_json(path_map["quarterly_period_fields"], flatten_period_fields(build.quarterly_fields))
    _write_json(path_map["annual_metric_bundles"], [bundle.to_dict() for bundle in build.annual_metrics])
    _write_json(path_map["quarterly_metric_bundles"], [bundle.to_dict() for bundle in build.quarterly_metrics])
    _write_json(path_map["annual_metrics"], annual_metrics)
    _write_json(path_map["quarterly_metrics"], quarterly_metrics)
    _write_json(path_map["metric_warnings"], warning_rows)

    return {name: str(path) for name, path in path_map.items()}


def _write_json(path: Path, payload: Any) -> None:
    """Write json.
    
    Args:
        path: The path value.
        payload: The payload value.
    """
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

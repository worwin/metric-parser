from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from metric_parser.compute import ComparisonContext
from metric_parser.compute import compute_metrics_bundle
from metric_parser.ingest import FilingCatalogRecord
from metric_parser.ingest import load_catalog_records
from metric_parser.ingest import load_periodic_report_filing
from metric_parser.ingest import select_preferred_periodic_records
from metric_parser.mapping import build_period_fields_artifact
from metric_parser.models import MetricsBundleArtifact
from metric_parser.models import PeriodFieldsArtifact
from metric_parser.quarterization import derive_standalone_quarter_fields


@dataclass(frozen=True, slots=True)
class CompanyMetricBuildResult:
    run_id: str
    ticker: str
    cik: str
    company_name: str
    created_at: str
    source_catalog_path: str | None = None
    source_filings: list[FilingCatalogRecord] = field(default_factory=list)
    annual_fields: list[PeriodFieldsArtifact] = field(default_factory=list)
    quarterly_fields: list[PeriodFieldsArtifact] = field(default_factory=list)
    annual_metrics: list[MetricsBundleArtifact] = field(default_factory=list)
    quarterly_metrics: list[MetricsBundleArtifact] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the object to a JSON-ready dictionary.
        
        Returns:
            The computed result.
        """
        return {
            "run_id": self.run_id,
            "ticker": self.ticker,
            "cik": self.cik,
            "company_name": self.company_name,
            "created_at": self.created_at,
            "source_catalog_path": self.source_catalog_path,
            "source_filings": [asdict(record) for record in self.source_filings],
            "annual_fields": [artifact.to_dict() for artifact in self.annual_fields],
            "quarterly_fields": [artifact.to_dict() for artifact in self.quarterly_fields],
            "annual_metrics": [artifact.to_dict() for artifact in self.annual_metrics],
            "quarterly_metrics": [artifact.to_dict() for artifact in self.quarterly_metrics],
        }


def build_metric_histories_from_catalog_path(
    run_id: str,
    catalog_path: str | Path,
    ticker: str | None = None,
    cik: str | None = None,
    created_at: str | None = None,
) -> list[CompanyMetricBuildResult]:
    """Build metric histories from catalog path.
    
    Args:
        run_id: The run_id value.
        catalog_path: The catalog_path value.
        ticker: The ticker value.
        cik: The cik value.
        created_at: The created_at value.
    
    Returns:
        The computed result.
    """
    records = load_catalog_records(catalog_path)
    filtered_records = _filter_company_records(records, ticker=ticker, cik=cik)
    grouped: dict[str, list[FilingCatalogRecord]] = {}
    for record in filtered_records:
        grouped.setdefault(record.cik, []).append(record)

    return [
        build_company_metric_history(
            run_id=run_id,
            records=company_records,
            created_at=created_at,
            source_catalog_path=str(Path(catalog_path)),
        )
        for _, company_records in sorted(grouped.items())
    ]


def build_company_metric_history_from_catalog_path(
    run_id: str,
    catalog_path: str | Path,
    ticker: str | None = None,
    cik: str | None = None,
    created_at: str | None = None,
) -> CompanyMetricBuildResult:
    """Build company metric history from catalog path.
    
    Args:
        run_id: The run_id value.
        catalog_path: The catalog_path value.
        ticker: The ticker value.
        cik: The cik value.
        created_at: The created_at value.
    
    Returns:
        The computed result.
    """
    results = build_metric_histories_from_catalog_path(
        run_id=run_id,
        catalog_path=catalog_path,
        ticker=ticker,
        cik=cik,
        created_at=created_at,
    )
    if not results:
        raise ValueError("No metric-relevant filings matched the requested company filter")
    if len(results) != 1:
        raise ValueError("Expected exactly one company build; provide ticker or cik to narrow the selection")
    return results[0]


def build_company_metric_history(
    run_id: str,
    records: list[FilingCatalogRecord],
    created_at: str | None = None,
    source_catalog_path: str | None = None,
) -> CompanyMetricBuildResult:
    """Build annual and quarterly metric history artifacts for one company.
    
    Args:
        run_id: The run_id value.
        records: The records value.
        created_at: The created_at value.
        source_catalog_path: The source_catalog_path value.
    
    Returns:
        The computed result.
    """
    if not records:
        raise ValueError("Cannot build metric history without catalog records")

    cik_values = {record.cik for record in records}
    if len(cik_values) != 1:
        raise ValueError("Catalog records must belong to a single company")

    selected_records = select_preferred_periodic_records(records)
    if not selected_records:
        raise ValueError("No metric-relevant periodic filings were found for this company")

    if created_at is None:
        created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    annual_fields: list[PeriodFieldsArtifact] = []
    quarterly_ytd_fields: list[PeriodFieldsArtifact] = []
    source_filings: list[FilingCatalogRecord] = []

    for record in selected_records:
        if not record.local_normalized_path:
            raise ValueError(f"Catalog record {record.accession_number} is missing local_normalized_path")
        filing = load_periodic_report_filing(record.local_normalized_path)
        fields_artifact = build_period_fields_artifact(run_id=run_id, filing=filing, catalog_record=record)
        source_filings.append(record)
        if record.form_family == "10-K":
            annual_fields.append(fields_artifact)
        elif record.form_family == "10-Q":
            quarterly_ytd_fields.append(fields_artifact)

    annual_fields = sorted(annual_fields, key=_artifact_sort_key)
    quarterly_ytd_fields = sorted(quarterly_ytd_fields, key=_artifact_sort_key)
    quarterly_fields = _build_standalone_quarter_history(quarterly_ytd_fields, annual_fields)
    annual_metrics = _compute_annual_metric_history(run_id, annual_fields, created_at)
    quarterly_metrics = _compute_quarterly_metric_history(run_id, quarterly_fields, created_at)

    identity_source = annual_fields[-1] if annual_fields else quarterly_fields[-1]
    return CompanyMetricBuildResult(
        run_id=run_id,
        ticker=identity_source.identity.ticker,
        cik=identity_source.identity.cik,
        company_name=identity_source.identity.company_name,
        created_at=created_at,
        source_catalog_path=source_catalog_path,
        source_filings=sorted(source_filings, key=_record_sort_key),
        annual_fields=annual_fields,
        quarterly_fields=quarterly_fields,
        annual_metrics=annual_metrics,
        quarterly_metrics=quarterly_metrics,
    )


def _build_standalone_quarter_history(
    quarterly_ytd_fields: list[PeriodFieldsArtifact],
    annual_fields: list[PeriodFieldsArtifact],
) -> list[PeriodFieldsArtifact]:
    """Build standalone quarter history.
    
    Args:
        quarterly_ytd_fields: The quarterly_ytd_fields value.
        annual_fields: The annual_fields value.
    
    Returns:
        The computed result.
    """
    quarterly_by_key = {
        (artifact.identity.fiscal_year, artifact.identity.fiscal_quarter): artifact
        for artifact in quarterly_ytd_fields
        if artifact.identity.fiscal_quarter is not None
    }
    standalone: list[PeriodFieldsArtifact] = []

    for artifact in quarterly_ytd_fields:
        quarter = artifact.identity.fiscal_quarter
        if quarter is None:
            continue
        prior_ytd = quarterly_by_key.get((artifact.identity.fiscal_year, quarter - 1)) if quarter in {2, 3} else None
        standalone.append(derive_standalone_quarter_fields(current_artifact=artifact, prior_ytd_artifact=prior_ytd))

    for annual_artifact in annual_fields:
        standalone.append(
            derive_standalone_quarter_fields(
                current_artifact=annual_artifact,
                prior_ytd_artifact=quarterly_by_key.get((annual_artifact.identity.fiscal_year, 3)),
                annual_artifact=annual_artifact,
            )
        )

    return sorted(standalone, key=_artifact_sort_key)


def _compute_annual_metric_history(
    run_id: str,
    annual_fields: list[PeriodFieldsArtifact],
    created_at: str,
) -> list[MetricsBundleArtifact]:
    """Handle compute annual metric history.
    
    Args:
        run_id: The run_id value.
        annual_fields: The annual_fields value.
        created_at: The created_at value.
    
    Returns:
        The computed result.
    """
    bundles: list[MetricsBundleArtifact] = []
    previous_period: PeriodFieldsArtifact | None = None
    for artifact in annual_fields:
        bundles.append(
            compute_metrics_bundle(
                run_id=run_id,
                fields_artifact=artifact,
                comparison=ComparisonContext(previous_period=previous_period, prior_comparable=previous_period),
                created_at=created_at,
            )
        )
        previous_period = artifact
    return bundles


def _compute_quarterly_metric_history(
    run_id: str,
    quarterly_fields: list[PeriodFieldsArtifact],
    created_at: str,
) -> list[MetricsBundleArtifact]:
    """Handle compute quarterly metric history.
    
    Args:
        run_id: The run_id value.
        quarterly_fields: The quarterly_fields value.
        created_at: The created_at value.
    
    Returns:
        The computed result.
    """
    bundles: list[MetricsBundleArtifact] = []
    previous_period: PeriodFieldsArtifact | None = None
    prior_comparable_index: dict[tuple[int, int | None], PeriodFieldsArtifact] = {}

    for artifact in quarterly_fields:
        prior_comparable = prior_comparable_index.get((artifact.identity.fiscal_year - 1, artifact.identity.fiscal_quarter))
        bundles.append(
            compute_metrics_bundle(
                run_id=run_id,
                fields_artifact=artifact,
                comparison=ComparisonContext(previous_period=previous_period, prior_comparable=prior_comparable),
                created_at=created_at,
            )
        )
        previous_period = artifact
        prior_comparable_index[(artifact.identity.fiscal_year, artifact.identity.fiscal_quarter)] = artifact
    return bundles


def _filter_company_records(
    records: list[FilingCatalogRecord],
    ticker: str | None = None,
    cik: str | None = None,
) -> list[FilingCatalogRecord]:
    """Filter company records.
    
    Args:
        records: The records value.
        ticker: The ticker value.
        cik: The cik value.
    
    Returns:
        The computed result.
    """
    filtered = records
    if cik is not None:
        filtered = [record for record in filtered if record.cik == cik]
    if ticker is not None:
        ticker_upper = ticker.upper()
        filtered = [record for record in filtered if _record_ticker(record) == ticker_upper]
    return filtered


def _record_ticker(record: FilingCatalogRecord) -> str | None:
    """Handle record ticker.
    
    Args:
        record: The record value.
    
    Returns:
        The computed result.
    """
    candidate_paths = [record.local_normalized_path, record.local_raw_filing_path, record.local_raw_index_path]
    for path in candidate_paths:
        if not path:
            continue
        parts = PurePosixPath(path.replace('\\', '/')).parts
        if 'ticker' in parts:
            index = parts.index('ticker')
            if index + 1 < len(parts):
                return parts[index + 1].upper()
    return None


def _artifact_sort_key(artifact: PeriodFieldsArtifact) -> tuple[str, int, int, str]:
    """Handle artifact sort key.
    
    Args:
        artifact: The artifact value.
    
    Returns:
        The computed result.
    """
    filing_period = artifact.identity.filing_period or artifact.identity.period_end or ''
    fiscal_quarter = artifact.identity.fiscal_quarter or 0
    primary_accession = artifact.identity.primary_filing_accession or ''
    return (filing_period, artifact.identity.fiscal_year, fiscal_quarter, primary_accession)


def _record_sort_key(record: FilingCatalogRecord) -> tuple[str, str, str, str]:
    """Handle record sort key.
    
    Args:
        record: The record value.
    
    Returns:
        The computed result.
    """
    return (record.report_period or '', record.filing_date, record.form_family, record.accession_number)

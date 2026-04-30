from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from typing import Any

from metric_parser.artifacts import write_company_metric_artifacts
from metric_parser.compute import METRIC_DEFINITIONS
from metric_parser.db import ingest_company_artifact_directories
from metric_parser.ingest import load_catalog_records
from metric_parser.models import MetricRecord
from metric_parser.pipeline import CompanyMetricBuildResult
from metric_parser.pipeline import build_company_metric_history


CONTEXTUAL_METRICS = frozenset(
    {
        "dividend_growth",
        "dividend_payout_ratio",
    }
)

APPROXIMATION_WARNING_CODES = frozenset(
    {
        "annualized_from_quarter",
        "average_balance_unavailable_used_ending_balance",
        "average_invested_capital_unavailable_used_current",
        "average_tangible_capital_unavailable_used_current",
        "capex_proxy_used",
        "cash_offsets_unavailable_using_gross_invested_capital",
        "cash_offsets_unavailable_using_total_debt",
        "maintenance_capex_unavailable",
        "nopat_using_operating_income_pretax",
        "owners_earnings_using_ocf_fallback",
        "partial_cash_offsets_used_in_invested_capital",
        "partial_cash_offsets_used_in_net_debt",
        "partial_tangible_adjustments_used",
        "quarter_share_base_using_ytd_weighted_average",
        "tangible_adjustments_unavailable_used_total_equity",
        "tangible_capital_approximated_as_tangible_equity",
    }
)

VALIDATION_WINDOWS = {
    "annual": 5,
    "quarterly": 4,
}


@dataclass(frozen=True, slots=True)
class ValidationCompanyTarget:
    ticker: str
    catalog_paths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MetricPeriodSignoff:
    period_type: str
    status: str
    company_count: int
    relevant_company_count: int
    latest_applicable_count: int
    mean_coverage_ratio: str
    companies_missing_latest: list[str] = field(default_factory=list)
    dominant_warning_codes: list[str] = field(default_factory=list)
    latest_missing_warning_codes: list[str] = field(default_factory=list)
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MetricSignoffRecord:
    metric_code: str
    metric_name: str
    category: str
    subcategory: str
    overall_status: str
    annual: MetricPeriodSignoff
    quarterly: MetricPeriodSignoff
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_code": self.metric_code,
            "metric_name": self.metric_name,
            "category": self.category,
            "subcategory": self.subcategory,
            "overall_status": self.overall_status,
            "annual": self.annual.to_dict(),
            "quarterly": self.quarterly.to_dict(),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ValidationReport:
    run_id: str
    created_at: str
    cohort: list[ValidationCompanyTarget]
    company_builds: list[CompanyMetricBuildResult]
    output_root: str
    database_path: str
    validation_windows: dict[str, int]
    signoffs: list[MetricSignoffRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "cohort": [item.to_dict() for item in self.cohort],
            "companies": [
                {
                    "ticker": build.ticker,
                    "cik": build.cik,
                    "company_name": build.company_name,
                    "annual_period_count": len(build.annual_metrics),
                    "quarterly_period_count": len(build.quarterly_metrics),
                }
                for build in self.company_builds
            ],
            "output_root": self.output_root,
            "database_path": self.database_path,
            "validation_windows": dict(self.validation_windows),
            "signoffs": [item.to_dict() for item in self.signoffs],
        }


def build_validation_report(
    run_id: str,
    company_targets: list[ValidationCompanyTarget],
    output_root: str | Path,
    created_at: str | None = None,
) -> ValidationReport:
    if created_at is None:
        created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    output_path = Path(output_root)
    output_path.mkdir(parents=True, exist_ok=True)
    db_path = output_path / "metrics.duckdb"

    builds: list[CompanyMetricBuildResult] = []
    artifact_dirs: list[Path] = []
    for target in company_targets:
        records = _load_records_for_target(target)
        build = build_company_metric_history(run_id=f"{run_id}-{target.ticker.lower()}", records=records, created_at=created_at)
        builds.append(build)
        artifact_dir = output_path / target.ticker.lower()
        artifact_dir.mkdir(parents=True, exist_ok=True)
        write_company_metric_artifacts(artifact_dir, build)
        artifact_dirs.append(artifact_dir)

    ingest_company_artifact_directories(db_path, artifact_dirs)
    signoffs = _build_metric_signoffs(builds)
    report = ValidationReport(
        run_id=run_id,
        created_at=created_at,
        cohort=company_targets,
        company_builds=builds,
        output_root=str(output_path),
        database_path=str(db_path),
        validation_windows=dict(VALIDATION_WINDOWS),
        signoffs=signoffs,
    )
    write_validation_report(output_path / "metric_signoff_report.json", report)
    write_validation_markdown(output_path / "metric_signoff_report.md", report)
    return report


def write_validation_report(path: str | Path, report: ValidationReport) -> None:
    Path(path).write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_validation_markdown(path: str | Path, report: ValidationReport) -> None:
    lines: list[str] = []
    lines.append("# Metric Signoff Report")
    lines.append("")
    lines.append(f"- Run ID: `{report.run_id}`")
    lines.append(f"- Created At: `{report.created_at}`")
    lines.append(f"- Cohort: {', '.join(target.ticker for target in report.cohort)}")
    lines.append(f"- DuckDB: `{report.database_path}`")
    lines.append(f"- Windows: annual={report.validation_windows['annual']} quarterly={report.validation_windows['quarterly']}")
    lines.append("")
    lines.append("## Status Legend")
    lines.append("")
    lines.append("- `solid`: broad coverage in the validation cohort and low approximation pressure")
    lines.append("- `usable_with_caveats`: useful, but warning patterns or coverage gaps still matter")
    lines.append("- `needs_refinement`: too much missing data or too little reliable coverage")
    lines.append("- `not_tested`: insufficient applicable history in the current cohort")
    lines.append("")
    lines.append("## Metric Summary")
    lines.append("")
    for signoff in report.signoffs:
        lines.append(f"### {signoff.metric_code}")
        lines.append("")
        lines.append(f"- Overall: `{signoff.overall_status}`")
        lines.append(
            f"- Annual: `{signoff.annual.status}` latest={signoff.annual.latest_applicable_count}/{signoff.annual.relevant_company_count} coverage={signoff.annual.mean_coverage_ratio}"
        )
        lines.append(
            f"- Quarterly: `{signoff.quarterly.status}` latest={signoff.quarterly.latest_applicable_count}/{signoff.quarterly.relevant_company_count} coverage={signoff.quarterly.mean_coverage_ratio}"
        )
        if signoff.notes:
            lines.append(f"- Notes: {'; '.join(signoff.notes)}")
        lines.append("")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_metric_signoffs(builds: list[CompanyMetricBuildResult]) -> list[MetricSignoffRecord]:
    signoffs: list[MetricSignoffRecord] = []
    for definition in METRIC_DEFINITIONS:
        annual = _summarize_metric_period(builds, definition.metric_code, "annual")
        quarterly = _summarize_metric_period(builds, definition.metric_code, "quarterly")
        overall_status = _combine_statuses(annual.status, quarterly.status)
        notes = _collect_signoff_notes(definition.metric_code, annual, quarterly)
        signoffs.append(
            MetricSignoffRecord(
                metric_code=definition.metric_code,
                metric_name=definition.metric_name,
                category=definition.category,
                subcategory=definition.subcategory or "",
                overall_status=overall_status,
                annual=annual,
                quarterly=quarterly,
                notes=notes,
            )
        )
    return signoffs


def _summarize_metric_period(
    builds: list[CompanyMetricBuildResult],
    metric_code: str,
    period_type: str,
) -> MetricPeriodSignoff:
    company_count = len(builds)
    companies_with_histories = 0
    relevant_company_count = 0
    latest_applicable_count = 0
    coverage_ratios: list[float] = []
    companies_missing_latest: list[str] = []
    warning_counter: Counter[str] = Counter()
    latest_missing_warning_counter: Counter[str] = Counter()

    for build in builds:
        bundles = build.annual_metrics if period_type == "annual" else build.quarterly_metrics
        metric_rows = _metric_rows_from_bundles(bundles, metric_code)
        if not metric_rows:
            companies_missing_latest.append(build.ticker)
            continue

        companies_with_histories += 1
        applicable_rows = [row for row in metric_rows if _is_applicable(row)]
        contextual = metric_code in CONTEXTUAL_METRICS
        if contextual and not applicable_rows:
            continue

        relevant_company_count += 1
        coverage_ratios.append(len(applicable_rows) / len(metric_rows))
        for row in applicable_rows:
            warning_counter.update(row.warnings)

        latest_row = metric_rows[-1]
        if _is_applicable(latest_row):
            latest_applicable_count += 1
        else:
            companies_missing_latest.append(build.ticker)
            latest_missing_warning_counter.update(latest_row.warnings)

    mean_coverage = 0.0 if not coverage_ratios else sum(coverage_ratios) / len(coverage_ratios)
    if companies_with_histories == 0:
        return MetricPeriodSignoff(
            period_type=period_type,
            status="not_tested",
            company_count=company_count,
            relevant_company_count=0,
            latest_applicable_count=0,
            mean_coverage_ratio="0.000",
            companies_missing_latest=sorted(companies_missing_latest),
            note=f"no {period_type} histories were included in the current cohort",
        )
    status, note = _assess_period_status(
        metric_code=metric_code,
        relevant_company_count=relevant_company_count,
        latest_applicable_count=latest_applicable_count,
        mean_coverage=mean_coverage,
        warning_counter=warning_counter,
    )
    return MetricPeriodSignoff(
        period_type=period_type,
        status=status,
        company_count=company_count,
        relevant_company_count=relevant_company_count,
        latest_applicable_count=latest_applicable_count,
        mean_coverage_ratio=_ratio_text(mean_coverage),
        companies_missing_latest=sorted(companies_missing_latest),
        dominant_warning_codes=[code for code, _ in warning_counter.most_common(5)],
        latest_missing_warning_codes=[code for code, _ in latest_missing_warning_counter.most_common(5)],
        note=note,
    )


def _metric_rows_from_bundles(bundles: list[Any], metric_code: str) -> list[MetricRecord]:
    rows: list[MetricRecord] = []
    for bundle in bundles:
        for metric in bundle.metrics:
            if metric.metric_code == metric_code:
                rows.append(metric)
    rows.sort(key=lambda item: (item.filing_period, item.fiscal_year, item.fiscal_quarter or 0))
    if not rows:
        return rows
    period_type = rows[-1].period_type
    window = VALIDATION_WINDOWS.get(period_type, len(rows))
    return rows[-window:]


def _is_applicable(metric: MetricRecord) -> bool:
    return metric.applicability == "applicable" and metric.value is not None


def _assess_period_status(
    metric_code: str,
    relevant_company_count: int,
    latest_applicable_count: int,
    mean_coverage: float,
    warning_counter: Counter[str],
) -> tuple[str, str | None]:
    if relevant_company_count == 0:
        if metric_code in CONTEXTUAL_METRICS:
            return "not_tested", "contextual metric with no applicable companies in the current cohort"
        return "needs_refinement", "no applicable company histories in the current cohort"

    latest_ratio = latest_applicable_count / relevant_company_count
    approximation_pressure = any(code in APPROXIMATION_WARNING_CODES for code in warning_counter)

    if latest_ratio >= 0.8 and mean_coverage >= 0.75 and not approximation_pressure:
        return "solid", None
    if latest_ratio >= 0.8 and mean_coverage >= 0.75:
        return "usable_with_caveats", "high coverage, but current implementation relies on approximation warnings"
    if latest_ratio >= 0.5 and mean_coverage >= 0.5:
        return "usable_with_caveats", "moderate coverage in the current cohort"
    return "needs_refinement", "coverage is too limited in the current cohort"


def _combine_statuses(annual_status: str, quarterly_status: str) -> str:
    if annual_status != "not_tested":
        return annual_status
    if quarterly_status != "not_tested":
        return quarterly_status
    return annual_status


def _collect_signoff_notes(
    metric_code: str,
    annual: MetricPeriodSignoff,
    quarterly: MetricPeriodSignoff,
) -> list[str]:
    notes: list[str] = []
    if metric_code in CONTEXTUAL_METRICS:
        notes.append("contextual metric; non-dividend issuers should not be treated as failures")
    if annual.note:
        notes.append(f"annual: {annual.note}")
    if quarterly.note:
        notes.append(f"quarterly: {quarterly.note}")
    if annual.latest_missing_warning_codes:
        notes.append(f"annual latest missing reasons: {', '.join(annual.latest_missing_warning_codes)}")
    if quarterly.latest_missing_warning_codes:
        notes.append(f"quarterly latest missing reasons: {', '.join(quarterly.latest_missing_warning_codes)}")
    return notes


def _ratio_text(value: float) -> str:
    return format(value, ".3f")


def _load_records_for_target(target: ValidationCompanyTarget) -> list[Any]:
    records = []
    for path_text in target.catalog_paths:
        path = Path(path_text)
        records.extend(load_catalog_records(path))
    ticker_lower = target.ticker.lower()
    filtered = [
        record
        for record in records
        if f"ticker/{ticker_lower}/" in (record.local_normalized_path or "").replace("\\", "/").lower()
    ]
    if not filtered:
        raise ValueError(f"No metric-relevant normalized records found for ticker {target.ticker}")
    return filtered

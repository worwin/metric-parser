from __future__ import annotations

import unittest

from metric_parser.compute import METRIC_DEFINITION_BY_CODE
from metric_parser.models import MetricRecord
from metric_parser.models import MetricsBundleArtifact
from metric_parser.models import PeriodArtifactIdentity
from metric_parser.pipeline import CompanyMetricBuildResult
from metric_parser.validation.signoff import _build_metric_signoffs


class ValidationSignoffTests(unittest.TestCase):
    def test_revenue_signoff_marks_clean_metric_as_solid(self) -> None:
        builds = [
            _company_build(
                ticker="AAA",
                annual_rows=[_metric_row("AAA", "annual", 2025, "revenue", "100")],
                quarterly_rows=[_metric_row("AAA", "quarterly", 2025, "revenue", "25", fiscal_quarter=1)],
            ),
            _company_build(
                ticker="BBB",
                annual_rows=[_metric_row("BBB", "annual", 2025, "revenue", "200")],
                quarterly_rows=[_metric_row("BBB", "quarterly", 2025, "revenue", "50", fiscal_quarter=1)],
            ),
        ]

        revenue_signoff = next(item for item in _build_metric_signoffs(builds) if item.metric_code == "revenue")

        self.assertEqual(revenue_signoff.annual.status, "solid")
        self.assertEqual(revenue_signoff.quarterly.status, "solid")
        self.assertEqual(revenue_signoff.overall_status, "solid")

    def test_owners_earnings_signoff_marks_approximation_metric_as_caveated(self) -> None:
        builds = [
            _company_build(
                ticker="AAA",
                annual_rows=[
                    _metric_row(
                        "AAA",
                        "annual",
                        2025,
                        "owners_earnings_approx",
                        "80",
                        warnings=["maintenance_capex_unavailable"],
                    )
                ],
            ),
            _company_build(
                ticker="BBB",
                annual_rows=[
                    _metric_row(
                        "BBB",
                        "annual",
                        2025,
                        "owners_earnings_approx",
                        "90",
                        warnings=["maintenance_capex_unavailable"],
                    )
                ],
            ),
        ]

        signoff = next(item for item in _build_metric_signoffs(builds) if item.metric_code == "owners_earnings_approx")

        self.assertEqual(signoff.annual.status, "usable_with_caveats")
        self.assertEqual(signoff.overall_status, "usable_with_caveats")
        self.assertTrue(any("approximation warnings" in note for note in signoff.notes))

    def test_dividend_growth_signoff_marks_no_applicable_history_as_not_tested(self) -> None:
        builds = [
            _company_build(
                ticker="AAA",
                annual_rows=[
                    _metric_row(
                        "AAA",
                        "annual",
                        2025,
                        "dividend_growth",
                        None,
                        applicability="not_computable",
                        warnings=["missing_prior_comparable"],
                    )
                ],
            ),
            _company_build(
                ticker="BBB",
                annual_rows=[
                    _metric_row(
                        "BBB",
                        "annual",
                        2025,
                        "dividend_growth",
                        None,
                        applicability="not_computable",
                        warnings=["missing_required_source_fact"],
                    )
                ],
            ),
        ]

        signoff = next(item for item in _build_metric_signoffs(builds) if item.metric_code == "dividend_growth")

        self.assertEqual(signoff.annual.status, "not_tested")
        self.assertEqual(signoff.overall_status, "not_tested")


def _company_build(
    ticker: str,
    annual_rows: list[MetricRecord] | None = None,
    quarterly_rows: list[MetricRecord] | None = None,
) -> CompanyMetricBuildResult:
    annual_rows = annual_rows or []
    quarterly_rows = quarterly_rows or []
    annual_bundles = [_bundle(ticker, "annual", annual_rows[0].fiscal_year, annual_rows)] if annual_rows else []
    quarterly_bundles = [
        _bundle(ticker, "quarterly", quarterly_rows[0].fiscal_year, quarterly_rows, fiscal_quarter=quarterly_rows[0].fiscal_quarter)
    ] if quarterly_rows else []
    return CompanyMetricBuildResult(
        run_id=f"run-{ticker.lower()}",
        ticker=ticker,
        cik=f"000{ticker}",
        company_name=f"{ticker} Corp",
        created_at="2026-04-29T12:00:00Z",
        annual_metrics=annual_bundles,
        quarterly_metrics=quarterly_bundles,
    )


def _bundle(
    ticker: str,
    period_type: str,
    fiscal_year: int,
    rows: list[MetricRecord],
    fiscal_quarter: int | None = 4,
) -> MetricsBundleArtifact:
    return MetricsBundleArtifact(
        run_id=f"run-{ticker.lower()}",
        identity=PeriodArtifactIdentity(
            ticker=ticker,
            cik=f"000{ticker}",
            company_name=f"{ticker} Corp",
            filing_period=f"{fiscal_year}-12-31" if period_type == "annual" else f"{fiscal_year}-03-31",
            period_type=period_type,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            period_start=f"{fiscal_year}-01-01",
            period_end=f"{fiscal_year}-12-31" if period_type == "annual" else f"{fiscal_year}-03-31",
            primary_filing_accession=f"{ticker}-{fiscal_year}-{period_type}",
            source_accessions=[f"{ticker}-{fiscal_year}-{period_type}"],
        ),
        metrics=rows,
    )


def _metric_row(
    ticker: str,
    period_type: str,
    fiscal_year: int,
    metric_code: str,
    value: str | None,
    *,
    fiscal_quarter: int | None = 4,
    warnings: list[str] | None = None,
    applicability: str = "applicable",
) -> MetricRecord:
    definition = METRIC_DEFINITION_BY_CODE[metric_code]
    return MetricRecord(
        metric_record_id=f"{ticker}:{period_type}:{fiscal_year}:{fiscal_quarter}:{metric_code}",
        run_id=f"run-{ticker.lower()}",
        ticker=ticker,
        cik=f"000{ticker}",
        company_name=f"{ticker} Corp",
        filing_period=f"{fiscal_year}-12-31" if period_type == "annual" else f"{fiscal_year}-03-31",
        period_start=f"{fiscal_year}-01-01",
        period_end=f"{fiscal_year}-12-31" if period_type == "annual" else f"{fiscal_year}-03-31",
        fiscal_year=fiscal_year,
        fiscal_quarter=fiscal_quarter,
        period_type=period_type,
        metric_name=definition.metric_name,
        metric_code=definition.metric_code,
        category=definition.category,
        subcategory=definition.subcategory,
        value=value,
        value_type=definition.value_type,
        unit=definition.unit,
        formula_id=definition.formula_id,
        formula_version=1,
        formula_text=definition.formula_text,
        confidence="1.00",
        warnings=list(warnings or []),
        applicability=applicability,
        created_at="2026-04-29T12:00:00Z",
    )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from decimal import Decimal
import unittest

from metric_parser.compute import ComparisonContext
from metric_parser.compute import compute_metrics_bundle
from metric_parser.models import CanonicalFieldRecord
from metric_parser.models import MetricSourceFact
from metric_parser.models import PeriodArtifactIdentity
from metric_parser.models import PeriodFieldsArtifact
from metric_parser.quarterization import derive_standalone_quarter_fields
from metric_parser.quarterization import infer_fiscal_quarter_from_filing


class QuarterizationTests(unittest.TestCase):
    def test_infer_fiscal_quarter_from_filing(self) -> None:
        self.assertEqual(infer_fiscal_quarter_from_filing("10-Q", "2026-03-31", "2026-01-01"), 1)
        self.assertEqual(infer_fiscal_quarter_from_filing("10-Q", "2026-06-30", "2026-01-01"), 2)
        self.assertEqual(infer_fiscal_quarter_from_filing("10-Q", "2026-09-30", "2026-01-01"), 3)
        self.assertEqual(infer_fiscal_quarter_from_filing("10-K", "2026-12-31", "2026-01-01"), 4)

    def test_derive_standalone_q2_fields_from_ytd_delta(self) -> None:
        q1 = _quarter_artifact(
            fiscal_year=2026,
            fiscal_quarter=1,
            filing_period="2026-03-31",
            revenue="100",
            gross_profit="60",
            operating_income="20",
            net_income="16",
            operating_cash_flow="30",
            capital_expenditures_proxy="8",
            depreciation_and_amortization="4",
            dividends_common_cash="3",
            weighted_avg_shares_basic="100",
            weighted_avg_shares_diluted="102",
            total_assets="1100",
            total_equity="700",
            current_assets="500",
            current_liabilities="200",
            cash_and_equivalents="100",
            short_term_investments="50",
            accounts_receivable_net="90",
            shares_outstanding_end="100",
            total_debt="200",
        )
        q2_ytd = _quarter_artifact(
            fiscal_year=2026,
            fiscal_quarter=2,
            filing_period="2026-06-30",
            revenue="260",
            gross_profit="150",
            operating_income="55",
            net_income="44",
            operating_cash_flow="75",
            capital_expenditures_proxy="20",
            depreciation_and_amortization="9",
            dividends_common_cash="7",
            weighted_avg_shares_basic="100",
            weighted_avg_shares_diluted="103",
            total_assets="1150",
            total_equity="730",
            current_assets="530",
            current_liabilities="210",
            cash_and_equivalents="120",
            short_term_investments="55",
            accounts_receivable_net="95",
            shares_outstanding_end="99",
            total_debt="210",
        )

        q2 = derive_standalone_quarter_fields(current_artifact=q2_ytd, prior_ytd_artifact=q1)
        field_by_code = {field.field_code: field for field in q2.fields}

        self.assertEqual(q2.quarterization_method, "derived_q2")
        self.assertEqual(field_by_code["revenue"].value, "160")
        self.assertEqual(field_by_code["operating_cash_flow"].value, "45")
        self.assertEqual(field_by_code["capital_expenditures_proxy"].value, "12")
        self.assertIn("quarter_derived_from_current_ytd_minus_q1_ytd", field_by_code["revenue"].warnings)
        self.assertEqual(field_by_code["current_assets"].value, "530")


class MetricComputationTests(unittest.TestCase):
    def test_compute_annual_metrics_bundle(self) -> None:
        current = _annual_artifact(
            fiscal_year=2025,
            filing_period="2025-12-31",
            revenue="1000",
            gross_profit="600",
            operating_income="250",
            net_income="200",
            operating_cash_flow="260",
            capital_expenditures_proxy="60",
            depreciation_and_amortization="30",
            dividends_common_cash="40",
            weighted_avg_shares_basic="102",
            weighted_avg_shares_diluted="104",
            total_assets="1200",
            total_equity="800",
            current_assets="500",
            current_liabilities="250",
            cash_and_equivalents="120",
            short_term_investments="80",
            accounts_receivable_net="90",
            shares_outstanding_end="100",
            total_debt="300",
        )
        prior = _annual_artifact(
            fiscal_year=2024,
            filing_period="2024-12-31",
            revenue="900",
            gross_profit="500",
            operating_income="210",
            net_income="170",
            operating_cash_flow="220",
            capital_expenditures_proxy="55",
            depreciation_and_amortization="28",
            dividends_common_cash="35",
            weighted_avg_shares_basic="108",
            weighted_avg_shares_diluted="110",
            total_assets="1000",
            total_equity="700",
            current_assets="450",
            current_liabilities="230",
            cash_and_equivalents="110",
            short_term_investments="70",
            accounts_receivable_net="85",
            shares_outstanding_end="110",
            total_debt="280",
        )

        bundle = compute_metrics_bundle("run-annual", current, ComparisonContext(prior_comparable=prior, previous_period=prior), created_at="2026-04-02T12:00:00Z")
        metric_by_code = {metric.metric_code: metric for metric in bundle.metrics}

        self.assertEqual(metric_by_code["revenue"].value, "1000")
        self.assertEqual(_q(metric_by_code["gross_margin"].value), Decimal("0.6"))
        self.assertEqual(_q(metric_by_code["free_cash_flow"].value), Decimal("200"))
        self.assertEqual(_q(metric_by_code["current_ratio"].value), Decimal("2"))
        self.assertEqual(_q(metric_by_code["quick_ratio"].value), Decimal("1.16"))
        self.assertEqual(_q(metric_by_code["book_value_per_share"].value), Decimal("8"))
        self.assertEqual(_q(metric_by_code["owners_earnings_approx"].value), Decimal("170"))
        self.assertEqual(metric_by_code["roe"].applicability, "applicable")

    def test_compute_quarterly_metrics_bundle_on_standalone_q2(self) -> None:
        q1 = _quarter_artifact(
            fiscal_year=2026,
            fiscal_quarter=1,
            filing_period="2026-03-31",
            revenue="100",
            gross_profit="60",
            operating_income="20",
            net_income="16",
            operating_cash_flow="30",
            capital_expenditures_proxy="8",
            depreciation_and_amortization="4",
            dividends_common_cash="3",
            weighted_avg_shares_basic="100",
            weighted_avg_shares_diluted="102",
            total_assets="1100",
            total_equity="700",
            current_assets="500",
            current_liabilities="200",
            cash_and_equivalents="100",
            short_term_investments="50",
            accounts_receivable_net="90",
            shares_outstanding_end="100",
            total_debt="200",
        )
        q2_ytd = _quarter_artifact(
            fiscal_year=2026,
            fiscal_quarter=2,
            filing_period="2026-06-30",
            revenue="260",
            gross_profit="150",
            operating_income="55",
            net_income="44",
            operating_cash_flow="75",
            capital_expenditures_proxy="20",
            depreciation_and_amortization="9",
            dividends_common_cash="7",
            weighted_avg_shares_basic="100",
            weighted_avg_shares_diluted="103",
            total_assets="1150",
            total_equity="730",
            current_assets="530",
            current_liabilities="210",
            cash_and_equivalents="120",
            short_term_investments="55",
            accounts_receivable_net="95",
            shares_outstanding_end="99",
            total_debt="210",
        )
        prior_year_q2 = _quarter_artifact(
            fiscal_year=2025,
            fiscal_quarter=2,
            filing_period="2025-06-30",
            revenue="140",
            gross_profit="84",
            operating_income="28",
            net_income="22",
            operating_cash_flow="35",
            capital_expenditures_proxy="10",
            depreciation_and_amortization="5",
            dividends_common_cash="3",
            weighted_avg_shares_basic="104",
            weighted_avg_shares_diluted="106",
            total_assets="1025",
            total_equity="680",
            current_assets="470",
            current_liabilities="190",
            cash_and_equivalents="95",
            short_term_investments="45",
            accounts_receivable_net="80",
            shares_outstanding_end="104",
            total_debt="195",
        )

        q2 = derive_standalone_quarter_fields(current_artifact=q2_ytd, prior_ytd_artifact=q1)
        bundle = compute_metrics_bundle("run-quarter", q2, ComparisonContext(previous_period=q1, prior_comparable=prior_year_q2), created_at="2026-04-02T12:00:00Z")
        metric_by_code = {metric.metric_code: metric for metric in bundle.metrics}

        self.assertEqual(metric_by_code["revenue"].value, "160")
        self.assertEqual(_q(metric_by_code["free_cash_flow"].value), Decimal("33"))
        self.assertEqual(_q(metric_by_code["free_cash_flow_margin"].value), Decimal("0.20625"))
        self.assertEqual(_q(metric_by_code["revenue_growth"].value), (Decimal("160") / Decimal("140")) - Decimal("1"))
        self.assertIn("annualized_from_quarter", metric_by_code["roe"].warnings)
        self.assertEqual(metric_by_code["roe"].applicability, "applicable")


def _annual_artifact(**values: str) -> PeriodFieldsArtifact:
    return PeriodFieldsArtifact(
        run_id="fixture",
        identity=PeriodArtifactIdentity(
            ticker="ACME",
            cik="0000001",
            company_name="Acme Corp",
            filing_period=values.pop("filing_period"),
            period_type="annual",
            fiscal_year=values.pop("fiscal_year"),
            fiscal_quarter=4,
            period_start="2025-01-01",
            period_end="2025-12-31",
            primary_filing_accession="acc-annual",
            source_accessions=["acc-annual"],
        ),
        fields=[_field(code, value) for code, value in values.items()],
    )


def _quarter_artifact(**values: str) -> PeriodFieldsArtifact:
    fiscal_year = values.pop("fiscal_year")
    fiscal_quarter = values.pop("fiscal_quarter")
    filing_period = values.pop("filing_period")
    return PeriodFieldsArtifact(
        run_id="fixture",
        identity=PeriodArtifactIdentity(
            ticker="ACME",
            cik="0000001",
            company_name="Acme Corp",
            filing_period=filing_period,
            period_type="quarterly",
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
            period_start="2026-01-01" if fiscal_quarter > 1 else "2026-01-01",
            period_end=filing_period,
            primary_filing_accession=f"acc-q{fiscal_quarter}",
            source_accessions=[f"acc-q{fiscal_quarter}"],
        ),
        fields=[_field(code, value) for code, value in values.items()],
    )


def _field(code: str, value: str) -> CanonicalFieldRecord:
    value_type = "count" if "shares" in code else "currency"
    unit = "shares" if value_type == "count" else "usd"
    return CanonicalFieldRecord(
        field_code=code,
        field_name=code,
        value=value,
        unit=unit,
        value_type=value_type,
        selection_method="fixture",
        confidence="1.00",
        source_facts=[MetricSourceFact(role="fixture", source_accession="fixture", source_form="10-K", concept_local_name=code)],
    )


def _q(value: str | None) -> Decimal:
    assert value is not None
    return Decimal(value)


if __name__ == "__main__":
    unittest.main()

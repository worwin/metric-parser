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
            income_before_tax="18",
            income_tax_expense="3",
            interest_expense="-4",
            operating_cash_flow="30",
            capital_expenditures_proxy="8",
            depreciation_and_amortization="4",
            dividends_common_cash="3",
            weighted_avg_shares_basic="100",
            weighted_avg_shares_diluted="102",
            total_assets="1100",
            total_equity="700",
            retained_earnings="420",
            current_assets="500",
            current_liabilities="200",
            cash_and_equivalents="100",
            short_term_investments="50",
            accounts_receivable_net="90",
            goodwill="45",
            intangible_assets_excluding_goodwill="25",
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
            income_before_tax="50",
            income_tax_expense="8",
            interest_expense="-10",
            operating_cash_flow="75",
            capital_expenditures_proxy="20",
            depreciation_and_amortization="9",
            dividends_common_cash="7",
            weighted_avg_shares_basic="100",
            weighted_avg_shares_diluted="103",
            total_assets="1150",
            total_equity="730",
            retained_earnings="455",
            current_assets="530",
            current_liabilities="210",
            cash_and_equivalents="120",
            short_term_investments="55",
            accounts_receivable_net="95",
            goodwill="46",
            intangible_assets_excluding_goodwill="26",
            shares_outstanding_end="99",
            total_debt="210",
        )

        q2 = derive_standalone_quarter_fields(current_artifact=q2_ytd, prior_ytd_artifact=q1)
        field_by_code = {field.field_code: field for field in q2.fields}

        self.assertEqual(q2.quarterization_method, "derived_q2")
        self.assertEqual(field_by_code["revenue"].value, "160")
        self.assertEqual(field_by_code["operating_cash_flow"].value, "45")
        self.assertEqual(field_by_code["capital_expenditures_proxy"].value, "12")
        self.assertEqual(field_by_code["interest_expense"].value, "-6")
        self.assertEqual(field_by_code["income_tax_expense"].value, "5")
        self.assertEqual(field_by_code["weighted_avg_shares_diluted"].value, "103")
        self.assertIn("quarter_share_base_using_ytd_weighted_average", field_by_code["weighted_avg_shares_diluted"].warnings)
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
            income_before_tax="240",
            income_tax_expense="40",
            interest_expense="-20",
            selling_general_and_administrative="120",
            research_and_development="80",
            operating_expenses="200",
            other_income_expense="5",
            operating_cash_flow="260",
            cash_from_investing="-70",
            cash_from_financing="-20",
            net_change_in_cash="170",
            capital_expenditures_proxy="60",
            depreciation_and_amortization="30",
            dividends_common_cash="40",
            share_repurchases="50",
            stock_issuance="10",
            debt_issuance="70",
            debt_repayment="40",
            weighted_avg_shares_basic="102",
            weighted_avg_shares_diluted="104",
            total_assets="1200",
            total_liabilities="400",
            total_equity="800",
            retained_earnings="500",
            current_assets="500",
            current_liabilities="250",
            inventory="140",
            cash_and_equivalents="120",
            short_term_investments="80",
            accounts_receivable_net="90",
            property_plant_equipment="300",
            goodwill="50",
            intangible_assets_excluding_goodwill="30",
            treasury_stock="-100",
            shares_outstanding_end="100",
            debt_noncurrent="240",
            total_debt="300",
        )
        prior = _annual_artifact(
            fiscal_year=2024,
            filing_period="2024-12-31",
            revenue="900",
            gross_profit="500",
            operating_income="210",
            net_income="170",
            income_before_tax="205",
            income_tax_expense="35",
            interest_expense="-18",
            selling_general_and_administrative="110",
            research_and_development="70",
            operating_expenses="180",
            other_income_expense="4",
            operating_cash_flow="220",
            cash_from_investing="-60",
            cash_from_financing="-15",
            net_change_in_cash="145",
            capital_expenditures_proxy="55",
            depreciation_and_amortization="28",
            dividends_common_cash="35",
            share_repurchases="45",
            stock_issuance="12",
            debt_issuance="65",
            debt_repayment="35",
            weighted_avg_shares_basic="108",
            weighted_avg_shares_diluted="110",
            total_assets="1000",
            total_liabilities="300",
            total_equity="700",
            retained_earnings="400",
            current_assets="450",
            current_liabilities="230",
            inventory="125",
            cash_and_equivalents="110",
            short_term_investments="70",
            accounts_receivable_net="85",
            property_plant_equipment="280",
            goodwill="55",
            intangible_assets_excluding_goodwill="35",
            treasury_stock="-80",
            shares_outstanding_end="110",
            debt_noncurrent="230",
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
        self.assertEqual(_q(metric_by_code["tangible_book_value_per_share"].value), Decimal("7.2"))
        self.assertEqual(_q(metric_by_code["owners_earnings_approx"].value), Decimal("170"))
        self.assertEqual(_q(metric_by_code["operating_expenses_to_gross_profit"].value), Decimal("0.3333333333333333333333333333"))
        self.assertEqual(_q(metric_by_code["sga_to_gross_profit"].value), Decimal("0.2"))
        self.assertEqual(_q(metric_by_code["r_and_d_to_gross_profit"].value), Decimal("0.1333333333333333333333333333"))
        self.assertEqual(_q(metric_by_code["depreciation_to_gross_profit"].value), Decimal("0.05"))
        self.assertEqual(_q(metric_by_code["interest_expense_to_operating_income"].value), Decimal("0.08"))
        self.assertEqual(_q(metric_by_code["tax_rate_effective"].value), Decimal("0.1666666666666666666666666667"))
        self.assertEqual(_q(metric_by_code["capex_to_net_income"].value), Decimal("0.3"))
        self.assertEqual(_q(metric_by_code["roic"].value), Decimal("0.2450980392156862745098039215"))
        self.assertEqual(_q(metric_by_code["cash_conversion_ocf_to_net_income"].value), Decimal("1.3"))
        self.assertEqual(_q(metric_by_code["cash_conversion_fcf_to_net_income"].value), Decimal("1"))
        self.assertEqual(_q(metric_by_code["free_cash_flow_growth"].value), Decimal("0.212121212121212121212121212"))
        self.assertEqual(_q(metric_by_code["net_income_growth"].value), Decimal("0.176470588235294117647058824"))
        self.assertEqual(_q(metric_by_code["eps_basic"].value), Decimal("1.960784313725490196078431373"))
        self.assertEqual(_q(metric_by_code["eps_diluted"].value), Decimal("1.923076923076923076923076923"))
        self.assertEqual(_q(metric_by_code["eps_growth"].value), Decimal("0.244343891402714932126696833"))
        self.assertEqual(_q(metric_by_code["net_debt"].value), Decimal("100"))
        self.assertEqual(_q(metric_by_code["net_debt_to_fcf"].value), Decimal("0.5"))
        self.assertEqual(_q(metric_by_code["debt_payback_years"].value), Decimal("1.5"))
        self.assertEqual(_q(metric_by_code["debt_to_equity"].value), Decimal("0.375"))
        self.assertEqual(_q(metric_by_code["adjusted_debt_to_equity"].value), Decimal("0.3333333333333333333333333333"))
        self.assertEqual(_q(metric_by_code["years_to_pay_long_term_debt"].value), Decimal("1.2"))
        self.assertEqual(_q(metric_by_code["intangibles_to_assets"].value), Decimal("0.06666666666666666666666666667"))
        self.assertEqual(_q(metric_by_code["ppe_to_assets"].value), Decimal("0.25"))
        self.assertEqual(_q(metric_by_code["ppe_to_net_income"].value), Decimal("1.5"))
        self.assertEqual(_q(metric_by_code["debt_to_ppe"].value), Decimal("1"))
        self.assertEqual(_q(metric_by_code["receivables_to_revenue"].value), Decimal("0.09"))
        self.assertEqual(_q(metric_by_code["inventory_growth"].value), Decimal("0.12"))
        self.assertEqual(_q(metric_by_code["goodwill_growth"].value), Decimal("-0.0909090909090909090909090909"))
        self.assertEqual(_q(metric_by_code["net_stock_issuance_or_retirement"].value), Decimal("-40"))
        self.assertEqual(_q(metric_by_code["net_debt_issuance_or_retirement"].value), Decimal("30"))
        self.assertEqual(_q(metric_by_code["retained_earnings_growth"].value), Decimal("0.25"))
        self.assertEqual(_q(metric_by_code["return_on_tangible_capital"].value), Decimal("0.3759398496240601503759398496"))
        self.assertEqual(_q(metric_by_code["dividend_growth"].value), Decimal("0.142857142857142857142857143"))
        self.assertEqual(_q(metric_by_code["interest_coverage"].value), Decimal("12.5"))
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
            income_before_tax="18",
            income_tax_expense="3",
            interest_expense="-4",
            operating_cash_flow="30",
            capital_expenditures_proxy="8",
            depreciation_and_amortization="4",
            dividends_common_cash="3",
            weighted_avg_shares_basic="100",
            weighted_avg_shares_diluted="102",
            total_assets="1100",
            total_equity="700",
            retained_earnings="420",
            current_assets="500",
            current_liabilities="200",
            cash_and_equivalents="100",
            short_term_investments="50",
            accounts_receivable_net="90",
            goodwill="45",
            intangible_assets_excluding_goodwill="25",
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
            income_before_tax="50",
            income_tax_expense="8",
            interest_expense="-10",
            operating_cash_flow="75",
            capital_expenditures_proxy="20",
            depreciation_and_amortization="9",
            dividends_common_cash="7",
            weighted_avg_shares_basic="100",
            weighted_avg_shares_diluted="103",
            total_assets="1150",
            total_equity="730",
            retained_earnings="455",
            current_assets="530",
            current_liabilities="210",
            cash_and_equivalents="120",
            short_term_investments="55",
            accounts_receivable_net="95",
            goodwill="46",
            intangible_assets_excluding_goodwill="26",
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
            income_before_tax="26",
            income_tax_expense="4",
            interest_expense="-5",
            operating_cash_flow="35",
            capital_expenditures_proxy="10",
            depreciation_and_amortization="5",
            dividends_common_cash="3",
            weighted_avg_shares_basic="104",
            weighted_avg_shares_diluted="106",
            total_assets="1025",
            total_equity="680",
            retained_earnings="390",
            current_assets="470",
            current_liabilities="190",
            cash_and_equivalents="95",
            short_term_investments="45",
            accounts_receivable_net="80",
            goodwill="44",
            intangible_assets_excluding_goodwill="24",
            shares_outstanding_end="104",
            total_debt="195",
        )

        q2 = derive_standalone_quarter_fields(current_artifact=q2_ytd, prior_ytd_artifact=q1)
        bundle = compute_metrics_bundle("run-quarter", q2, ComparisonContext(previous_period=q1, prior_comparable=prior_year_q2), created_at="2026-04-02T12:00:00Z")
        metric_by_code = {metric.metric_code: metric for metric in bundle.metrics}

        self.assertEqual(metric_by_code["revenue"].value, "160")
        self.assertEqual(_q(metric_by_code["free_cash_flow"].value), Decimal("33"))
        self.assertEqual(_q(metric_by_code["free_cash_flow_growth"].value), Decimal("0.32"))
        self.assertEqual(_q(metric_by_code["free_cash_flow_margin"].value), Decimal("0.20625"))
        self.assertEqual(_q(metric_by_code["revenue_growth"].value), (Decimal("160") / Decimal("140")) - Decimal("1"))
        self.assertEqual(_q(metric_by_code["net_income_growth"].value), Decimal("0.272727272727272727272727273"))
        self.assertEqual(_q(metric_by_code["cash_conversion_ocf_to_net_income"].value), Decimal("1.607142857142857142857142857"))
        self.assertEqual(_q(metric_by_code["eps_basic"].value), Decimal("0.28"))
        self.assertEqual(_q(metric_by_code["eps_diluted"].value), Decimal("0.2718446601941747572815533981"))
        self.assertEqual(_q(metric_by_code["eps_growth"].value), Decimal("0.309796999117387466902030009"))
        self.assertEqual(_q(metric_by_code["net_debt"].value), Decimal("35"))
        self.assertEqual(_q(metric_by_code["dividend_growth"].value), Decimal("0.333333333333333333333333333"))
        self.assertEqual(_q(metric_by_code["interest_coverage"].value), Decimal("5.833333333333333333333333333"))
        self.assertIn("annualized_from_quarter", metric_by_code["roe"].warnings)
        self.assertIn("annualized_from_quarter", metric_by_code["roic"].warnings)
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

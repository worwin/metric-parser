from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation

from metric_parser.compute.definitions import METRIC_DEFINITION_BY_CODE
from metric_parser.compute.definitions import MetricDefinition
from metric_parser.models import CanonicalFieldRecord
from metric_parser.models import MetricRecord
from metric_parser.models import MetricSourceFact
from metric_parser.models import MetricWarningRecord
from metric_parser.models import MetricsBundleArtifact
from metric_parser.models import PeriodFieldsArtifact


@dataclass(frozen=True, slots=True)
class ComparisonContext:
    previous_period: PeriodFieldsArtifact | None = None
    prior_comparable: PeriodFieldsArtifact | None = None


def compute_metrics_bundle(
    run_id: str,
    fields_artifact: PeriodFieldsArtifact,
    comparison: ComparisonContext | None = None,
    created_at: str | None = None,
) -> MetricsBundleArtifact:
    if comparison is None:
        comparison = ComparisonContext()
    if created_at is None:
        created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    field_map = {field.field_code: field for field in fields_artifact.fields}
    previous_field_map = _field_map(comparison.previous_period)
    prior_comparable_map = _field_map(comparison.prior_comparable)

    metric_records: list[MetricRecord] = []
    warning_records: list[MetricWarningRecord] = []

    for metric_code in METRIC_DEFINITION_BY_CODE:
        record = _compute_metric_record(
            run_id=run_id,
            fields_artifact=fields_artifact,
            field_map=field_map,
            previous_field_map=previous_field_map,
            prior_comparable_map=prior_comparable_map,
            metric_code=metric_code,
            created_at=created_at,
        )
        metric_records.append(record)
        for warning_code in record.warnings:
            warning_records.append(
                MetricWarningRecord(
                    warning_id=f"{record.metric_record_id}:{warning_code}",
                    metric_record_id=record.metric_record_id,
                    cik=record.cik,
                    ticker=record.ticker,
                    filing_period=record.filing_period,
                    fiscal_year=record.fiscal_year,
                    fiscal_quarter=record.fiscal_quarter,
                    period_type=record.period_type,
                    metric_code=record.metric_code,
                    warning_code=warning_code,
                    severity="warning",
                    warning_source="formula",
                    message=warning_code.replace("_", " "),
                    created_at=created_at,
                )
            )

    return MetricsBundleArtifact(
        run_id=run_id,
        identity=fields_artifact.identity,
        schema_version=fields_artifact.schema_version,
        parser_warnings_inherited=list(fields_artifact.parser_warnings_inherited),
        metrics=metric_records,
        warnings=warning_records,
    )


def _compute_metric_record(
    run_id: str,
    fields_artifact: PeriodFieldsArtifact,
    field_map: dict[str, CanonicalFieldRecord],
    previous_field_map: dict[str, CanonicalFieldRecord],
    prior_comparable_map: dict[str, CanonicalFieldRecord],
    metric_code: str,
    created_at: str,
) -> MetricRecord:
    definition = METRIC_DEFINITION_BY_CODE[metric_code]
    warnings: list[str] = []
    source_fields: list[CanonicalFieldRecord] = []
    value: str | None = None
    applicability = "applicable"

    if metric_code == "revenue":
        value, source_fields, warnings = _field_value_result(field_map, "revenue")
    elif metric_code == "revenue_growth":
        value, source_fields, warnings = _growth_result(field_map.get("revenue"), prior_comparable_map.get("revenue"))
    elif metric_code == "gross_margin":
        gross_profit = field_map.get("gross_profit")
        revenue = field_map.get("revenue")
        if gross_profit is None and revenue is not None and field_map.get("cost_of_revenue") is not None:
            value, warnings = _ratio_from_values(_subtract(field_map["revenue"].value, field_map["cost_of_revenue"].value), revenue.value)
            source_fields = [field_map["revenue"], field_map["cost_of_revenue"]]
            warnings.extend(["gross_margin_derived_from_cost_of_revenue"])
        else:
            value, warnings = _ratio_result(gross_profit, revenue)
            source_fields = _used_fields(gross_profit, revenue)
    elif metric_code == "operating_margin":
        value, warnings = _ratio_result(field_map.get("operating_income"), field_map.get("revenue"))
        source_fields = _used_fields(field_map.get("operating_income"), field_map.get("revenue"))
    elif metric_code == "net_margin":
        value, warnings = _ratio_result(field_map.get("net_income"), field_map.get("revenue"))
        source_fields = _used_fields(field_map.get("net_income"), field_map.get("revenue"))
    elif metric_code == "roe":
        value, source_fields, warnings = _return_metric_result(fields_artifact, field_map, previous_field_map, "net_income", "total_equity")
    elif metric_code == "roa":
        value, source_fields, warnings = _return_metric_result(fields_artifact, field_map, previous_field_map, "net_income", "total_assets")
    elif metric_code == "roic":
        value, source_fields, warnings = _roic_result(fields_artifact, field_map, previous_field_map)
    elif metric_code == "operating_cash_flow":
        value, source_fields, warnings = _field_value_result(field_map, "operating_cash_flow")
    elif metric_code == "free_cash_flow":
        value, source_fields, warnings = _difference_result(field_map.get("operating_cash_flow"), field_map.get("capital_expenditures_proxy"))
    elif metric_code == "free_cash_flow_margin":
        fcf_value, fcf_fields, fcf_warnings = _difference_result(field_map.get("operating_cash_flow"), field_map.get("capital_expenditures_proxy"))
        value, warnings = _ratio_from_values(fcf_value, _field_value(field_map.get("revenue")))
        source_fields = fcf_fields + _used_fields(field_map.get("revenue"))
        warnings = fcf_warnings + warnings
    elif metric_code == "cash_conversion_ocf_to_net_income":
        value, warnings = _ratio_result(field_map.get("operating_cash_flow"), field_map.get("net_income"))
        source_fields = _used_fields(field_map.get("operating_cash_flow"), field_map.get("net_income"))
    elif metric_code == "cash_conversion_fcf_to_net_income":
        fcf_value, fcf_fields, fcf_warnings = _difference_result(field_map.get("operating_cash_flow"), field_map.get("capital_expenditures_proxy"))
        value, warnings = _ratio_from_values(fcf_value, _field_value(field_map.get("net_income")))
        source_fields = fcf_fields + _used_fields(field_map.get("net_income"))
        warnings = fcf_warnings + warnings
    elif metric_code == "free_cash_flow_per_share":
        fcf_value, fcf_fields, fcf_warnings = _difference_result(field_map.get("operating_cash_flow"), field_map.get("capital_expenditures_proxy"))
        share_field, share_warnings = _share_base_field(field_map)
        value, warnings = _ratio_from_values(fcf_value, _field_value(share_field))
        source_fields = fcf_fields + _used_fields(share_field)
        warnings = fcf_warnings + share_warnings + warnings
    elif metric_code == "operating_cash_flow_per_share":
        share_field, share_warnings = _share_base_field(field_map)
        value, warnings = _ratio_result(field_map.get("operating_cash_flow"), share_field)
        source_fields = _used_fields(field_map.get("operating_cash_flow"), share_field)
        warnings = share_warnings + warnings
    elif metric_code == "book_value_per_share":
        share_field, share_warnings = _ending_share_field(field_map)
        value, warnings = _ratio_result(field_map.get("total_equity"), share_field)
        source_fields = _used_fields(field_map.get("total_equity"), share_field)
        warnings = share_warnings + warnings
    elif metric_code == "book_value_per_share_growth":
        current_bvps, current_fields, current_warnings = _book_value_per_share_components(field_map)
        prior_bvps, prior_fields, prior_warnings = _book_value_per_share_components(prior_comparable_map)
        value, warnings = _growth_from_values(current_bvps, prior_bvps)
        source_fields = current_fields + prior_fields
        warnings = current_warnings + prior_warnings + warnings
    elif metric_code == "tangible_book_value_per_share":
        current_tbvps, current_fields, current_warnings = _tangible_book_value_per_share_components(field_map)
        value = current_tbvps
        source_fields = current_fields
        warnings = current_warnings
    elif metric_code == "retained_earnings_growth":
        value, source_fields, warnings = _growth_result(field_map.get("retained_earnings"), prior_comparable_map.get("retained_earnings"))
    elif metric_code == "debt_to_capital":
        total_debt = field_map.get("total_debt")
        total_equity = field_map.get("total_equity")
        denominator = _sum_values(_field_value(total_debt), _field_value(total_equity))
        value, warnings = _ratio_from_values(_field_value(total_debt), denominator)
        source_fields = _used_fields(total_debt, total_equity)
    elif metric_code == "financial_leverage":
        avg_assets, asset_warnings, asset_fields = _average_balance(field_map.get("total_assets"), previous_field_map.get("total_assets"))
        avg_equity, equity_warnings, equity_fields = _average_balance(field_map.get("total_equity"), previous_field_map.get("total_equity"))
        value, warnings = _ratio_from_values(avg_assets, avg_equity)
        source_fields = asset_fields + equity_fields
        warnings = asset_warnings + equity_warnings + warnings
    elif metric_code == "net_debt":
        value, source_fields, warnings = _net_debt_result(field_map)
    elif metric_code == "net_debt_to_fcf":
        net_debt_value, net_debt_fields, net_debt_warnings = _net_debt_result(field_map)
        fcf_value, fcf_fields, fcf_warnings = _difference_result(field_map.get("operating_cash_flow"), field_map.get("capital_expenditures_proxy"))
        value, warnings = _ratio_from_values(net_debt_value, fcf_value)
        source_fields = net_debt_fields + fcf_fields
        warnings = net_debt_warnings + fcf_warnings + warnings
    elif metric_code == "debt_payback_years":
        fcf_value, fcf_fields, fcf_warnings = _difference_result(field_map.get("operating_cash_flow"), field_map.get("capital_expenditures_proxy"))
        value, warnings = _ratio_from_values(_field_value(field_map.get("total_debt")), fcf_value)
        source_fields = _used_fields(field_map.get("total_debt")) + fcf_fields
        warnings = fcf_warnings + warnings
    elif metric_code == "return_on_tangible_capital":
        value, source_fields, warnings = _return_on_tangible_capital_result(fields_artifact, field_map, previous_field_map)
    elif metric_code == "current_ratio":
        value, warnings = _ratio_result(field_map.get("current_assets"), field_map.get("current_liabilities"))
        source_fields = _used_fields(field_map.get("current_assets"), field_map.get("current_liabilities"))
    elif metric_code == "quick_ratio":
        quick_assets = _sum_values(_field_value(field_map.get("cash_and_equivalents")), _field_value(field_map.get("short_term_investments")), _field_value(field_map.get("accounts_receivable_net")))
        value, warnings = _ratio_from_values(quick_assets, _field_value(field_map.get("current_liabilities")))
        source_fields = _used_fields(field_map.get("cash_and_equivalents"), field_map.get("short_term_investments"), field_map.get("accounts_receivable_net"), field_map.get("current_liabilities"))
    elif metric_code == "share_count_trend":
        value, source_fields, warnings = _growth_result(field_map.get("shares_outstanding_end"), prior_comparable_map.get("shares_outstanding_end"))
    elif metric_code == "dividend_payout_ratio":
        value, warnings = _ratio_result(field_map.get("dividends_common_cash"), field_map.get("net_income"))
        source_fields = _used_fields(field_map.get("dividends_common_cash"), field_map.get("net_income"))
    elif metric_code == "interest_coverage":
        value, source_fields, warnings = _interest_coverage_result(field_map)
    elif metric_code == "owners_earnings_approx":
        net_income = field_map.get("net_income")
        depreciation = field_map.get("depreciation_and_amortization")
        capex = field_map.get("capital_expenditures_proxy")
        if net_income is not None and depreciation is not None and capex is not None:
            value = _sum_values(_field_value(net_income), _field_value(depreciation))
            value = _subtract(value, _field_value(capex))
            warnings = ["maintenance_capex_unavailable"]
            source_fields = _used_fields(net_income, depreciation, capex)
        else:
            value, source_fields, warnings = _difference_result(field_map.get("operating_cash_flow"), field_map.get("capital_expenditures_proxy"))
            warnings = warnings + ["maintenance_capex_unavailable", "owners_earnings_using_ocf_fallback"]
    else:
        warnings = ["metric_not_implemented"]
        applicability = "not_computable"

    if value is None and applicability == "applicable":
        applicability = "not_computable"
    if value is None and not warnings:
        warnings = ["missing_required_source_fact"]

    warnings = _unique_warnings(warnings)
    source_facts = _merge_source_facts(source_fields)
    confidence = _confidence_from_warnings(warnings)
    metric_record_id = _metric_record_id(fields_artifact, metric_code)
    return MetricRecord(
        metric_record_id=metric_record_id,
        run_id=run_id,
        ticker=fields_artifact.identity.ticker,
        cik=fields_artifact.identity.cik,
        company_name=fields_artifact.identity.company_name,
        filing_period=fields_artifact.identity.filing_period,
        period_start=fields_artifact.identity.period_start,
        period_end=fields_artifact.identity.period_end,
        fiscal_year=fields_artifact.identity.fiscal_year,
        fiscal_quarter=fields_artifact.identity.fiscal_quarter,
        period_type=fields_artifact.identity.period_type,
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
        source_facts=source_facts,
        source_accessions=sorted({fact.source_accession for fact in source_facts}),
        confidence=confidence,
        warnings=warnings,
        parser_warning_inherited=bool(fields_artifact.parser_warnings_inherited),
        applicability=applicability,
        primary_filing_accession=fields_artifact.identity.primary_filing_accession,
        created_at=created_at,
    )


def _field_map(artifact: PeriodFieldsArtifact | None) -> dict[str, CanonicalFieldRecord]:
    if artifact is None:
        return {}
    return {field.field_code: field for field in artifact.fields}


def _field_value_result(field_map: dict[str, CanonicalFieldRecord], field_code: str) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    field = field_map.get(field_code)
    if field is None or field.value is None:
        return None, [], ["missing_required_source_fact"]
    return field.value, [field], list(field.warnings)


def _ratio_result(numerator: CanonicalFieldRecord | None, denominator: CanonicalFieldRecord | None) -> tuple[str | None, list[str]]:
    return _ratio_from_values(_field_value(numerator), _field_value(denominator))


def _ratio_from_values(numerator: str | None, denominator: str | None) -> tuple[str | None, list[str]]:
    if numerator is None or denominator is None:
        return None, ["missing_required_source_fact"]
    try:
        denominator_decimal = Decimal(denominator)
        numerator_decimal = Decimal(numerator)
    except InvalidOperation:
        return None, ["non_numeric_source_fact"]
    if denominator_decimal == 0:
        return None, ["negative_or_zero_denominator"]
    value = numerator_decimal / denominator_decimal
    return _decimal_text(value), []


def _difference_result(minuend: CanonicalFieldRecord | None, subtrahend: CanonicalFieldRecord | None) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    if minuend is None or subtrahend is None or minuend.value is None or subtrahend.value is None:
        return None, _used_fields(minuend, subtrahend), ["missing_required_source_fact"]
    return _subtract(minuend.value, subtrahend.value), _used_fields(minuend, subtrahend), list(minuend.warnings) + list(subtrahend.warnings)


def _growth_result(current: CanonicalFieldRecord | None, prior: CanonicalFieldRecord | None) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    value, warnings = _growth_from_values(_field_value(current), _field_value(prior))
    return value, _used_fields(current, prior), warnings


def _growth_from_values(current: str | None, prior: str | None) -> tuple[str | None, list[str]]:
    if current is None or prior is None:
        return None, ["missing_prior_comparable"]
    try:
        prior_decimal = Decimal(prior)
        current_decimal = Decimal(current)
    except InvalidOperation:
        return None, ["non_numeric_source_fact"]
    if prior_decimal == 0:
        return None, ["negative_or_zero_denominator"]
    return _decimal_text((current_decimal / prior_decimal) - Decimal("1")), []


def _return_metric_result(
    fields_artifact: PeriodFieldsArtifact,
    field_map: dict[str, CanonicalFieldRecord],
    previous_field_map: dict[str, CanonicalFieldRecord],
    income_code: str,
    balance_code: str,
) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    income_field = field_map.get(income_code)
    annualization_warnings: list[str] = []
    income_value = _field_value(income_field)
    if income_value is None:
        return None, _used_fields(income_field), ["missing_required_source_fact"]
    if fields_artifact.identity.period_type == "quarterly":
        income_value = _annualize_quarter_value(income_value)
        annualization_warnings.append("annualized_from_quarter")
    avg_balance, balance_warnings, balance_fields = _average_balance(field_map.get(balance_code), previous_field_map.get(balance_code))
    value, warnings = _ratio_from_values(income_value, avg_balance)
    return value, _used_fields(income_field) + balance_fields, annualization_warnings + balance_warnings + warnings


def _roic_result(
    fields_artifact: PeriodFieldsArtifact,
    field_map: dict[str, CanonicalFieldRecord],
    previous_field_map: dict[str, CanonicalFieldRecord],
) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    operating_income = field_map.get("operating_income")
    operating_income_value = _field_value(operating_income)
    if operating_income_value is None:
        return None, _used_fields(operating_income), ["missing_required_source_fact"]

    annualization_warnings: list[str] = []
    if fields_artifact.identity.period_type == "quarterly":
        operating_income_value = _annualize_quarter_value(operating_income_value)
        annualization_warnings.append("annualized_from_quarter")

    tax_rate_value, tax_fields, tax_warnings = _effective_tax_rate(field_map)
    nopat_value = operating_income_value
    if tax_rate_value is None:
        tax_warnings.append("nopat_using_operating_income_pretax")
    else:
        nopat_value = _multiply_values(operating_income_value, _subtract("1", tax_rate_value))

    current_invested_capital, current_fields, current_warnings = _invested_capital_value(field_map)
    previous_invested_capital, previous_fields, previous_warnings = _invested_capital_value(previous_field_map)
    average_invested_capital, average_warnings = _average_value(
        current_invested_capital,
        previous_invested_capital,
        "average_invested_capital_unavailable_used_current",
    )
    value, warnings = _ratio_from_values(nopat_value, average_invested_capital)
    source_fields = _used_fields(operating_income) + tax_fields + current_fields + previous_fields
    return value, source_fields, annualization_warnings + tax_warnings + current_warnings + previous_warnings + average_warnings + warnings


def _return_on_tangible_capital_result(
    fields_artifact: PeriodFieldsArtifact,
    field_map: dict[str, CanonicalFieldRecord],
    previous_field_map: dict[str, CanonicalFieldRecord],
) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    operating_income = field_map.get("operating_income")
    operating_income_value = _field_value(operating_income)
    if operating_income_value is None:
        return None, _used_fields(operating_income), ["missing_required_source_fact"]

    annualization_warnings: list[str] = []
    if fields_artifact.identity.period_type == "quarterly":
        operating_income_value = _annualize_quarter_value(operating_income_value)
        annualization_warnings.append("annualized_from_quarter")

    current_tangible_capital, current_fields, current_warnings = _tangible_capital_value(field_map)
    previous_tangible_capital, previous_fields, previous_warnings = _tangible_capital_value(previous_field_map)
    average_tangible_capital, average_warnings = _average_value(
        current_tangible_capital,
        previous_tangible_capital,
        "average_tangible_capital_unavailable_used_current",
    )
    value, warnings = _ratio_from_values(operating_income_value, average_tangible_capital)
    source_fields = _used_fields(operating_income) + current_fields + previous_fields
    return value, source_fields, annualization_warnings + current_warnings + previous_warnings + average_warnings + warnings


def _interest_coverage_result(field_map: dict[str, CanonicalFieldRecord]) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    operating_income = field_map.get("operating_income")
    interest_expense = field_map.get("interest_expense")
    interest_value = _field_value(interest_expense)
    warnings: list[str] = []
    if interest_value is None:
        return None, _used_fields(operating_income, interest_expense), ["missing_required_source_fact"]

    try:
        interest_decimal = Decimal(interest_value)
    except InvalidOperation:
        return None, _used_fields(operating_income, interest_expense), ["non_numeric_source_fact"]
    if interest_decimal < 0:
        warnings.append("interest_expense_absolute_value_used")
        interest_value = _decimal_text(abs(interest_decimal))
    value, ratio_warnings = _ratio_from_values(_field_value(operating_income), interest_value)
    return value, _used_fields(operating_income, interest_expense), list(interest_expense.warnings if interest_expense is not None else []) + warnings + ratio_warnings


def _average_balance(current: CanonicalFieldRecord | None, previous: CanonicalFieldRecord | None) -> tuple[str | None, list[str], list[CanonicalFieldRecord]]:
    current_value = _field_value(current)
    previous_value = _field_value(previous)
    if current_value is None:
        return None, ["missing_required_source_fact"], _used_fields(current)
    if previous_value is None:
        return current_value, ["average_balance_unavailable_used_ending_balance"], _used_fields(current)
    try:
        average = (Decimal(current_value) + Decimal(previous_value)) / Decimal("2")
    except InvalidOperation:
        return current_value, ["non_numeric_source_fact"], _used_fields(current, previous)
    return _decimal_text(average), [], _used_fields(current, previous)


def _share_base_field(field_map: dict[str, CanonicalFieldRecord]) -> tuple[CanonicalFieldRecord | None, list[str]]:
    diluted = field_map.get("weighted_avg_shares_diluted")
    if diluted is not None and diluted.value is not None:
        return diluted, []
    basic = field_map.get("weighted_avg_shares_basic")
    if basic is not None and basic.value is not None:
        return basic, ["share_count_fallback_to_weighted_average_basic"]
    ending = field_map.get("shares_outstanding_end")
    if ending is not None and ending.value is not None:
        return ending, ["share_count_fallback_to_ending_shares"]
    return None, ["shares_outstanding_missing"]


def _ending_share_field(field_map: dict[str, CanonicalFieldRecord]) -> tuple[CanonicalFieldRecord | None, list[str]]:
    ending = field_map.get("shares_outstanding_end")
    if ending is not None and ending.value is not None:
        return ending, []
    basic = field_map.get("weighted_avg_shares_basic")
    if basic is not None and basic.value is not None:
        return basic, ["share_count_fallback_to_weighted_average"]
    diluted = field_map.get("weighted_avg_shares_diluted")
    if diluted is not None and diluted.value is not None:
        return diluted, ["share_count_fallback_to_weighted_average"]
    return None, ["shares_outstanding_missing"]


def _book_value_per_share_components(field_map: dict[str, CanonicalFieldRecord]) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    share_field, share_warnings = _ending_share_field(field_map)
    value, warnings = _ratio_result(field_map.get("total_equity"), share_field)
    return value, _used_fields(field_map.get("total_equity"), share_field), share_warnings + warnings


def _tangible_book_value_per_share_components(field_map: dict[str, CanonicalFieldRecord]) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    share_field, share_warnings = _ending_share_field(field_map)
    tangible_capital, tangible_fields, tangible_warnings = _tangible_capital_value(field_map)
    value, warnings = _ratio_from_values(tangible_capital, _field_value(share_field))
    return value, tangible_fields + _used_fields(share_field), tangible_warnings + share_warnings + warnings


def _effective_tax_rate(field_map: dict[str, CanonicalFieldRecord]) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    income_before_tax = field_map.get("income_before_tax")
    income_tax_expense = field_map.get("income_tax_expense")
    pretax_value = _field_value(income_before_tax)
    tax_value = _field_value(income_tax_expense)
    source_fields = _used_fields(income_before_tax, income_tax_expense)
    if pretax_value is None or tax_value is None:
        return None, source_fields, ["effective_tax_rate_unavailable"]

    try:
        pretax_decimal = Decimal(pretax_value)
        tax_decimal = Decimal(tax_value)
    except InvalidOperation:
        return None, source_fields, ["non_numeric_source_fact"]
    if pretax_decimal <= 0:
        return None, source_fields, ["non_positive_pretax_income"]

    rate = tax_decimal / pretax_decimal
    if rate < 0 or rate > 1:
        return None, source_fields, ["effective_tax_rate_out_of_range"]
    return _decimal_text(rate), source_fields, []


def _invested_capital_value(field_map: dict[str, CanonicalFieldRecord]) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    total_equity = field_map.get("total_equity")
    total_debt = field_map.get("total_debt")
    cash_and_equivalents = field_map.get("cash_and_equivalents")
    short_term_investments = field_map.get("short_term_investments")
    source_fields = _used_fields(total_equity, total_debt, cash_and_equivalents, short_term_investments)

    equity_value = _field_value(total_equity)
    debt_value = _field_value(total_debt)
    if equity_value is None or debt_value is None:
        return None, source_fields, ["missing_required_source_fact"]

    base_value = _sum_values(equity_value, debt_value)
    offset_warnings: list[str] = []
    cash_offsets = [field for field in (cash_and_equivalents, short_term_investments) if field is not None and field.value is not None]
    if not cash_offsets:
        offset_warnings.append("cash_offsets_unavailable_using_gross_invested_capital")
        return base_value, source_fields, offset_warnings

    if cash_and_equivalents is None or cash_and_equivalents.value is None or short_term_investments is None or short_term_investments.value is None:
        offset_warnings.append("partial_cash_offsets_used_in_invested_capital")
    total_offsets = _sum_values(_field_value(cash_and_equivalents), _field_value(short_term_investments))
    return _subtract(base_value, total_offsets), source_fields, offset_warnings


def _net_debt_result(field_map: dict[str, CanonicalFieldRecord]) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    total_debt = field_map.get("total_debt")
    cash_and_equivalents = field_map.get("cash_and_equivalents")
    short_term_investments = field_map.get("short_term_investments")
    source_fields = _used_fields(total_debt, cash_and_equivalents, short_term_investments)
    debt_value = _field_value(total_debt)
    if debt_value is None:
        return None, source_fields, ["missing_required_source_fact"]

    available_offsets = [field for field in (cash_and_equivalents, short_term_investments) if field is not None and field.value is not None]
    if not available_offsets:
        return debt_value, source_fields, ["cash_offsets_unavailable_using_total_debt"]

    warnings: list[str] = []
    if cash_and_equivalents is None or cash_and_equivalents.value is None or short_term_investments is None or short_term_investments.value is None:
        warnings.append("partial_cash_offsets_used_in_net_debt")
    offset_value = _sum_values(_field_value(cash_and_equivalents), _field_value(short_term_investments))
    return _subtract(debt_value, offset_value), source_fields, warnings


def _tangible_capital_value(field_map: dict[str, CanonicalFieldRecord]) -> tuple[str | None, list[CanonicalFieldRecord], list[str]]:
    total_equity = field_map.get("total_equity")
    goodwill = field_map.get("goodwill")
    intangible_assets = field_map.get("intangible_assets_excluding_goodwill")
    source_fields = _used_fields(total_equity, goodwill, intangible_assets)
    equity_value = _field_value(total_equity)
    if equity_value is None:
        return None, source_fields, ["missing_required_source_fact"]

    warnings = ["tangible_capital_approximated_as_tangible_equity"]
    available_adjustments = [field for field in (goodwill, intangible_assets) if field is not None and field.value is not None]
    if not available_adjustments:
        warnings.append("tangible_adjustments_unavailable_used_total_equity")
        return equity_value, source_fields, warnings

    if goodwill is None or goodwill.value is None or intangible_assets is None or intangible_assets.value is None:
        warnings.append("partial_tangible_adjustments_used")
    adjustment_value = _sum_values(_field_value(goodwill), _field_value(intangible_assets))
    return _subtract(equity_value, adjustment_value), source_fields, warnings


def _average_value(current: str | None, previous: str | None, fallback_warning: str) -> tuple[str | None, list[str]]:
    if current is None:
        return None, ["missing_required_source_fact"]
    if previous is None:
        return current, [fallback_warning]
    try:
        average = (Decimal(current) + Decimal(previous)) / Decimal("2")
    except InvalidOperation:
        return current, ["non_numeric_source_fact"]
    return _decimal_text(average), []


def _used_fields(*fields: CanonicalFieldRecord | None) -> list[CanonicalFieldRecord]:
    return [field for field in fields if field is not None]


def _merge_source_facts(fields: list[CanonicalFieldRecord]) -> list[MetricSourceFact]:
    source_facts: list[MetricSourceFact] = []
    seen: set[tuple[str, str, str | None, str | None]] = set()
    for field in fields:
        for source_fact in field.source_facts:
            key = (source_fact.source_accession, source_fact.concept_local_name, source_fact.context_id, source_fact.role)
            if key in seen:
                continue
            seen.add(key)
            source_facts.append(source_fact)
    return source_facts


def _metric_record_id(fields_artifact: PeriodFieldsArtifact, metric_code: str) -> str:
    quarter = fields_artifact.identity.fiscal_quarter if fields_artifact.identity.fiscal_quarter is not None else "A"
    return f"{fields_artifact.identity.ticker}:{fields_artifact.identity.period_type}:{fields_artifact.identity.fiscal_year}:{quarter}:{metric_code}"


def _field_value(field: CanonicalFieldRecord | None) -> str | None:
    if field is None:
        return None
    return field.value


def _subtract(left: str | None, right: str | None) -> str | None:
    if left is None or right is None:
        return None
    try:
        result = Decimal(left) - Decimal(right)
    except InvalidOperation:
        return None
    return _decimal_text(result)


def _multiply_values(left: str | None, right: str | None) -> str | None:
    if left is None or right is None:
        return None
    try:
        result = Decimal(left) * Decimal(right)
    except InvalidOperation:
        return None
    return _decimal_text(result)


def _sum_values(*values: str | None) -> str | None:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    try:
        total = sum(Decimal(value) for value in usable)
    except InvalidOperation:
        return None
    return _decimal_text(total)


def _annualize_quarter_value(value: str) -> str:
    return _decimal_text(Decimal(value) * Decimal("4"))


def _decimal_text(value: Decimal) -> str:
    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))
    return format(value.normalize(), "f")


def _confidence_from_warnings(warnings: list[str]) -> str:
    if not warnings:
        return "1.00"
    if any(code in warnings for code in ["missing_required_source_fact", "missing_prior_comparable", "negative_or_zero_denominator"]):
        return "0.25"
    if len(warnings) >= 2:
        return "0.50"
    return "0.75"



def _unique_warnings(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for warning in warnings:
        if warning in seen:
            continue
        seen.add(warning)
        ordered.append(warning)
    return ordered



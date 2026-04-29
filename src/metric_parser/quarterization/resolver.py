from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal

from metric_parser.models import CanonicalFieldRecord
from metric_parser.models import MetricSourceFact
from metric_parser.models import PeriodArtifactIdentity
from metric_parser.models import PeriodFieldsArtifact


FLOW_FIELD_CODES = frozenset(
    {
        "revenue",
        "gross_profit",
        "cost_of_revenue",
        "operating_income",
        "net_income",
        "income_before_tax",
        "income_tax_expense",
        "interest_expense",
        "operating_cash_flow",
        "capital_expenditures_proxy",
        "depreciation_and_amortization",
        "dividends_common_cash",
    }
)

INSTANT_FIELD_CODES = frozenset(
    {
        "total_assets",
        "total_equity",
        "retained_earnings",
        "current_assets",
        "current_liabilities",
        "cash_and_equivalents",
        "short_term_investments",
        "accounts_receivable_net",
        "goodwill",
        "intangible_assets_excluding_goodwill",
        "shares_outstanding_end",
        "debt_current",
        "debt_noncurrent",
        "total_debt",
    }
)

NON_DELTA_CURRENT_FIELD_CODES = frozenset(
    {
        "weighted_avg_shares_basic",
        "weighted_avg_shares_diluted",
    }
)


def infer_fiscal_quarter_from_filing(form: str, report_period: str | None, period_start: str | None) -> int | None:
    form_upper = form.upper()
    if form_upper.startswith("10-K"):
        return 4
    if not form_upper.startswith("10-Q") or not report_period or not period_start:
        return None

    duration = _duration_days(period_start, report_period)
    if duration < 0:
        return None
    if duration <= 110:
        return 1
    if duration <= 210:
        return 2
    return 3


def derive_standalone_quarter_fields(
    current_artifact: PeriodFieldsArtifact,
    prior_ytd_artifact: PeriodFieldsArtifact | None = None,
    annual_artifact: PeriodFieldsArtifact | None = None,
) -> PeriodFieldsArtifact:
    quarter = current_artifact.identity.fiscal_quarter
    if quarter is None:
        raise ValueError("Current artifact is missing fiscal_quarter")
    if quarter == 1 and current_artifact.identity.period_type == "quarterly":
        return PeriodFieldsArtifact(
            run_id=current_artifact.run_id,
            identity=current_artifact.identity,
            schema_version=current_artifact.schema_version,
            parser_warnings_inherited=list(current_artifact.parser_warnings_inherited),
            quarterization_method="direct_quarter",
            fields=list(current_artifact.fields),
        )

    current_by_code = {field.field_code: field for field in current_artifact.fields}
    prior_by_code = {field.field_code: field for field in prior_ytd_artifact.fields} if prior_ytd_artifact is not None else {}
    annual_by_code = {field.field_code: field for field in annual_artifact.fields} if annual_artifact is not None else {}

    derived_fields: list[CanonicalFieldRecord] = []
    all_codes = {field.field_code for field in current_artifact.fields}
    all_codes.update(prior_by_code)
    all_codes.update(annual_by_code)

    for code in sorted(all_codes):
        if code in INSTANT_FIELD_CODES:
            source_field = current_by_code.get(code) or annual_by_code.get(code)
            if source_field is not None:
                derived_fields.append(source_field)
            continue

        if code in NON_DELTA_CURRENT_FIELD_CODES:
            source_field = current_by_code.get(code) or annual_by_code.get(code)
            if source_field is not None:
                derived_fields.append(_mark_current_period_proxy(source_field, quarter))
            continue

        if code not in FLOW_FIELD_CODES:
            source_field = current_by_code.get(code) or annual_by_code.get(code)
            if source_field is not None:
                derived_fields.append(source_field)
            continue

        if quarter in {2, 3}:
            derived_fields.append(_delta_field(code, current_by_code.get(code), prior_by_code.get(code), f"current_ytd_minus_q{quarter - 1}_ytd"))
            continue

        if quarter == 4:
            derived_fields.append(_delta_field(code, annual_by_code.get(code), prior_by_code.get(code), "annual_minus_q3_ytd"))
            continue

    identity = PeriodArtifactIdentity(
        ticker=current_artifact.identity.ticker,
        cik=current_artifact.identity.cik,
        company_name=current_artifact.identity.company_name,
        filing_period=current_artifact.identity.filing_period,
        period_type="quarterly",
        fiscal_year=current_artifact.identity.fiscal_year,
        fiscal_quarter=quarter,
        period_start=current_artifact.identity.period_start,
        period_end=current_artifact.identity.period_end,
        primary_filing_accession=current_artifact.identity.primary_filing_accession,
        source_accessions=list(current_artifact.identity.source_accessions),
    )
    method = "direct_quarter" if quarter == 1 else f"derived_q{quarter}"
    return PeriodFieldsArtifact(
        run_id=current_artifact.run_id,
        identity=identity,
        schema_version=current_artifact.schema_version,
        parser_warnings_inherited=list(current_artifact.parser_warnings_inherited),
        quarterization_method=method,
        fields=derived_fields,
    )


def _delta_field(
    field_code: str,
    current_field: CanonicalFieldRecord | None,
    prior_field: CanonicalFieldRecord | None,
    method: str,
) -> CanonicalFieldRecord:
    if current_field is None:
        return CanonicalFieldRecord(
            field_code=field_code,
            field_name=field_code,
            value=None,
            unit=None,
            value_type="unknown",
            selection_method=method,
            confidence="0.00",
            warnings=["missing_required_source_fact"],
            source_facts=[],
        )
    if prior_field is None or current_field.value is None or prior_field.value is None:
        return CanonicalFieldRecord(
            field_code=current_field.field_code,
            field_name=current_field.field_name,
            value=None,
            unit=current_field.unit,
            value_type=current_field.value_type,
            selection_method=method,
            confidence="0.25",
            warnings=["missing_prior_comparable"],
            source_facts=current_field.source_facts,
        )

    current_value = Decimal(current_field.value)
    prior_value = Decimal(prior_field.value)
    delta_value = current_value - prior_value
    value_text = str(delta_value.quantize(Decimal("1"))) if delta_value == delta_value.to_integral() else format(delta_value.normalize(), "f")
    warnings = [f"quarter_derived_from_{method}"]
    source_facts = [replace(source, role="current_ytd") for source in current_field.source_facts]
    source_facts.extend(replace(source, role="prior_ytd") for source in prior_field.source_facts)
    return CanonicalFieldRecord(
        field_code=current_field.field_code,
        field_name=current_field.field_name,
        value=value_text,
        unit=current_field.unit,
        value_type=current_field.value_type,
        selection_method=method,
        confidence="0.75",
        warnings=warnings,
        source_facts=source_facts,
    )


def _mark_current_period_proxy(field: CanonicalFieldRecord, quarter: int) -> CanonicalFieldRecord:
    if quarter <= 1:
        return field
    warnings = list(field.warnings)
    warnings.append("quarter_share_base_using_ytd_weighted_average")
    return CanonicalFieldRecord(
        field_code=field.field_code,
        field_name=field.field_name,
        value=field.value,
        unit=field.unit,
        value_type=field.value_type,
        selection_method=field.selection_method,
        confidence=field.confidence,
        warnings=warnings,
        source_facts=list(field.source_facts),
    )


def _duration_days(period_start: str | None, period_end: str | None) -> int:
    if not period_start or not period_end:
        return -1
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end)
    return (end - start).days

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import PurePosixPath

from metric_parser.ingest.edgar_models import FilingCatalogRecord
from metric_parser.ingest.edgar_models import PeriodicReportFactRecord
from metric_parser.ingest.edgar_models import PeriodicReportParsedFiling
from metric_parser.mapping.registry import FIELD_DEFINITIONS
from metric_parser.mapping.registry import FIELD_DEFINITION_BY_CODE
from metric_parser.mapping.registry import FieldDefinition
from metric_parser.models import CanonicalFieldRecord
from metric_parser.models import MetricSourceFact
from metric_parser.models import PeriodArtifactIdentity
from metric_parser.models import PeriodFieldsArtifact
from metric_parser.quarterization import infer_fiscal_quarter_from_filing


DOCUMENT_FISCAL_YEAR_FOCUS = 'DocumentFiscalYearFocus'
DOCUMENT_FISCAL_PERIOD_FOCUS = 'DocumentFiscalPeriodFocus'


def select_canonical_fields(filing: PeriodicReportParsedFiling) -> list[CanonicalFieldRecord]:
    selected: list[CanonicalFieldRecord] = []
    by_code: dict[str, CanonicalFieldRecord] = {}

    for definition in FIELD_DEFINITIONS:
        field_record = _select_direct_field(definition, filing)
        if field_record is not None:
            selected.append(field_record)
            by_code[field_record.field_code] = field_record

    derived_total_debt = _derive_total_debt(by_code)
    if derived_total_debt is not None and 'total_debt' not in by_code:
        selected.append(derived_total_debt)

    return selected


def build_period_fields_artifact(
    run_id: str,
    filing: PeriodicReportParsedFiling,
    catalog_record: FilingCatalogRecord | None = None,
) -> PeriodFieldsArtifact:
    parser_warning_codes = []
    if filing.validation is not None:
        parser_warning_codes = [warning.code for warning in filing.validation.warnings]

    company_name = catalog_record.company_name if catalog_record is not None else (filing.cik or 'UNKNOWN')
    period_start = _resolve_period_start(filing)
    identity = PeriodArtifactIdentity(
        ticker=_resolve_ticker(filing, catalog_record),
        cik=filing.cik,
        company_name=company_name,
        filing_period=filing.report_period or filing.filing_date,
        period_type=_period_type_from_form(filing.form),
        fiscal_year=_fiscal_year_from_filing(filing),
        fiscal_quarter=_fiscal_quarter_from_filing(filing, period_start),
        period_start=period_start,
        period_end=filing.report_period,
        primary_filing_accession=filing.accession_number,
        source_accessions=[filing.accession_number],
    )

    return PeriodFieldsArtifact(
        run_id=run_id,
        identity=identity,
        parser_warnings_inherited=parser_warning_codes,
        fields=select_canonical_fields(filing),
    )


def _select_direct_field(definition: FieldDefinition, filing: PeriodicReportParsedFiling) -> CanonicalFieldRecord | None:
    for alias in definition.concept_aliases:
        candidates = [
            fact
            for fact in filing.facts
            if fact.concept_local_name == alias.concept_local_name and _fact_numeric_value(fact) is not None
        ]
        if not candidates:
            continue
        chosen = max(candidates, key=lambda fact: _fact_preference_key(fact, filing, definition))
        value = _fact_numeric_value(chosen)
        if value is None:
            continue
        warnings = list(alias.warnings)
        source_fact = _metric_source_fact('primary', chosen, definition.field_code)
        return CanonicalFieldRecord(
            field_code=definition.field_code,
            field_name=definition.field_name,
            value=value,
            unit=_normalize_unit(chosen.unit, definition.value_type),
            value_type=definition.value_type,
            selection_method=f'concept_alias:{alias.concept_local_name}',
            confidence='1.00' if not warnings else '0.75',
            warnings=warnings,
            source_facts=[source_fact],
        )
    return None


def _derive_total_debt(selected_fields: dict[str, CanonicalFieldRecord]) -> CanonicalFieldRecord | None:
    direct = selected_fields.get('total_debt')
    if direct is not None:
        return direct

    parts = [selected_fields.get('debt_current'), selected_fields.get('debt_noncurrent')]
    usable = [part for part in parts if part is not None and part.value is not None]
    if not usable:
        return None

    total = sum(Decimal(part.value or '0') for part in usable)
    warnings = ['debt_components_aggregated']
    if len(usable) == 1:
        warnings.append('partial_debt_components_used')

    source_facts: list[MetricSourceFact] = []
    for part in usable:
        source_facts.extend(
            replace(source_fact, role=f'component:{part.field_code}', mapped_field_code='total_debt')
            for source_fact in part.source_facts
        )

    total_text = str(total.quantize(Decimal('1'))) if total == total.to_integral() else format(total.normalize(), 'f')
    return CanonicalFieldRecord(
        field_code='total_debt',
        field_name=FIELD_DEFINITION_BY_CODE['total_debt'].field_name,
        value=total_text,
        unit=usable[0].unit,
        value_type='currency',
        selection_method='derived_sum:debt_current+debt_noncurrent',
        confidence='0.75' if len(usable) == 2 else '0.50',
        warnings=warnings,
        source_facts=source_facts,
    )


def _fact_preference_key(
    fact: PeriodicReportFactRecord,
    filing: PeriodicReportParsedFiling,
    definition: FieldDefinition,
) -> tuple[int, int, int, int, str]:
    report_period = filing.report_period
    period_match = int(
        (definition.period_kind == 'duration' and fact.period_end == report_period)
        or (definition.period_kind == 'instant' and fact.instant == report_period)
    )
    no_dimensions = int(not fact.dimensions)
    statement_hint_match = int(definition.statement_hint is None or fact.statement_hint == definition.statement_hint)
    duration_days = _duration_days(fact.period_start, fact.period_end) if definition.period_kind == 'duration' else 0
    temporal_marker = fact.instant or fact.period_end or ''
    return (period_match, no_dimensions, statement_hint_match, duration_days, temporal_marker)


def _resolve_ticker(filing: PeriodicReportParsedFiling, catalog_record: FilingCatalogRecord | None) -> str:
    ticker_from_facts = next((fact.ticker_workspace for fact in filing.facts if fact.ticker_workspace), None)
    if ticker_from_facts:
        return ticker_from_facts.upper()

    candidate_paths: list[str] = []
    if catalog_record is not None:
        if catalog_record.local_normalized_path:
            candidate_paths.append(catalog_record.local_normalized_path)
        if catalog_record.local_raw_filing_path:
            candidate_paths.append(catalog_record.local_raw_filing_path)
    candidate_paths.append(filing.source_path)

    for path in candidate_paths:
        parts = PurePosixPath(path.replace('\\', '/')).parts
        if 'ticker' in parts:
            index = parts.index('ticker')
            if index + 1 < len(parts):
                return parts[index + 1].upper()
    return filing.cik


def _resolve_period_start(filing: PeriodicReportParsedFiling) -> str | None:
    duration_candidates = [
        fact
        for fact in filing.facts
        if fact.period_start and fact.period_end == filing.report_period and not fact.dimensions and _fact_numeric_value(fact) is not None
    ]
    if not duration_candidates:
        return None
    chosen = max(duration_candidates, key=lambda fact: _duration_days(fact.period_start, fact.period_end))
    return chosen.period_start


def _period_type_from_form(form: str) -> str:
    return 'annual' if form.upper().startswith('10-K') else 'quarterly'


def _fiscal_year_from_filing(filing: PeriodicReportParsedFiling) -> int:
    document_fiscal_year = _document_fiscal_year_focus(filing)
    if document_fiscal_year is not None:
        return document_fiscal_year
    return _fiscal_year_from_report_period(filing.report_period or filing.filing_date)


def _fiscal_quarter_from_filing(filing: PeriodicReportParsedFiling, period_start: str | None) -> int | None:
    document_period_focus = _document_fiscal_period_focus(filing)
    if document_period_focus == 'Q1':
        return 1
    if document_period_focus == 'Q2':
        return 2
    if document_period_focus == 'Q3':
        return 3
    if document_period_focus == 'FY':
        return 4
    return infer_fiscal_quarter_from_filing(filing.form, filing.report_period, period_start)


def _document_fiscal_year_focus(filing: PeriodicReportParsedFiling) -> int | None:
    for fact in filing.facts:
        if fact.concept_local_name != DOCUMENT_FISCAL_YEAR_FOCUS:
            continue
        if fact.value is None:
            continue
        try:
            return int(fact.value.strip())
        except ValueError:
            continue
    return None


def _document_fiscal_period_focus(filing: PeriodicReportParsedFiling) -> str | None:
    for fact in filing.facts:
        if fact.concept_local_name != DOCUMENT_FISCAL_PERIOD_FOCUS:
            continue
        if fact.value is None:
            continue
        value = fact.value.strip().upper()
        if value:
            return value
    return None


def _fiscal_year_from_report_period(report_period: str) -> int:
    return date.fromisoformat(report_period).year


def _metric_source_fact(role: str, fact: PeriodicReportFactRecord, mapped_field_code: str) -> MetricSourceFact:
    return MetricSourceFact(
        role=role,
        source_accession=fact.accession_number,
        source_form=fact.form,
        concept_local_name=fact.concept_local_name,
        concept_qname=fact.concept_qname,
        context_id=fact.context_id,
        period_start=fact.period_start,
        period_end=fact.period_end,
        instant=fact.instant,
        unit=fact.unit,
        raw_value=fact.value,
        source_path=fact.source_path,
        mapped_field_code=mapped_field_code,
    )


def _normalize_unit(unit: str | None, value_type: str) -> str | None:
    if value_type == 'currency':
        return 'usd' if unit and 'USD' in unit.upper() else unit
    if value_type == 'count':
        return 'shares' if unit and 'SHARE' in unit.upper() else unit
    return unit


def _coerce_numeric_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text or text == '--':
        return None
    negative = text.startswith('(') and text.endswith(')')
    if negative:
        text = text[1:-1]
    text = text.replace(',', '').replace('$', '').strip()
    if text.startswith('+'):
        text = text[1:]
    try:
        number = Decimal(text)
    except Exception:
        return None
    if negative:
        number = -number
    if number == number.to_integral():
        return str(number.quantize(Decimal('1')))
    return format(number.normalize(), 'f')


def _fact_numeric_value(fact: PeriodicReportFactRecord) -> str | None:
    normalized = _coerce_numeric_text(fact.normalized_value)
    if normalized is not None:
        return normalized
    return _coerce_numeric_text(fact.value)


def _duration_days(period_start: str | None, period_end: str | None) -> int:
    if not period_start or not period_end:
        return -1
    start = date.fromisoformat(period_start)
    end = date.fromisoformat(period_end)
    return (end - start).days

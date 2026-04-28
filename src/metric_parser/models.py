from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any


SCHEMA_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class PeriodArtifactIdentity:
    ticker: str
    cik: str
    company_name: str
    filing_period: str
    period_type: str
    fiscal_year: int
    fiscal_quarter: int | None
    period_start: str | None = None
    period_end: str | None = None
    primary_filing_accession: str | None = None
    source_accessions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MetricSourceFact:
    role: str
    source_accession: str
    source_form: str
    concept_local_name: str
    concept_qname: str | None = None
    context_id: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    instant: str | None = None
    unit: str | None = None
    raw_value: str | None = None
    source_path: str | None = None
    mapped_field_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CanonicalFieldRecord:
    field_code: str
    field_name: str
    value: str | None
    unit: str | None
    value_type: str
    selection_method: str
    confidence: str
    warnings: list[str] = field(default_factory=list)
    source_facts: list[MetricSourceFact] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_facts"] = [fact.to_dict() for fact in self.source_facts]
        return data


@dataclass(frozen=True, slots=True)
class MetricRecord:
    metric_record_id: str
    run_id: str
    ticker: str
    cik: str
    company_name: str
    filing_period: str
    period_start: str | None
    period_end: str | None
    fiscal_year: int
    fiscal_quarter: int | None
    period_type: str
    metric_name: str
    metric_code: str
    category: str
    subcategory: str | None
    value: str | None
    value_type: str
    unit: str | None
    formula_id: str
    formula_version: int
    formula_text: str
    source_facts: list[MetricSourceFact] = field(default_factory=list)
    source_accessions: list[str] = field(default_factory=list)
    confidence: str = "1.00"
    warnings: list[str] = field(default_factory=list)
    parser_warning_inherited: bool = False
    applicability: str = "applicable"
    primary_filing_accession: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_facts"] = [fact.to_dict() for fact in self.source_facts]
        return data


@dataclass(frozen=True, slots=True)
class MetricWarningRecord:
    warning_id: str
    metric_record_id: str | None
    cik: str
    ticker: str
    filing_period: str
    fiscal_year: int
    fiscal_quarter: int | None
    period_type: str
    metric_code: str | None
    warning_code: str
    severity: str
    warning_source: str
    message: str
    source_accession: str | None = None
    upstream_warning_code: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PeriodFieldsArtifact:
    run_id: str
    identity: PeriodArtifactIdentity
    schema_version: str = SCHEMA_VERSION
    parser_warnings_inherited: list[str] = field(default_factory=list)
    quarterization_method: str | None = None
    fields: list[CanonicalFieldRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            **self.identity.to_dict(),
            "parser_warnings_inherited": list(self.parser_warnings_inherited),
            "quarterization_method": self.quarterization_method,
            "fields": [item.to_dict() for item in self.fields],
        }


@dataclass(frozen=True, slots=True)
class MetricsBundleArtifact:
    run_id: str
    identity: PeriodArtifactIdentity
    schema_version: str = SCHEMA_VERSION
    parser_warnings_inherited: list[str] = field(default_factory=list)
    metrics: list[MetricRecord] = field(default_factory=list)
    warnings: list[MetricWarningRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            **self.identity.to_dict(),
            "parser_warnings_inherited": list(self.parser_warnings_inherited),
            "metrics": [item.to_dict() for item in self.metrics],
            "warnings": [item.to_dict() for item in self.warnings],
        }


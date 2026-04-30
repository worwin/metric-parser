from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


METRIC_RELEVANT_PERIODIC_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})


@dataclass(frozen=True, slots=True)
class EdgarValidationIssue:
    code: str
    message: str
    severity: str = "warning"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EdgarValidationIssue":
        return cls(
            code=str(data.get("code") or ""),
            message=str(data.get("message") or ""),
            severity=str(data.get("severity") or "warning"),
        )


@dataclass(frozen=True, slots=True)
class EdgarValidationSummary:
    accession_number: str
    filing_date: str
    form: str
    parser_format: str
    validation_status: str
    warnings: list[EdgarValidationIssue] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EdgarValidationSummary | None":
        if data is None:
            return None
        return cls(
            accession_number=str(data.get("accession_number") or ""),
            filing_date=str(data.get("filing_date") or ""),
            form=str(data.get("form") or ""),
            parser_format=str(data.get("parser_format") or ""),
            validation_status=str(data.get("validation_status") or "unchecked"),
            warnings=[EdgarValidationIssue.from_dict(item) for item in data.get("warnings", [])],
        )


@dataclass(frozen=True, slots=True)
class FilingCatalogRecord:
    accession_number: str
    cik: str
    company_name: str
    form: str
    filing_date: str
    report_period: str | None
    parser_family: str
    validation_status: str
    schema_version: str | None = None
    sec_filing_url: str | None = None
    sec_primary_document_url: str | None = None
    local_raw_filing_path: str | None = None
    local_raw_index_path: str | None = None
    local_normalized_path: str | None = None
    raw_sha256: str | None = None
    parser_format: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FilingCatalogRecord":
        return cls(
            accession_number=str(data.get("accession_number") or ""),
            cik=str(data.get("cik") or ""),
            company_name=str(data.get("company_name") or ""),
            form=str(data.get("form") or ""),
            filing_date=str(data.get("filing_date") or ""),
            report_period=data.get("report_period"),
            parser_family=str(data.get("parser_family") or ""),
            validation_status=str(data.get("validation_status") or "unchecked"),
            schema_version=data.get("schema_version"),
            sec_filing_url=data.get("sec_filing_url"),
            sec_primary_document_url=data.get("sec_primary_document_url"),
            local_raw_filing_path=data.get("local_raw_filing_path"),
            local_raw_index_path=data.get("local_raw_index_path"),
            local_normalized_path=data.get("local_normalized_path"),
            raw_sha256=data.get("raw_sha256"),
            parser_format=data.get("parser_format"),
        )

    @property
    def form_family(self) -> str:
        form = self.form.upper()
        if form.startswith("10-K"):
            return "10-K"
        if form.startswith("10-Q"):
            return "10-Q"
        return form

    @property
    def is_amendment(self) -> bool:
        return self.form.upper().endswith("/A")

    @property
    def is_metric_relevant_periodic(self) -> bool:
        return self.form.upper() in METRIC_RELEVANT_PERIODIC_FORMS


@dataclass(frozen=True, slots=True)
class PeriodicReportFactRecord:
    accession_number: str
    cik: str
    filing_date: str
    form: str
    concept_qname: str
    concept_local_name: str
    dimensions: dict[str, str]
    parser_format: str
    source_path: str
    validation_status: str
    ticker_workspace: str | None = None
    report_period: str | None = None
    namespace_uri: str | None = None
    context_id: str | None = None
    unit: str | None = None
    decimals: str | None = None
    scale: int | None = None
    scale_source: str | None = None
    presentation_note: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    instant: str | None = None
    value: str | None = None
    normalized_value: str | None = None
    statement_hint: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PeriodicReportFactRecord":
        return cls(
            accession_number=str(data.get("accession_number") or ""),
            cik=str(data.get("cik") or ""),
            filing_date=str(data.get("filing_date") or ""),
            form=str(data.get("form") or ""),
            concept_qname=str(data.get("concept_qname") or ""),
            concept_local_name=str(data.get("concept_local_name") or ""),
            dimensions=dict(data.get("dimensions") or {}),
            parser_format=str(data.get("parser_format") or ""),
            source_path=str(data.get("source_path") or ""),
            validation_status=str(data.get("validation_status") or "unchecked"),
            ticker_workspace=data.get("ticker_workspace"),
            report_period=data.get("report_period"),
            namespace_uri=data.get("namespace_uri"),
            context_id=data.get("context_id"),
            unit=data.get("unit"),
            decimals=data.get("decimals"),
            scale=data.get("scale"),
            scale_source=data.get("scale_source"),
            presentation_note=data.get("presentation_note"),
            period_start=data.get("period_start"),
            period_end=data.get("period_end"),
            instant=data.get("instant"),
            value=data.get("value"),
            normalized_value=data.get("normalized_value"),
            statement_hint=data.get("statement_hint"),
        )


@dataclass(frozen=True, slots=True)
class PeriodicReportParsedFiling:
    accession_number: str
    cik: str
    form: str
    filing_date: str
    parser_format: str
    source_path: str
    facts: list[PeriodicReportFactRecord]
    schema_version: str | None = None
    report_period: str | None = None
    validation: EdgarValidationSummary | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PeriodicReportParsedFiling":
        return cls(
            accession_number=str(data.get("accession_number") or ""),
            cik=str(data.get("cik") or ""),
            form=str(data.get("form") or ""),
            filing_date=str(data.get("filing_date") or ""),
            parser_format=str(data.get("parser_format") or ""),
            source_path=str(data.get("source_path") or ""),
            facts=[PeriodicReportFactRecord.from_dict(item) for item in data.get("facts", [])],
            schema_version=data.get("schema_version"),
            report_period=data.get("report_period"),
            validation=EdgarValidationSummary.from_dict(data.get("validation")),
        )

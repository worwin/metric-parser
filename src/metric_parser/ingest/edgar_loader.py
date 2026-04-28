from __future__ import annotations

import json
from pathlib import Path

from metric_parser.ingest.edgar_models import FilingCatalogRecord
from metric_parser.ingest.edgar_models import PeriodicReportParsedFiling


def load_catalog_records(path: str | Path) -> list[FilingCatalogRecord]:
    records: list[FilingCatalogRecord] = []
    path = Path(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        records.append(FilingCatalogRecord.from_dict(json.loads(line)))
    return records


def load_periodic_report_filing(path: str | Path) -> PeriodicReportParsedFiling:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return PeriodicReportParsedFiling.from_dict(payload)


def filter_metric_relevant_periodic_records(records: list[FilingCatalogRecord]) -> list[FilingCatalogRecord]:
    return [record for record in records if record.is_metric_relevant_periodic]


def select_preferred_periodic_records(records: list[FilingCatalogRecord]) -> list[FilingCatalogRecord]:
    grouped: dict[tuple[str, str, str | None], list[FilingCatalogRecord]] = {}
    for record in filter_metric_relevant_periodic_records(records):
        key = (record.cik, record.form_family, record.report_period)
        grouped.setdefault(key, []).append(record)

    selected: list[FilingCatalogRecord] = []
    for group in grouped.values():
        selected.append(max(group, key=_catalog_preference_key))
    return sorted(selected, key=lambda item: (item.cik, item.form_family, item.report_period or "", item.filing_date, item.accession_number))


def _catalog_preference_key(record: FilingCatalogRecord) -> tuple[int, str, str, str]:
    return (
        int(record.is_amendment),
        record.filing_date,
        record.accession_number,
        record.parser_format or "",
    )

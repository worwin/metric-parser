from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from metric_parser.ingest import filter_metric_relevant_periodic_records
from metric_parser.ingest import load_catalog_records
from metric_parser.ingest import load_periodic_report_filing
from metric_parser.ingest import select_preferred_periodic_records
from metric_parser.mapping import build_period_fields_artifact
from metric_parser.mapping import select_canonical_fields


_WORKSPACE_TMP_ROOT = Path(".tmp-tests")


class EdgarIngestionTests(unittest.TestCase):
    def test_catalog_selection_prefers_amendment_for_same_period(self) -> None:
        catalog_path = _workspace_file("catalog_selection.jsonl")
        rows = [
            {
                "accession_number": "0001",
                "cik": "0000123",
                "company_name": "Example Corp",
                "form": "10-Q",
                "filing_date": "2026-05-01",
                "report_period": "2026-03-31",
                "parser_family": "periodic_reports",
                "validation_status": "pass",
                "local_normalized_path": "D:/data/ticker/example/normalized/10q/0001.json",
            },
            {
                "accession_number": "0002",
                "cik": "0000123",
                "company_name": "Example Corp",
                "form": "10-Q/A",
                "filing_date": "2026-05-10",
                "report_period": "2026-03-31",
                "parser_family": "periodic_reports",
                "validation_status": "pass",
                "local_normalized_path": "D:/data/ticker/example/normalized/10q/0002.json",
            },
            {
                "accession_number": "0003",
                "cik": "0000123",
                "company_name": "Example Corp",
                "form": "8-K",
                "filing_date": "2026-04-15",
                "report_period": "2026-04-15",
                "parser_family": "current_reports",
                "validation_status": "pass",
                "local_normalized_path": "D:/data/ticker/example/normalized/8k/0003.json",
            },
        ]
        catalog_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

        records = load_catalog_records(catalog_path)
        periodic_records = filter_metric_relevant_periodic_records(records)
        selected = select_preferred_periodic_records(records)

        self.assertEqual(len(periodic_records), 2)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].form, "10-Q/A")
        self.assertEqual(selected[0].accession_number, "0002")

    def test_periodic_filing_loader_reads_minimal_upstream_shape(self) -> None:
        filing_path = _workspace_file("periodic_minimal.json")
        filing_path.write_text(
            json.dumps(
                {
                    "schema_version": "0.1.0",
                    "accession_number": "0001",
                    "cik": "0000123",
                    "form": "10-K",
                    "filing_date": "2026-02-20",
                    "report_period": "2025-12-31",
                    "parser_format": "inline_xbrl",
                    "source_path": "D:/data/ticker/example/normalized/10k/0001.json",
                    "facts": [
                        {
                            "accession_number": "0001",
                            "cik": "0000123",
                            "filing_date": "2026-02-20",
                            "form": "10-K",
                            "concept_qname": "us-gaap:Revenues",
                            "concept_local_name": "Revenues",
                            "dimensions": {},
                            "parser_format": "inline_xbrl",
                            "source_path": "D:/data/source",
                            "validation_status": "pass",
                            "report_period": "2025-12-31",
                            "period_start": "2025-01-01",
                            "period_end": "2025-12-31",
                            "unit": "iso4217:USD",
                            "value": "100"
                        }
                    ],
                    "validation": {
                        "accession_number": "0001",
                        "filing_date": "2026-02-20",
                        "form": "10-K",
                        "parser_format": "inline_xbrl",
                        "validation_status": "pass",
                        "warnings": []
                    }
                }
            ),
            encoding="utf-8",
        )

        filing = load_periodic_report_filing(filing_path)
        self.assertEqual(filing.accession_number, "0001")
        self.assertEqual(filing.facts[0].concept_local_name, "Revenues")
        self.assertEqual(filing.validation.validation_status, "pass")


class CanonicalFieldMappingTests(unittest.TestCase):
    def test_field_selector_prefers_current_nondimensional_fact_and_derives_total_debt(self) -> None:
        filing = load_periodic_report_filing(_write_periodic_fixture("mapping_selection.json"))
        fields = select_canonical_fields(filing)
        field_by_code = {field.field_code: field for field in fields}

        self.assertEqual(field_by_code["revenue"].value, "1200")
        self.assertEqual(field_by_code["revenue"].selection_method, "concept_alias:Revenues")
        self.assertEqual(field_by_code["capital_expenditures_proxy"].warnings, ["capex_proxy_used"])
        self.assertEqual(field_by_code["total_debt"].value, "450")
        self.assertIn("debt_components_aggregated", field_by_code["total_debt"].warnings)
        self.assertEqual(len(field_by_code["total_debt"].source_facts), 2)

    def test_build_period_fields_artifact_carries_identity_and_parser_warnings(self) -> None:
        filing = load_periodic_report_filing(_write_periodic_fixture("mapping_artifact.json"))
        artifact = build_period_fields_artifact(run_id="run-001", filing=filing)
        data = artifact.to_dict()

        self.assertEqual(data["ticker"], "EXAMPLE")
        self.assertEqual(data["period_type"], "quarterly")
        self.assertEqual(data["fiscal_year"], 2026)
        self.assertEqual(data["fiscal_quarter"], 3)
        self.assertEqual(data["parser_warnings_inherited"], ["missing_cash_flow_facts"])
        self.assertEqual(data["fields"][0]["field_code"], "revenue")


@classmethod
def tearDownClass(cls) -> None:
    shutil.rmtree(_WORKSPACE_TMP_ROOT, ignore_errors=True)


EdgarIngestionTests.tearDownClass = tearDownClass
CanonicalFieldMappingTests.tearDownClass = tearDownClass


def _workspace_file(name: str) -> Path:
    _WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return _WORKSPACE_TMP_ROOT / name


def _write_periodic_fixture(name: str) -> Path:
    path = _workspace_file(name)
    path.write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "accession_number": "0009",
                "cik": "0000999",
                "form": "10-Q",
                "filing_date": "2026-11-01",
                "report_period": "2026-09-30",
                "parser_format": "inline_xbrl",
                "source_path": "D:/data/ticker/example/normalized/10q/0009.json",
                "facts": [
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:Revenues",
                        "concept_local_name": "Revenues",
                        "dimensions": {},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "income_statement",
                        "report_period": "2026-09-30",
                        "context_id": "c1",
                        "period_start": "2026-01-01",
                        "period_end": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "1,200"
                    },
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:Revenues",
                        "concept_local_name": "Revenues",
                        "dimensions": {"SegmentAxis": "Cloud"},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "income_statement",
                        "report_period": "2026-09-30",
                        "context_id": "c2",
                        "period_start": "2026-01-01",
                        "period_end": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "600"
                    },
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:GrossProfit",
                        "concept_local_name": "GrossProfit",
                        "dimensions": {},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "income_statement",
                        "report_period": "2026-09-30",
                        "context_id": "c1",
                        "period_start": "2026-01-01",
                        "period_end": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "700"
                    },
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:Assets",
                        "concept_local_name": "Assets",
                        "dimensions": {},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "balance_sheet",
                        "report_period": "2026-09-30",
                        "context_id": "i1",
                        "instant": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "4,000"
                    },
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:StockholdersEquity",
                        "concept_local_name": "StockholdersEquity",
                        "dimensions": {},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "balance_sheet",
                        "report_period": "2026-09-30",
                        "context_id": "i1",
                        "instant": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "2,500"
                    },
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:NetCashProvidedByUsedInOperatingActivities",
                        "concept_local_name": "NetCashProvidedByUsedInOperatingActivities",
                        "dimensions": {},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "cash_flow",
                        "report_period": "2026-09-30",
                        "context_id": "c1",
                        "period_start": "2026-01-01",
                        "period_end": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "300"
                    },
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:CapitalExpendituresIncurredButNotYetPaid",
                        "concept_local_name": "CapitalExpendituresIncurredButNotYetPaid",
                        "dimensions": {},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "cash_flow",
                        "report_period": "2026-09-30",
                        "context_id": "c1",
                        "period_start": "2026-01-01",
                        "period_end": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "90"
                    },
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:LongTermDebtCurrent",
                        "concept_local_name": "LongTermDebtCurrent",
                        "dimensions": {},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "balance_sheet",
                        "report_period": "2026-09-30",
                        "context_id": "i1",
                        "instant": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "100"
                    },
                    {
                        "accession_number": "0009",
                        "cik": "0000999",
                        "ticker_workspace": "example",
                        "filing_date": "2026-11-01",
                        "form": "10-Q",
                        "concept_qname": "us-gaap:LongTermDebtNoncurrent",
                        "concept_local_name": "LongTermDebtNoncurrent",
                        "dimensions": {},
                        "parser_format": "inline_xbrl",
                        "source_path": "D:/data/source",
                        "validation_status": "pass",
                        "statement_hint": "balance_sheet",
                        "report_period": "2026-09-30",
                        "context_id": "i1",
                        "instant": "2026-09-30",
                        "unit": "iso4217:USD",
                        "value": "350"
                    }
                ],
                "validation": {
                    "accession_number": "0009",
                    "filing_date": "2026-11-01",
                    "form": "10-Q",
                    "parser_format": "inline_xbrl",
                    "validation_status": "warn",
                    "warnings": [
                        {
                            "code": "missing_cash_flow_facts",
                            "message": "Example warning",
                            "severity": "warning"
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    unittest.main()


class FiscalFocusTests(unittest.TestCase):
    def test_build_period_fields_artifact_prefers_document_fiscal_focus(self) -> None:
        filing = load_periodic_report_filing(_write_off_calendar_fiscal_focus_fixture())
        artifact = build_period_fields_artifact(run_id='run-fiscal-focus', filing=filing)

        self.assertEqual(artifact.identity.fiscal_year, 2026)
        self.assertEqual(artifact.identity.fiscal_quarter, 3)
        self.assertEqual(artifact.identity.filing_period, '2025-10-26')


FiscalFocusTests.tearDownClass = tearDownClass


def _write_off_calendar_fiscal_focus_fixture() -> Path:
    path = _workspace_file('off_calendar_focus.json')
    path.write_text(
        json.dumps(
            {
                'schema_version': '0.1.0',
                'accession_number': '0010',
                'cik': '0001045810',
                'form': '10-Q',
                'filing_date': '2025-11-19',
                'report_period': '2025-10-26',
                'parser_format': 'inline_xbrl',
                'source_path': 'D:/data/ticker/nvda/normalized/10q/0010.json',
                'facts': [
                    {
                        'accession_number': '0010',
                        'cik': '0001045810',
                        'ticker_workspace': 'nvda',
                        'filing_date': '2025-11-19',
                        'form': '10-Q',
                        'concept_qname': 'dei:DocumentFiscalYearFocus',
                        'concept_local_name': 'DocumentFiscalYearFocus',
                        'dimensions': {},
                        'parser_format': 'inline_xbrl',
                        'source_path': 'D:/data/source',
                        'validation_status': 'pass',
                        'report_period': '2025-10-26',
                        'context_id': 'focus-1',
                        'period_start': '2025-01-27',
                        'period_end': '2025-10-26',
                        'value': '2026'
                    },
                    {
                        'accession_number': '0010',
                        'cik': '0001045810',
                        'ticker_workspace': 'nvda',
                        'filing_date': '2025-11-19',
                        'form': '10-Q',
                        'concept_qname': 'dei:DocumentFiscalPeriodFocus',
                        'concept_local_name': 'DocumentFiscalPeriodFocus',
                        'dimensions': {},
                        'parser_format': 'inline_xbrl',
                        'source_path': 'D:/data/source',
                        'validation_status': 'pass',
                        'report_period': '2025-10-26',
                        'context_id': 'focus-1',
                        'period_start': '2025-01-27',
                        'period_end': '2025-10-26',
                        'value': 'Q3'
                    },
                    {
                        'accession_number': '0010',
                        'cik': '0001045810',
                        'ticker_workspace': 'nvda',
                        'filing_date': '2025-11-19',
                        'form': '10-Q',
                        'concept_qname': 'us-gaap:Revenues',
                        'concept_local_name': 'Revenues',
                        'dimensions': {},
                        'parser_format': 'inline_xbrl',
                        'source_path': 'D:/data/source',
                        'validation_status': 'pass',
                        'statement_hint': 'income_statement',
                        'report_period': '2025-10-26',
                        'context_id': 'c1',
                        'period_start': '2025-01-27',
                        'period_end': '2025-10-26',
                        'unit': 'iso4217:USD',
                        'value': '1234'
                    }
                ],
                'validation': {
                    'accession_number': '0010',
                    'filing_date': '2025-11-19',
                    'form': '10-Q',
                    'parser_format': 'inline_xbrl',
                    'validation_status': 'pass',
                    'warnings': []
                }
            }
        ),
        encoding='utf-8',
    )
    return path

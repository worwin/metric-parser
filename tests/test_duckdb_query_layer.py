from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from metric_parser.artifacts import write_company_metric_artifacts
from metric_parser.db import ingest_company_artifact_directory
from metric_parser.pipeline import build_company_metric_history_from_catalog_path
from metric_parser.query import MetricQueryService


class DuckDbQueryLayerTests(unittest.TestCase):
    def test_ingest_artifacts_and_query_metric_history(self) -> None:
        fixture_root = Path('.tmp-tests') / 'duckdb-fixture'
        if fixture_root.exists():
            shutil.rmtree(fixture_root)
        artifact_dir = fixture_root / 'artifacts' / 'acme'
        db_path = fixture_root / 'metrics.duckdb'

        catalog_path = _write_company_fixture(fixture_root)
        build = build_company_metric_history_from_catalog_path(
            run_id='duckdb-test',
            catalog_path=catalog_path,
            ticker='ACME',
            created_at='2026-04-04T12:00:00Z',
        )
        write_company_metric_artifacts(artifact_dir, build)
        ingest_company_artifact_directory(database_path=db_path, artifact_dir=artifact_dir)

        query = MetricQueryService(db_path)
        companies = query.list_companies()
        annual_revenue_history = query.get_metric_history('ACME', 'revenue', 'annual')
        quarterly_revenue_history = query.get_metric_history('ACME', 'revenue', 'quarterly')
        latest_fcf_margin = query.get_latest_metric('ACME', 'free_cash_flow_margin')
        warnings = query.get_metric_warnings('ACME')

        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0]['ticker'], 'ACME')
        self.assertEqual(len(annual_revenue_history), 2)
        self.assertEqual(len(quarterly_revenue_history), 5)
        self.assertIsNotNone(latest_fcf_margin)
        self.assertEqual(latest_fcf_margin['metric_code'], 'free_cash_flow_margin')
        self.assertEqual(latest_fcf_margin['fiscal_year'], 2026)
        self.assertEqual(latest_fcf_margin['fiscal_quarter'], 4)
        self.assertTrue(warnings)

        q4_revenue_record_id = next(
            row['metric_record_id']
            for row in quarterly_revenue_history
            if row['fiscal_year'] == 2026 and row['fiscal_quarter'] == 4
        )
        lineage = query.get_metric_lineage(q4_revenue_record_id)
        filings = query.get_source_filings_for_metric_record(q4_revenue_record_id)

        self.assertEqual(len(lineage), 2)
        self.assertEqual({row['source_accession'] for row in filings}, {'0000001-26-000013', '0000001-26-000014'})


def _write_company_fixture(fixture_root: Path) -> Path:
    catalog_path = fixture_root / 'catalog' / 'filings.jsonl'
    normalized_dir = fixture_root / 'ticker' / 'acme' / 'normalized'
    normalized_dir.mkdir(parents=True, exist_ok=True)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)

    filings = [
        _filing_fixture('0000001-25-000010', '10-K', '2026-02-15', '2025-12-31', '2025-01-01', {
            'Revenues': '700',
            'GrossProfit': '420',
            'OperatingIncomeLoss': '175',
            'NetIncomeLoss': '140',
            'NetCashProvidedByOperatingActivities': '180',
            'CapitalExpendituresIncurredButNotYetPaid': '50',
            'DepreciationDepletionAndAmortization': '28',
            'PaymentsOfDividends': '30',
            'WeightedAverageNumberOfSharesOutstandingBasic': '102',
            'WeightedAverageNumberOfDilutedSharesOutstanding': '104',
        }, {
            'Assets': '1100',
            'StockholdersEquity': '700',
            'AssetsCurrent': '440',
            'LiabilitiesCurrent': '220',
            'CashAndCashEquivalentsAtCarryingValue': '100',
            'ShortTermInvestments': '70',
            'AccountsReceivableNetCurrent': '80',
            'CommonStockSharesOutstanding': '101',
            'LongTermDebtCurrent': '40',
            'LongTermDebtNoncurrent': '200',
        }),
        _filing_fixture('0000001-26-000011', '10-Q', '2026-04-20', '2026-03-31', '2026-01-01', {
            'Revenues': '120',
            'GrossProfit': '72',
            'OperatingIncomeLoss': '24',
            'NetIncomeLoss': '20',
            'NetCashProvidedByOperatingActivities': '30',
            'CapitalExpendituresIncurredButNotYetPaid': '8',
            'DepreciationDepletionAndAmortization': '4',
            'PaymentsOfDividends': '2',
            'WeightedAverageNumberOfSharesOutstandingBasic': '100',
            'WeightedAverageNumberOfDilutedSharesOutstanding': '102',
        }, {
            'Assets': '1120',
            'StockholdersEquity': '720',
            'AssetsCurrent': '450',
            'LiabilitiesCurrent': '225',
            'CashAndCashEquivalentsAtCarryingValue': '105',
            'ShortTermInvestments': '72',
            'AccountsReceivableNetCurrent': '81',
            'CommonStockSharesOutstanding': '100',
            'LongTermDebtCurrent': '42',
            'LongTermDebtNoncurrent': '205',
        }),
        _filing_fixture('0000001-26-000012', '10-Q', '2026-07-20', '2026-06-30', '2026-01-01', {
            'Revenues': '250',
            'GrossProfit': '150',
            'OperatingIncomeLoss': '52',
            'NetIncomeLoss': '42',
            'NetCashProvidedByOperatingActivities': '68',
            'CapitalExpendituresIncurredButNotYetPaid': '18',
            'DepreciationDepletionAndAmortization': '9',
            'PaymentsOfDividends': '4',
            'WeightedAverageNumberOfSharesOutstandingBasic': '99',
            'WeightedAverageNumberOfDilutedSharesOutstanding': '101',
        }, {
            'Assets': '1140',
            'StockholdersEquity': '730',
            'AssetsCurrent': '460',
            'LiabilitiesCurrent': '228',
            'CashAndCashEquivalentsAtCarryingValue': '108',
            'ShortTermInvestments': '75',
            'AccountsReceivableNetCurrent': '83',
            'CommonStockSharesOutstanding': '99',
            'LongTermDebtCurrent': '43',
            'LongTermDebtNoncurrent': '206',
        }),
        _filing_fixture('0000001-26-000013', '10-Q', '2026-10-20', '2026-09-30', '2026-01-01', {
            'Revenues': '580',
            'GrossProfit': '348',
            'OperatingIncomeLoss': '120',
            'NetIncomeLoss': '96',
            'NetCashProvidedByOperatingActivities': '150',
            'CapitalExpendituresIncurredButNotYetPaid': '40',
            'DepreciationDepletionAndAmortization': '15',
            'PaymentsOfDividends': '7',
            'WeightedAverageNumberOfSharesOutstandingBasic': '99',
            'WeightedAverageNumberOfDilutedSharesOutstanding': '101',
        }, {
            'Assets': '1180',
            'StockholdersEquity': '748',
            'AssetsCurrent': '470',
            'LiabilitiesCurrent': '230',
            'CashAndCashEquivalentsAtCarryingValue': '112',
            'ShortTermInvestments': '78',
            'AccountsReceivableNetCurrent': '88',
            'CommonStockSharesOutstanding': '98',
            'LongTermDebtCurrent': '45',
            'LongTermDebtNoncurrent': '208',
        }),
        _filing_fixture('0000001-26-000014', '10-K', '2027-02-15', '2026-12-31', '2026-01-01', {
            'Revenues': '800',
            'GrossProfit': '480',
            'OperatingIncomeLoss': '165',
            'NetIncomeLoss': '132',
            'NetCashProvidedByOperatingActivities': '205',
            'CapitalExpendituresIncurredButNotYetPaid': '58',
            'DepreciationDepletionAndAmortization': '21',
            'PaymentsOfDividends': '10',
            'WeightedAverageNumberOfSharesOutstandingBasic': '99',
            'WeightedAverageNumberOfDilutedSharesOutstanding': '101',
        }, {
            'Assets': '1200',
            'StockholdersEquity': '760',
            'AssetsCurrent': '480',
            'LiabilitiesCurrent': '240',
            'CashAndCashEquivalentsAtCarryingValue': '115',
            'ShortTermInvestments': '80',
            'AccountsReceivableNetCurrent': '90',
            'CommonStockSharesOutstanding': '98',
            'LongTermDebtCurrent': '46',
            'LongTermDebtNoncurrent': '210',
        }),
    ]

    catalog_lines: list[str] = []
    for filing in filings:
        form_dir = filing['form'].lower().replace('/', '').replace('-', '')
        normalized_path = normalized_dir / form_dir / f"{filing['accession_number']}.json"
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_path.write_text(json.dumps(filing), encoding='utf-8')
        catalog_lines.append(json.dumps(_catalog_record(filing, normalized_path)))

    catalog_path.write_text('\n'.join(catalog_lines) + '\n', encoding='utf-8')
    return catalog_path


def _catalog_record(filing: dict, normalized_path: Path) -> dict:
    return {
        'accession_number': filing['accession_number'],
        'cik': filing['cik'],
        'company_name': 'Acme Corp',
        'form': filing['form'],
        'filing_date': filing['filing_date'],
        'report_period': filing['report_period'],
        'parser_family': 'periodic_reports',
        'validation_status': 'pass',
        'schema_version': '0.1.0',
        'local_normalized_path': normalized_path.as_posix(),
        'parser_format': 'inline_xbrl',
    }


def _filing_fixture(
    accession_number: str,
    form: str,
    filing_date: str,
    report_period: str,
    period_start: str,
    duration_values: dict[str, str],
    instant_values: dict[str, str],
) -> dict:
    facts: list[dict] = [
        {
            'accession_number': accession_number,
            'cik': '0000001',
            'ticker_workspace': 'acme',
            'filing_date': filing_date,
            'form': form,
            'concept_qname': 'dei:DocumentFiscalYearFocus',
            'concept_local_name': 'DocumentFiscalYearFocus',
            'dimensions': {},
            'parser_format': 'inline_xbrl',
            'source_path': f'D:/fixtures/ticker/acme/raw/{accession_number}.htm',
            'validation_status': 'pass',
            'report_period': report_period,
            'context_id': 'focus-1',
            'value': report_period[:4],
        },
        {
            'accession_number': accession_number,
            'cik': '0000001',
            'ticker_workspace': 'acme',
            'filing_date': filing_date,
            'form': form,
            'concept_qname': 'dei:DocumentFiscalPeriodFocus',
            'concept_local_name': 'DocumentFiscalPeriodFocus',
            'dimensions': {},
            'parser_format': 'inline_xbrl',
            'source_path': f'D:/fixtures/ticker/acme/raw/{accession_number}.htm',
            'validation_status': 'pass',
            'report_period': report_period,
            'context_id': 'focus-1',
            'value': 'FY' if form == '10-K' else ('Q1' if report_period.endswith('03-31') else 'Q2' if report_period.endswith('06-30') else 'Q3'),
        },
    ]
    for concept_local_name, value in duration_values.items():
        facts.append(
            {
                'accession_number': accession_number,
                'cik': '0000001',
                'filing_date': filing_date,
                'form': form,
                'concept_qname': f'us-gaap:{concept_local_name}',
                'concept_local_name': concept_local_name,
                'dimensions': {},
                'parser_format': 'inline_xbrl',
                'source_path': f'D:/fixtures/ticker/acme/raw/{accession_number}.htm',
                'validation_status': 'pass',
                'ticker_workspace': 'acme',
                'report_period': report_period,
                'context_id': f'duration-{concept_local_name}',
                'unit': 'USD' if 'Shares' not in concept_local_name else 'shares',
                'period_start': period_start,
                'period_end': report_period,
                'value': value,
                'statement_hint': 'cash_flow' if 'Cash' in concept_local_name or 'Depreciation' in concept_local_name or 'CapitalExpenditures' in concept_local_name or 'Payments' in concept_local_name else 'income_statement',
            }
        )
    for concept_local_name, value in instant_values.items():
        facts.append(
            {
                'accession_number': accession_number,
                'cik': '0000001',
                'filing_date': filing_date,
                'form': form,
                'concept_qname': f'us-gaap:{concept_local_name}',
                'concept_local_name': concept_local_name,
                'dimensions': {},
                'parser_format': 'inline_xbrl',
                'source_path': f'D:/fixtures/ticker/acme/raw/{accession_number}.htm',
                'validation_status': 'pass',
                'ticker_workspace': 'acme',
                'report_period': report_period,
                'context_id': f'instant-{concept_local_name}',
                'unit': 'USD' if 'Shares' not in concept_local_name else 'shares',
                'instant': report_period,
                'value': value,
                'statement_hint': 'balance_sheet',
            }
        )

    return {
        'accession_number': accession_number,
        'cik': '0000001',
        'form': form,
        'filing_date': filing_date,
        'parser_format': 'inline_xbrl',
        'source_path': f'D:/fixtures/ticker/acme/raw/{accession_number}.htm',
        'report_period': report_period,
        'schema_version': '0.1.0',
        'facts': facts,
        'validation': {
            'accession_number': accession_number,
            'filing_date': filing_date,
            'form': form,
            'parser_format': 'inline_xbrl',
            'validation_status': 'pass',
            'warnings': [],
        },
    }


if __name__ == '__main__':
    unittest.main()

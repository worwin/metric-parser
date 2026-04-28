from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from metric_parser.artifacts import write_company_metric_artifacts
from metric_parser.pipeline import build_company_metric_history_from_catalog_path


class PipelineTests(unittest.TestCase):
    def test_build_company_metric_history_and_write_artifacts(self) -> None:
        fixture_root = Path('.tmp-tests') / 'pipeline-fixture'
        if fixture_root.exists():
            shutil.rmtree(fixture_root)
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
                'PaymentsToAcquirePropertyPlantAndEquipment': '50',
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
                'PaymentsToAcquirePropertyPlantAndEquipment': '8',
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
                'PaymentsToAcquirePropertyPlantAndEquipment': '18',
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
                'PaymentsToAcquirePropertyPlantAndEquipment': '40',
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
                'PaymentsToAcquirePropertyPlantAndEquipment': '58',
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

        result = build_company_metric_history_from_catalog_path(
            run_id='pipeline-test',
            catalog_path=catalog_path,
            ticker='ACME',
            created_at='2026-04-03T12:00:00Z',
        )

        self.assertEqual(result.ticker, 'ACME')
        self.assertEqual(result.cik, '0000001')
        self.assertEqual(len(result.annual_fields), 2)
        self.assertEqual(len(result.quarterly_fields), 5)
        self.assertEqual(len(result.annual_metrics), 2)
        self.assertEqual(len(result.quarterly_metrics), 5)

        quarterly_by_key = {
            (bundle.identity.fiscal_year, bundle.identity.fiscal_quarter): bundle
            for bundle in result.quarterly_metrics
        }
        q2_revenue = _metric_value(quarterly_by_key[(2026, 2)], 'revenue')
        q4_revenue = _metric_value(quarterly_by_key[(2026, 4)], 'revenue')
        q4_free_cash_flow_warnings = _metric_warnings(quarterly_by_key[(2026, 4)], 'free_cash_flow')
        self.assertEqual(q2_revenue, '130')
        self.assertEqual(q4_revenue, '220')
        self.assertEqual(q4_free_cash_flow_warnings, ['quarter_derived_from_annual_minus_q3_ytd'])

        output_paths = write_company_metric_artifacts(fixture_root / 'output', result)
        annual_metrics_payload = json.loads(Path(output_paths['annual_metrics']).read_text(encoding='utf-8'))
        quarterly_metrics_payload = json.loads(Path(output_paths['quarterly_metrics']).read_text(encoding='utf-8'))
        manifest_payload = json.loads(Path(output_paths['build_manifest']).read_text(encoding='utf-8'))

        self.assertTrue(annual_metrics_payload)
        self.assertTrue(quarterly_metrics_payload)
        self.assertEqual(manifest_payload['annual_period_count'], 2)
        self.assertEqual(manifest_payload['quarterly_period_count'], 5)
        self.assertIn('metric_code', annual_metrics_payload[0])
        self.assertIn('source_accessions', quarterly_metrics_payload[0])


def _metric_value(bundle, metric_code: str) -> str | None:
    for metric in bundle.metrics:
        if metric.metric_code == metric_code:
            return metric.value
    return None


def _metric_warnings(bundle, metric_code: str) -> list[str]:
    for metric in bundle.metrics:
        if metric.metric_code == metric_code:
            return metric.warnings
    return []


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
    facts: list[dict] = []
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
                'statement_hint': 'cash_flow' if 'Cash' in concept_local_name or 'Depreciation' in concept_local_name or 'Payments' in concept_local_name else 'income_statement',
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


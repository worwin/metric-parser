from __future__ import annotations

import json
from decimal import Decimal
from decimal import InvalidOperation
from pathlib import Path
from typing import Any

from metric_parser.compute.definitions import METRIC_DEFINITIONS
from metric_parser.db.schema import connect_duckdb
from metric_parser.db.schema import ensure_schema


def ingest_company_artifact_directory(database_path: str | Path, artifact_dir: str | Path) -> None:
    artifact_root = Path(artifact_dir)
    connection = connect_duckdb(database_path)
    try:
        ensure_schema(connection)
        payload = _load_artifact_payloads(artifact_root)
        ticker = str(payload['build_manifest']['ticker'])
        cik = str(payload['build_manifest']['cik'])
        _delete_company_rows(connection, ticker=ticker, cik=cik)
        _upsert_company(connection, payload['build_manifest'])
        _insert_metric_definitions(connection)
        _insert_filings(connection, payload['source_filings'], ticker=ticker)
        _insert_metrics(connection, 'metrics_annual', payload['annual_metrics'])
        _insert_metrics(connection, 'metrics_quarterly', payload['quarterly_metrics'])
        _insert_metric_warnings(connection, payload['metric_warnings'])
        _insert_metric_lineage(connection, payload['annual_metrics'])
        _insert_metric_lineage(connection, payload['quarterly_metrics'])
    finally:
        connection.close()


def ingest_company_artifact_directories(database_path: str | Path, artifact_directories: list[str | Path]) -> None:
    for artifact_dir in artifact_directories:
        ingest_company_artifact_directory(database_path=database_path, artifact_dir=artifact_dir)


def _load_artifact_payloads(artifact_root: Path) -> dict[str, Any]:
    file_names = {
        'build_manifest': 'build_manifest.json',
        'source_filings': 'source_filings.json',
        'annual_metrics': 'annual_metrics.json',
        'quarterly_metrics': 'quarterly_metrics.json',
        'metric_warnings': 'metric_warnings.json',
    }
    payloads: dict[str, Any] = {}
    for key, file_name in file_names.items():
        path = artifact_root / file_name
        payloads[key] = json.loads(path.read_text(encoding='utf-8'))
    return payloads


def _delete_company_rows(connection, ticker: str, cik: str) -> None:
    for table_name in ('metric_lineage', 'metric_warnings', 'metrics_annual', 'metrics_quarterly', 'filings', 'companies'):
        connection.execute(f"DELETE FROM {table_name} WHERE cik = ? OR ticker = ?", [cik, ticker])


def _upsert_company(connection, manifest: dict[str, Any]) -> None:
    connection.execute(
        """
        INSERT INTO companies (
            cik,
            ticker,
            company_name,
            latest_run_id,
            source_catalog_path,
            created_at,
            annual_period_count,
            quarterly_period_count,
            annual_metric_record_count,
            quarterly_metric_record_count,
            warning_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            manifest.get('cik'),
            manifest.get('ticker'),
            manifest.get('company_name'),
            manifest.get('run_id'),
            manifest.get('source_catalog_path'),
            manifest.get('created_at'),
            manifest.get('annual_period_count'),
            manifest.get('quarterly_period_count'),
            manifest.get('annual_metric_record_count'),
            manifest.get('quarterly_metric_record_count'),
            manifest.get('warning_count'),
        ],
    )


def _insert_metric_definitions(connection) -> None:
    connection.execute('DELETE FROM metric_definitions')
    rows = [
        (
            definition.metric_code,
            definition.metric_name,
            definition.category,
            definition.subcategory,
            definition.value_type,
            definition.unit,
            definition.formula_id,
            definition.formula_text,
            1,
        )
        for definition in METRIC_DEFINITIONS
    ]
    connection.executemany(
        """
        INSERT INTO metric_definitions (
            metric_code,
            metric_name,
            category,
            subcategory,
            value_type,
            unit,
            formula_id,
            formula_text,
            formula_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_filings(connection, filings: list[dict[str, Any]], ticker: str) -> None:
    rows = []
    for filing in filings:
        rows.append(
            (
                filing.get('accession_number'),
                filing.get('cik'),
                ticker,
                filing.get('company_name'),
                filing.get('form'),
                _form_family(filing.get('form')),
                filing.get('filing_date'),
                filing.get('report_period'),
                filing.get('parser_family'),
                filing.get('validation_status'),
                filing.get('schema_version'),
                filing.get('parser_format'),
                filing.get('local_normalized_path'),
                filing.get('local_raw_filing_path'),
                filing.get('local_raw_index_path'),
                filing.get('sec_filing_url'),
                filing.get('sec_primary_document_url'),
                filing.get('raw_sha256'),
            )
        )
    connection.executemany(
        """
        INSERT INTO filings (
            accession_number,
            cik,
            ticker,
            company_name,
            form,
            form_family,
            filing_date,
            report_period,
            parser_family,
            validation_status,
            schema_version,
            parser_format,
            local_normalized_path,
            local_raw_filing_path,
            local_raw_index_path,
            sec_filing_url,
            sec_primary_document_url,
            raw_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_metrics(connection, table_name: str, metrics: list[dict[str, Any]]) -> None:
    rows = []
    for metric in metrics:
        rows.append(
            (
                metric.get('metric_record_id'),
                metric.get('run_id'),
                metric.get('ticker'),
                metric.get('cik'),
                metric.get('company_name'),
                metric.get('filing_period'),
                metric.get('period_start'),
                metric.get('period_end'),
                metric.get('fiscal_year'),
                metric.get('fiscal_quarter'),
                metric.get('period_type'),
                metric.get('metric_name'),
                metric.get('metric_code'),
                metric.get('category'),
                metric.get('subcategory'),
                metric.get('value'),
                _coerce_numeric_value(metric.get('value')),
                metric.get('value_type'),
                metric.get('unit'),
                metric.get('formula_id'),
                metric.get('formula_version'),
                metric.get('formula_text'),
                json.dumps(metric.get('source_accessions', []), sort_keys=True),
                json.dumps(metric.get('warnings', []), sort_keys=True),
                _coerce_numeric_value(metric.get('confidence')),
                bool(metric.get('parser_warning_inherited')),
                metric.get('applicability'),
                metric.get('primary_filing_accession'),
                metric.get('created_at'),
            )
        )
    connection.executemany(
        f"""
        INSERT INTO {table_name} (
            metric_record_id,
            run_id,
            ticker,
            cik,
            company_name,
            filing_period,
            period_start,
            period_end,
            fiscal_year,
            fiscal_quarter,
            period_type,
            metric_name,
            metric_code,
            category,
            subcategory,
            value,
            numeric_value,
            value_type,
            unit,
            formula_id,
            formula_version,
            formula_text,
            source_accessions_json,
            warnings_json,
            confidence,
            parser_warning_inherited,
            applicability,
            primary_filing_accession,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_metric_warnings(connection, warnings: list[dict[str, Any]]) -> None:
    rows = [
        (
            warning.get('warning_id'),
            warning.get('metric_record_id'),
            warning.get('cik'),
            warning.get('ticker'),
            warning.get('filing_period'),
            warning.get('fiscal_year'),
            warning.get('fiscal_quarter'),
            warning.get('period_type'),
            warning.get('metric_code'),
            warning.get('warning_code'),
            warning.get('severity'),
            warning.get('warning_source'),
            warning.get('message'),
            warning.get('source_accession'),
            warning.get('upstream_warning_code'),
            warning.get('created_at'),
        )
        for warning in warnings
    ]
    if not rows:
        return
    connection.executemany(
        """
        INSERT INTO metric_warnings (
            warning_id,
            metric_record_id,
            cik,
            ticker,
            filing_period,
            fiscal_year,
            fiscal_quarter,
            period_type,
            metric_code,
            warning_code,
            severity,
            warning_source,
            message,
            source_accession,
            upstream_warning_code,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _insert_metric_lineage(connection, metrics: list[dict[str, Any]]) -> None:
    rows = []
    for metric in metrics:
        for index, source_fact in enumerate(metric.get('source_facts', []), start=1):
            rows.append(
                (
                    f"{metric.get('metric_record_id')}:{index}",
                    metric.get('metric_record_id'),
                    metric.get('ticker'),
                    metric.get('cik'),
                    metric.get('filing_period'),
                    metric.get('fiscal_year'),
                    metric.get('fiscal_quarter'),
                    metric.get('period_type'),
                    metric.get('metric_code'),
                    source_fact.get('source_accession'),
                    source_fact.get('source_form'),
                    source_fact.get('concept_local_name'),
                    source_fact.get('concept_qname'),
                    source_fact.get('context_id'),
                    source_fact.get('role'),
                    source_fact.get('period_start'),
                    source_fact.get('period_end'),
                    source_fact.get('instant'),
                    source_fact.get('unit'),
                    source_fact.get('raw_value'),
                    source_fact.get('source_path'),
                    source_fact.get('mapped_field_code'),
                )
            )
    if not rows:
        return
    connection.executemany(
        """
        INSERT INTO metric_lineage (
            lineage_id,
            metric_record_id,
            ticker,
            cik,
            filing_period,
            fiscal_year,
            fiscal_quarter,
            period_type,
            metric_code,
            source_accession,
            source_form,
            concept_local_name,
            concept_qname,
            context_id,
            role,
            period_start,
            period_end,
            instant,
            unit,
            raw_value,
            source_path,
            mapped_field_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _coerce_numeric_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return None


def _form_family(form: str | None) -> str:
    if not form:
        return ''
    form_upper = form.upper()
    if form_upper.startswith('10-K'):
        return '10-K'
    if form_upper.startswith('10-Q'):
        return '10-Q'
    return form_upper

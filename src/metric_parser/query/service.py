from __future__ import annotations

from pathlib import Path
from typing import Any

from metric_parser.db.schema import connect_duckdb


class MetricQueryService:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)

    def list_companies(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT cik, ticker, company_name, annual_period_count, quarterly_period_count
            FROM companies
            ORDER BY ticker
            """
        )

    def get_annual_metrics(self, ticker: str, metric_code: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM metrics_annual WHERE ticker = ?"
        params: list[Any] = [ticker.upper()]
        if metric_code is not None:
            sql += " AND metric_code = ?"
            params.append(metric_code)
        sql += " ORDER BY filing_period, metric_code"
        return self._fetch_all(sql, params)

    def get_quarterly_metrics(self, ticker: str, metric_code: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM metrics_quarterly WHERE ticker = ?"
        params: list[Any] = [ticker.upper()]
        if metric_code is not None:
            sql += " AND metric_code = ?"
            params.append(metric_code)
        sql += " ORDER BY filing_period, fiscal_quarter, metric_code"
        return self._fetch_all(sql, params)

    def get_metric_history(self, ticker: str, metric_code: str, period_type: str) -> list[dict[str, Any]]:
        table_name = _metric_table_name(period_type)
        return self._fetch_all(
            f"""
            SELECT metric_record_id, ticker, cik, company_name, filing_period, fiscal_year, fiscal_quarter, metric_code, metric_name,
                   numeric_value, value, unit, applicability, confidence, warnings_json
            FROM {table_name}
            WHERE ticker = ? AND metric_code = ?
            ORDER BY filing_period
            """,
            [ticker.upper(), metric_code],
        )

    def get_latest_metric(self, ticker: str, metric_code: str) -> dict[str, Any] | None:
        rows = self._fetch_all(
            """
            SELECT *
            FROM (
                SELECT 'annual' AS layer, * FROM metrics_annual
                UNION ALL
                SELECT 'quarterly' AS layer, * FROM metrics_quarterly
            ) AS metrics_union
            WHERE ticker = ? AND metric_code = ? AND applicability = 'applicable'
            ORDER BY filing_period DESC, COALESCE(fiscal_quarter, 0) DESC
            LIMIT 1
            """,
            [ticker.upper(), metric_code],
        )
        return rows[0] if rows else None

    def get_metric_warnings(self, ticker: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT ticker, filing_period, fiscal_year, fiscal_quarter, period_type, metric_code,
                   warning_code, severity, warning_source, message, metric_record_id
            FROM metric_warnings
            WHERE ticker = ?
            ORDER BY filing_period, metric_code, warning_code
            """,
            [ticker.upper()],
        )

    def get_metric_lineage(self, metric_record_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT metric_record_id, source_accession, source_form, concept_local_name, concept_qname,
                   role, context_id, period_start, period_end, instant, raw_value, unit, source_path, mapped_field_code
            FROM metric_lineage
            WHERE metric_record_id = ?
            ORDER BY lineage_id
            """,
            [metric_record_id],
        )

    def get_source_filings_for_metric_record(self, metric_record_id: str) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT DISTINCT filings.accession_number AS source_accession, filings.ticker, filings.company_name, filings.form,
                   filings.filing_date, filings.report_period, filings.sec_filing_url, filings.sec_primary_document_url
            FROM metric_lineage
            JOIN filings ON filings.accession_number = metric_lineage.source_accession
            WHERE metric_lineage.metric_record_id = ?
            ORDER BY filings.report_period, filings.accession_number
            """,
            [metric_record_id],
        )

    def query_sql(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        return self._fetch_all(sql, params or [])

    def _fetch_all(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        connection = connect_duckdb(self.database_path)
        try:
            cursor = connection.execute(sql, params or [])
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            connection.close()


def _metric_table_name(period_type: str) -> str:
    normalized = period_type.lower()
    if normalized == 'annual':
        return 'metrics_annual'
    if normalized == 'quarterly':
        return 'metrics_quarterly'
    raise ValueError("period_type must be 'annual' or 'quarterly'")

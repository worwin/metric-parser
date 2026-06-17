from __future__ import annotations

from pathlib import Path

import duckdb


SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS companies (
        cik VARCHAR PRIMARY KEY,
        ticker VARCHAR NOT NULL,
        company_name VARCHAR NOT NULL,
        latest_run_id VARCHAR,
        source_catalog_path VARCHAR,
        created_at TIMESTAMP,
        annual_period_count INTEGER,
        quarterly_period_count INTEGER,
        annual_metric_record_count INTEGER,
        quarterly_metric_record_count INTEGER,
        warning_count INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS filings (
        accession_number VARCHAR PRIMARY KEY,
        cik VARCHAR NOT NULL,
        ticker VARCHAR NOT NULL,
        company_name VARCHAR NOT NULL,
        form VARCHAR NOT NULL,
        form_family VARCHAR NOT NULL,
        filing_date DATE,
        report_period DATE,
        parser_family VARCHAR,
        validation_status VARCHAR,
        schema_version VARCHAR,
        parser_format VARCHAR,
        local_normalized_path VARCHAR,
        local_raw_filing_path VARCHAR,
        local_raw_index_path VARCHAR,
        sec_filing_url VARCHAR,
        sec_primary_document_url VARCHAR,
        raw_sha256 VARCHAR
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metric_definitions (
        metric_code VARCHAR PRIMARY KEY,
        metric_name VARCHAR NOT NULL,
        category VARCHAR NOT NULL,
        subcategory VARCHAR,
        value_type VARCHAR NOT NULL,
        unit VARCHAR,
        formula_id VARCHAR NOT NULL,
        formula_text VARCHAR NOT NULL,
        formula_version INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics_annual (
        metric_record_id VARCHAR PRIMARY KEY,
        run_id VARCHAR NOT NULL,
        ticker VARCHAR NOT NULL,
        cik VARCHAR NOT NULL,
        company_name VARCHAR NOT NULL,
        filing_period DATE,
        period_start DATE,
        period_end DATE,
        fiscal_year INTEGER NOT NULL,
        fiscal_quarter INTEGER,
        period_type VARCHAR NOT NULL,
        metric_name VARCHAR NOT NULL,
        metric_code VARCHAR NOT NULL,
        category VARCHAR NOT NULL,
        subcategory VARCHAR,
        value VARCHAR,
        numeric_value DOUBLE,
        value_type VARCHAR NOT NULL,
        unit VARCHAR,
        formula_id VARCHAR NOT NULL,
        formula_version INTEGER NOT NULL,
        formula_text VARCHAR NOT NULL,
        source_accessions_json VARCHAR,
        warnings_json VARCHAR,
        confidence DOUBLE,
        parser_warning_inherited BOOLEAN,
        applicability VARCHAR NOT NULL,
        primary_filing_accession VARCHAR,
        created_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metrics_quarterly (
        metric_record_id VARCHAR PRIMARY KEY,
        run_id VARCHAR NOT NULL,
        ticker VARCHAR NOT NULL,
        cik VARCHAR NOT NULL,
        company_name VARCHAR NOT NULL,
        filing_period DATE,
        period_start DATE,
        period_end DATE,
        fiscal_year INTEGER NOT NULL,
        fiscal_quarter INTEGER,
        period_type VARCHAR NOT NULL,
        metric_name VARCHAR NOT NULL,
        metric_code VARCHAR NOT NULL,
        category VARCHAR NOT NULL,
        subcategory VARCHAR,
        value VARCHAR,
        numeric_value DOUBLE,
        value_type VARCHAR NOT NULL,
        unit VARCHAR,
        formula_id VARCHAR NOT NULL,
        formula_version INTEGER NOT NULL,
        formula_text VARCHAR NOT NULL,
        source_accessions_json VARCHAR,
        warnings_json VARCHAR,
        confidence DOUBLE,
        parser_warning_inherited BOOLEAN,
        applicability VARCHAR NOT NULL,
        primary_filing_accession VARCHAR,
        created_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metric_warnings (
        warning_id VARCHAR PRIMARY KEY,
        metric_record_id VARCHAR,
        cik VARCHAR NOT NULL,
        ticker VARCHAR NOT NULL,
        filing_period DATE,
        fiscal_year INTEGER NOT NULL,
        fiscal_quarter INTEGER,
        period_type VARCHAR NOT NULL,
        metric_code VARCHAR,
        warning_code VARCHAR NOT NULL,
        severity VARCHAR NOT NULL,
        warning_source VARCHAR NOT NULL,
        message VARCHAR NOT NULL,
        source_accession VARCHAR,
        upstream_warning_code VARCHAR,
        created_at TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS metric_lineage (
        lineage_id VARCHAR PRIMARY KEY,
        metric_record_id VARCHAR NOT NULL,
        ticker VARCHAR NOT NULL,
        cik VARCHAR NOT NULL,
        filing_period DATE,
        fiscal_year INTEGER NOT NULL,
        fiscal_quarter INTEGER,
        period_type VARCHAR NOT NULL,
        metric_code VARCHAR NOT NULL,
        source_accession VARCHAR NOT NULL,
        source_form VARCHAR,
        concept_local_name VARCHAR NOT NULL,
        concept_qname VARCHAR,
        context_id VARCHAR,
        role VARCHAR,
        period_start DATE,
        period_end DATE,
        instant DATE,
        unit VARCHAR,
        raw_value VARCHAR,
        source_path VARCHAR,
        mapped_field_code VARCHAR
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_filings_ticker_period ON filings(ticker, report_period)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_annual_ticker_code_period ON metrics_annual(ticker, metric_code, filing_period)",
    "CREATE INDEX IF NOT EXISTS idx_metrics_quarterly_ticker_code_period ON metrics_quarterly(ticker, metric_code, filing_period)",
    "CREATE INDEX IF NOT EXISTS idx_metric_warnings_ticker_period ON metric_warnings(ticker, filing_period)",
    "CREATE INDEX IF NOT EXISTS idx_metric_lineage_metric_record_id ON metric_lineage(metric_record_id)",
)


def connect_duckdb(database_path: str | Path):
    """Open a DuckDB connection for metric storage and querying.
    
    Args:
        database_path: The database_path value.
    """
    return duckdb.connect(str(Path(database_path)))


def ensure_schema(connection) -> None:
    """Create the DuckDB metric schema if it does not already exist.
    
    Args:
        connection: The connection value.
    """
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)

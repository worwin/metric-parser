# metric-parser Phase 01 Architecture

## Mission

`metric-parser` is the financial-metric computation layer that sits between `edgar-parser` and a downstream investment-analysis engine.

Primary goals:
- use `edgar-parser` normalized outputs as input
- compute structured, auditable financial metrics
- emit canonical machine-readable artifacts
- build a derived DuckDB query layer
- make the data queryable later through a clean API and MCP-friendly interface

Primary non-goals:
- SEC filing retrieval
- raw filing parsing
- narrative scoring
- company grading
- buy, hold, or sell recommendations

## What Was Reviewed In `edgar-parser`

Reviewed sources:
- `src/edgar_parser/schemas.py`
- `src/edgar_parser/periodic_reports.py`
- `src/edgar_parser/narrative_reports.py`
- `src/edgar_parser/thirteenf.py`
- `README.md`
- parser tests
- representative normalized outputs in `_modern_form_smokes_20260329`
- post-2013 periodic samples in `_post2013_verify_20260329`

Representative normalized files inspected:
- `ticker/nvda/normalized/10k/0001045810-26-000021.json`
- `ticker/nvda/normalized/10q/0001045810-25-000230.json`
- `ticker/msft/normalized/8k/0001193125-26-027198.json`
- `ticker/msft/normalized/def14a/0001193125-25-245150.json`
- `ticker/brk-b/normalized/13f/0001193125-26-054580.json`

## Findings From `edgar-parser`

### Stable upstream contracts

`edgar-parser` already exposes stable dataclass-backed normalized contracts:
- `PeriodicReportParsedFiling` for `10-K` and `10-Q`
- `NarrativeReportParsedFiling` for `8-K` and `DEF 14A`
- `ThirteenFParsedFiling` for `13F`
- `FilingCatalogRecord` in `catalog/filings.jsonl`

That is a strong foundation for `metric-parser` because we can treat upstream JSON as contract-driven input instead of scraping free-form files.

### Form-by-form relevance

| Form | Upstream shape | Relevance to metric computation | MVP role |
| --- | --- | --- | --- |
| `10-K` | filing metadata + `facts[]` + grouped `statements` + `validation` | highest | primary annual metric source |
| `10-Q` | filing metadata + `facts[]` + grouped `statements` + `validation` | highest | primary quarterly metric source |
| `8-K` | filing metadata + `sections[]` + `validation` | indirect | filing lineage and future event annotations only |
| `DEF 14A` | filing metadata + `sections[]` + `validation` | indirect | future governance metrics only |
| `13F-HR` | filing metadata + `holdings[]` + `validation` | not relevant to issuer fundamentals | out of MVP metric computation |

Important note on `13F`:
- `13F` describes a filer's holdings portfolio, not the issuer's own operating fundamentals.
- It should not feed universal issuer-level metrics like margin, ROE, ROA, FCF, or current ratio.
- It can be preserved as future optional holdings analytics, but it should stay outside the first issuer-metrics pipeline.

### 10-K and 10-Q are the real metric inputs

Observed periodic output shape:
- top-level keys are stable: `schema_version`, `accession_number`, `cik`, `form`, `filing_date`, `report_period`, `parser_format`, `source_path`, `facts`, `statements`, `validation`
- `facts[]` include:
  - concept identity
  - context id
  - unit
  - decimals
  - period start/end or instant
  - raw value text
  - dimensions
  - `statement_hint`
- `statements` groups a selected context into:
  - `income_statement`
  - `balance_sheet`
  - `cash_flow_statement`
- `validation` gives filing-level parse quality and warnings

Downstream selection should treat `facts[]` as authoritative. The grouped
`statements` payload and `statement_hint` values are useful context and ranking
signals, but they are not completeness boundaries. Some valid equity-table or
financing facts, such as repurchases, can remain outside a statement bucket and
still be eligible for canonical field mapping.

Observed modern sample sizes:
- NVDA `10-K`: 1305 facts, 23 income rows, 64 balance-sheet rows, 6 cash-flow rows
- NVDA `10-Q`: 1058 facts, 20 income rows, 41 balance-sheet rows, 5 cash-flow rows

### Periodic parser formats appear stable enough

Across NVDA post-2013 `10-K` samples:
- 2013 to 2014: `legacy_html_tables`
- 2015 to 2019: mostly `xbrl_instance`
- 2020 to 2026: mostly `inline_xbrl`, with some `xbrl_instance`

The good news:
- parser formats vary
- output contract stays stable

That means `metric-parser` should key its logic off normalized schema, not parser format specific file layout.

### Upstream limitations that matter downstream

#### 1. `10-Q` grouped statements are often year-to-date, not standalone quarter

This is the single biggest architectural implication.

Example from NVDA `10-Q` sample:
- selected `income_statement` rows use `period_start = 2025-01-27`
- selected `period_end = 2025-10-26`
- that is nine-month year-to-date, not standalone Q3

Implication:
- `metric-parser` must implement explicit quarterization logic
- we cannot assume upstream `statements.income_statement` or `statements.cash_flow_statement` are ready-to-use standalone quarterly values

Required downstream behavior:
- Q1 can usually use the quarter directly
- Q2 and Q3 must usually be derived as current YTD minus prior YTD
- Q4 must usually be derived as annual `10-K` minus Q3 YTD `10-Q`

#### 2. Numeric values arrive as strings

Examples:
- revenue values like `"147,811"`
- share counts like `"24,304"`
- EPS like `"3.14"`

Implication:
- `metric-parser` must parse values into canonical decimals
- raw source text must still be preserved in lineage for auditability

#### 3. Inline XBRL facts are captured from normalized parser output, not re-derived from raw XBRL internals

Observed behavior in `edgar-parser`:
- inline facts use text content extracted from the filing
- units and period metadata are preserved
- the metric layer should not silently assume any richer upstream normalization than what the artifact actually provides

Implication:
- `metric-parser` should preserve:
  - upstream `parser_format`
  - upstream `unit`
  - upstream `decimals`
  - original fact `value`
- if later upstream scale handling improves, the metric layer can adapt without changing its audit model

#### 4. Many facts are dimensional

Observed in modern NVDA samples:
- roughly 40 percent to 50 percent of facts have non-empty `dimensions`

Good upstream behavior:
- `edgar-parser` statement grouping already prefers non-dimensional facts when selecting a statement bucket

Implication:
- `metric-parser` should use grouped statements as a helpful default view
- but canonical field mapping should still inspect raw `facts[]` when needed

#### 5. Post-2013 support is stronger than older support

`edgar-parser` explicitly states:
- strongest support is post-2013
- historical support exists for parts of `13F` and `10-K`

Implication:
- phase 1 metric computation should target modern post-2013 workflows first
- legacy support should be carried as best-effort with warnings, not silent equivalence

### Upstream warning vocabulary that should be inherited

Periodic-report warning codes:
- `no_facts_parsed`
- `missing_income_statement_facts`
- `missing_balance_sheet_facts`
- `missing_cash_flow_facts`
- `missing_income_statement_rows`
- `missing_balance_sheet_rows`
- `missing_cash_flow_rows`
- `no_legacy_statement_rows`
- `parse_error`

Narrative-report warning codes:
- `fallback_full_text`
- `parse_error`

13F warning codes:
- `split_row_count_mismatch`
- `entry_total_mismatch`
- `value_total_mismatch`
- `no_holdings_parsed`
- `parse_error`

Design rule:
- `metric-parser` should never discard upstream warnings
- it should carry them forward as inherited provenance on computed records

## Architecture Summary

Use a two-root model:
- code root: `metric-parser`
- data root: separate working directory, for example `D:/Projects/metric-parser-data`

Use a dual-layer storage model:
- canonical source of truth: structured metric artifacts on disk
- derived analytical query layer: DuckDB built from those artifacts

Recommended pipeline stages:
1. read `edgar-parser` catalog and normalized filing JSON
2. resolve filing periods and amendments
3. map raw facts into canonical financial fields
4. derive standalone quarterly fields where needed
5. compute metrics from canonical fields
6. write auditable JSON artifacts
7. write flat JSONL and parquet analytical exports
8. ingest parquet exports into DuckDB
9. serve query access later through a repository layer and MCP-friendly interface

## Proposed Working Data Layout

```text
metric-parser-data/
  metric-parser.toml
  runs/
    <run-id>/
      manifest.json
      inputs_snapshot.json

  snapshots/
    edgar_catalog/
      <run-id>.jsonl

  companies/
    <ticker>/
      annual/
        FY2025/
          fields.json
          metrics.json
      quarterly/
        FY2026/
          Q1/
            fields.json
            metrics.json
          Q2/
            fields.json
            metrics.json
          Q3/
            fields.json
            metrics.json
          Q4/
            fields.json
            metrics.json

  exports/
    annual_metrics.jsonl
    annual_metrics.parquet
    quarterly_metrics.jsonl
    quarterly_metrics.parquet
    metric_warnings.jsonl
    metric_warnings.parquet
    metric_definitions.json
    formula_definitions.json
    companies.jsonl
    filings.jsonl
    metric_lineage.jsonl

  db/
    metrics.duckdb
```

Why this shape:
- period-bundle JSON is easy to inspect manually
- flat exports are easy to ingest into DuckDB
- DuckDB remains rebuildable from disk artifacts
- run manifests preserve reproducibility

## Canonical Artifact Strategy

### Primary canonical artifacts

Primary source of truth should be the per-period JSON bundles:
- `companies/<ticker>/annual/FY<year>/fields.json`
- `companies/<ticker>/annual/FY<year>/metrics.json`
- `companies/<ticker>/quarterly/FY<year>/Q<q>/fields.json`
- `companies/<ticker>/quarterly/FY<year>/Q<q>/metrics.json`

Why not a single giant `annual_metrics.json`:
- it becomes hard to update incrementally
- it is awkward for audit and diff review
- large JSON arrays are poor for streaming and partial rebuilds

Flat exports should still be produced because they are query-friendly:
- `annual_metrics.jsonl`
- `quarterly_metrics.jsonl`
- parquet mirrors of both

If a downstream consumer strongly wants `annual_metrics.json`, it can be emitted later as a convenience export, not as the primary canonical store.

### Period-level intermediate artifact: `fields.json`

This layer is important.

It separates:
- raw filing facts from `edgar-parser`
- canonical financial fields used by formulas

That prevents formula logic from becoming a giant concept-name switchboard.

Suggested `fields.json` contents:
- period identity
- primary filing accession
- source accessions used
- inherited parser warnings
- canonical field records such as:
  - `revenue`
  - `gross_profit`
  - `cost_of_revenue`
  - `operating_income`
  - `net_income`
  - `total_assets`
  - `current_assets`
  - `cash_and_equivalents`
  - `short_term_investments`
  - `accounts_receivable_net`
  - `current_liabilities`
  - `total_equity`
  - `total_debt`
  - `operating_cash_flow`
  - `capital_expenditures_proxy`
  - `depreciation_and_amortization`
  - `dividends_common_cash`
  - `shares_outstanding_end`
  - `weighted_avg_shares_basic`
  - `weighted_avg_shares_diluted`

Each field record should carry:
- canonical field code
- value
- unit
- source facts
- source accession list
- selection method
- warnings

### Period-level computed artifact: `metrics.json`

Suggested top-level shape:

```json
{
  "schema_version": "0.1.0",
  "run_id": "2026-04-02T12-00-00Z",
  "ticker": "NVDA",
  "cik": "0001045810",
  "company_name": "NVIDIA CORP",
  "period_type": "annual",
  "filing_period": "2026-01-25",
  "fiscal_year": 2026,
  "fiscal_quarter": null,
  "period_start": "2025-01-27",
  "period_end": "2026-01-25",
  "primary_filing_accession": "0001045810-26-000021",
  "source_accessions": ["0001045810-26-000021"],
  "parser_warnings_inherited": [],
  "metrics": []
}
```

### Flat export artifacts

Recommended export set:
- `annual_metrics.jsonl`
- `annual_metrics.parquet`
- `quarterly_metrics.jsonl`
- `quarterly_metrics.parquet`
- `metric_warnings.jsonl`
- `metric_warnings.parquet`
- `metric_lineage.jsonl`
- `companies.jsonl`
- `filings.jsonl`
- `metric_definitions.json`
- `formula_definitions.json`

## Metric Record Schema

Use long-form records: one metric per row.

Suggested metric record fields:
- `metric_record_id`
- `run_id`
- `ticker`
- `cik`
- `company_name`
- `filing_period`
- `period_start`
- `period_end`
- `fiscal_year`
- `fiscal_quarter`
- `period_type`
- `metric_name`
- `metric_code`
- `category`
- `subcategory`
- `value`
- `value_type`
- `unit`
- `formula_id`
- `formula_version`
- `formula_text`
- `source_facts`
- `source_accessions`
- `confidence`
- `warnings`
- `parser_warning_inherited`
- `applicability`
- `primary_filing_accession`
- `created_at`

Recommended field semantics:
- `value`: decimal as string, not floating-point binary
- `value_type`: for example `currency`, `ratio`, `percent`, `count`, `per_share`
- `unit`: for example `usd_millions`, `ratio`, `percent`, `shares_millions`, `usd_per_share`
- `confidence`: decimal score such as `1.00`, `0.75`, `0.50`
- `warnings`: array of warning codes on this metric record
- `parser_warning_inherited`: boolean
- `applicability`: one of `applicable`, `limited`, `not_applicable`, `not_computable`

Recommended `source_facts` shape:

```json
[
  {
    "role": "numerator",
    "source_accession": "0001045810-26-000021",
    "source_form": "10-K",
    "concept_local_name": "NetCashProvidedByUsedInOperatingActivities",
    "context_id": "c-1",
    "period_start": "2025-01-27",
    "period_end": "2026-01-25",
    "instant": null,
    "unit": "iso4217:USD",
    "raw_value": "102,718",
    "source_path": "..."
  }
]
```

## Formula System Proposal

Use an explicit three-layer model:

1. `concept mapping`
- map upstream concepts into canonical field codes
- version this separately from formulas

2. `field derivation`
- derive quarterized fields
- derive aggregate fields like `total_debt`
- preserve lineage and warnings here

3. `metric formulas`
- compute final metrics from canonical fields only

This keeps formulas readable and auditable.

### Formula registry

Create `formula_definitions.json` with records like:
- `formula_id`
- `formula_version`
- `metric_code`
- `period_type`
- `expression_text`
- `required_fields`
- `fallback_fields`
- `notes`
- `default_warning_codes`

Example:

```json
{
  "formula_id": "roe_v1",
  "formula_version": 1,
  "metric_code": "roe",
  "period_type": "annual",
  "expression_text": "net_income / average(total_equity_current, total_equity_prior)",
  "required_fields": ["net_income", "total_equity_current", "total_equity_prior"],
  "fallback_fields": ["total_equity_current"],
  "notes": "Falls back to ending equity when prior comparable is unavailable."
}
```

### Concept mapping registry

Create a versioned mapping catalog that ranks concept aliases for each canonical field.

Examples:
- `revenue`
  - `Revenues`
  - `SalesRevenueNet`
  - `RevenueFromContractWithCustomerExcludingAssessedTax`
- `gross_profit`
  - `GrossProfit`
- `operating_income`
  - `OperatingIncomeLoss`
- `net_income`
  - `NetIncomeLoss`
- `operating_cash_flow`
  - `NetCashProvidedByUsedInOperatingActivities`
  - `NetCashProvidedByOperatingActivities`
- `shares_outstanding_end`
  - `CommonStockSharesOutstanding`
  - `EntityCommonStockSharesOutstanding`

This mapping should be declarative, not buried inside metric formulas.

## Minimum Viable Metric Set

Phase 1 metric set should focus on universal issuer fundamentals.

### Core annual and quarterly metrics

- `revenue`
- `revenue_growth`
- `gross_margin`
- `operating_margin`
- `net_margin`
- `roe`
- `roa`
- `operating_cash_flow`
- `free_cash_flow`
- `free_cash_flow_margin`
- `free_cash_flow_per_share`
- `operating_cash_flow_per_share`
- `book_value_per_share`
- `book_value_per_share_growth`
- `debt_to_capital`
- `financial_leverage`
- `current_ratio`
- `quick_ratio`
- `share_count_trend`
- `dividend_payout_ratio`
- `owners_earnings_approx`

Added intentionally:
- `free_cash_flow_margin`

Reason:
- it appears directly in the target query examples and uses the same MVP inputs as `free_cash_flow`

### Recommended phase 1 formula semantics

- `revenue`
  - annual: fiscal-year revenue from `10-K`
  - quarterly: standalone quarter revenue after quarterization when needed

- `revenue_growth`
  - annual: current FY revenue vs prior FY revenue
  - quarterly: standalone quarter revenue vs same fiscal quarter prior year

- `gross_margin`
  - `gross_profit / revenue`
  - fallback: `(revenue - cost_of_revenue) / revenue`

- `operating_margin`
  - `operating_income / revenue`

- `net_margin`
  - `net_income / revenue`

- `roe`
  - annual: `net_income / average_equity`
  - quarterly: `annualized_quarter_net_income / average_quarter_equity`
  - fallback: ending equity with warning

- `roa`
  - annual: `net_income / average_assets`
  - quarterly: `annualized_quarter_net_income / average_quarter_assets`
  - fallback: ending assets with warning

- `operating_cash_flow`
  - direct field

- `free_cash_flow`
  - `operating_cash_flow - capital_expenditures_proxy`

- `free_cash_flow_margin`
  - `free_cash_flow / revenue`

- `free_cash_flow_per_share`
  - `free_cash_flow / diluted_weighted_avg_shares`
  - fallback to basic shares or ending shares with warning

- `operating_cash_flow_per_share`
  - `operating_cash_flow / diluted_weighted_avg_shares`
  - fallback to basic shares or ending shares with warning

- `book_value_per_share`
  - `total_equity / ending_common_shares_outstanding`
  - fallback to weighted-average shares with warning

- `book_value_per_share_growth`
  - current BVPS vs prior comparable period BVPS

- `debt_to_capital`
  - `total_debt / (total_debt + total_equity)`

- `financial_leverage`
  - `average_assets / average_equity`
  - fallback to ending balances with warning

- `current_ratio`
  - `current_assets / current_liabilities`

- `quick_ratio`
  - `(cash_and_equivalents + short_term_investments + accounts_receivable_net) / current_liabilities`
  - missing components can reduce confidence or prevent computation

- `share_count_trend`
  - ending common shares outstanding vs prior comparable period
  - fallback to weighted-average shares with warning

- `dividend_payout_ratio`
  - `common_dividends_cash / net_income`

- `owners_earnings_approx`
  - preferred: `net_income + depreciation_and_amortization - capital_expenditures_proxy`
  - fallback: `operating_cash_flow - capital_expenditures_proxy`
  - always warn that maintenance capex is unavailable

### Metrics to defer

Do not make phase 1 depend on:
- bank-specific metrics
- insurer-specific metrics
- REIT-specific metrics
- commodity reserve metrics
- valuation metrics that require market prices
- recommendation scores

## Caveat Model

Every metric record should be able to carry structured caveats.

Recommended warning record fields:
- `warning_id`
- `metric_record_id`
- `warning_code`
- `severity`
- `warning_source`
- `message`
- `source_accession`
- `upstream_warning_code`
- `created_at`

Recommended warning sources:
- `parser`
- `mapping`
- `quarterization`
- `formula`
- `applicability`

Recommended phase 1 warning codes:
- `parser_warning_inherited`
- `source_filing_warn_status`
- `average_balance_unavailable_used_ending_balance`
- `quarter_derived_from_ytd_delta`
- `quarter_derived_from_10k_minus_q3_ytd`
- `missing_prior_comparable`
- `missing_required_source_fact`
- `gross_margin_derived_from_cost_of_revenue`
- `capex_proxy_used`
- `maintenance_capex_unavailable`
- `share_count_fallback_to_weighted_average`
- `shares_outstanding_missing`
- `equity_proxy_used`
- `debt_proxy_used`
- `metric_not_applicable_business_type`
- `negative_or_zero_denominator`
- `amended_filing_preferred`
- `comparison_period_from_amended_filing`
- `buybacks_may_distort_roe`

Recommended warning behavior:
- warnings are additive, not exclusive
- inherited upstream warnings should remain visible
- warnings should affect `confidence`, but not automatically suppress output
- use `applicability = not_computable` when required inputs are missing

## DuckDB Query Layer

DuckDB is a derived analytical layer, not the only source of truth.

Recommended build rule:
- canonical JSON bundle on disk is primary
- flat parquet exports are derived from canonical JSON
- DuckDB tables are derived from parquet exports
- a full rebuild of DuckDB must be possible without touching SEC raw filings

### Recommended tables

#### `companies`

One row per company identity.

Suggested columns:
- `cik` primary key
- `ticker`
- `company_name`
- `latest_company_name`
- `first_seen_filing_date`
- `last_seen_filing_date`
- `created_at`
- `updated_at`

#### `filings`

One row per parsed filing from `edgar-parser`.

Suggested columns:
- `accession_number` primary key
- `cik`
- `ticker`
- `company_name`
- `form`
- `filing_date`
- `report_period`
- `fiscal_year`
- `fiscal_quarter`
- `period_type`
- `parser_family`
- `parser_format`
- `validation_status`
- `local_normalized_path`
- `sec_filing_url`
- `sec_primary_document_url`
- `raw_sha256`
- `is_amendment`
- `supersedes_accession`
- `created_at`

#### `metric_definitions`

One row per metric code.

Suggested columns:
- `metric_code` primary key
- `metric_name`
- `category`
- `subcategory`
- `description`
- `default_unit`
- `default_value_type`
- `supported_period_types`
- `applicability_notes`
- `introduced_in_version`

#### `formula_definitions`

One row per formula version.

Suggested columns:
- `formula_id` primary key
- `formula_version`
- `metric_code`
- `period_type`
- `expression_text`
- `required_fields_json`
- `fallback_fields_json`
- `notes`
- `effective_from`

#### `metrics_annual`

Long-form annual metric table.

Suggested columns:
- `metric_record_id` primary key
- `cik`
- `ticker`
- `company_name`
- `filing_period`
- `period_start`
- `period_end`
- `fiscal_year`
- `metric_code`
- `metric_name`
- `category`
- `subcategory`
- `value`
- `value_type`
- `unit`
- `formula_id`
- `formula_version`
- `confidence`
- `applicability`
- `parser_warning_inherited`
- `warning_count`
- `primary_filing_accession`
- `source_accessions_json`
- `created_at`

#### `metrics_quarterly`

Same shape as `metrics_annual`, plus:
- `fiscal_quarter`
- `quarterization_method`

#### `metric_warnings`

One row per warning attached to a metric record or period.

Suggested columns:
- `warning_id` primary key
- `metric_record_id`
- `cik`
- `ticker`
- `fiscal_year`
- `fiscal_quarter`
- `period_type`
- `metric_code`
- `warning_code`
- `severity`
- `warning_source`
- `message`
- `source_accession`
- `upstream_warning_code`
- `created_at`

#### `metric_lineage`

One row per source fact used by one metric record.

Suggested columns:
- `lineage_id` primary key
- `metric_record_id`
- `cik`
- `ticker`
- `metric_code`
- `lineage_role`
- `source_accession`
- `source_form`
- `source_concept_qname`
- `source_concept_local_name`
- `source_context_id`
- `source_period_start`
- `source_period_end`
- `source_instant`
- `source_unit`
- `source_value_raw`
- `mapped_field_code`
- `source_path`

### Query examples this schema supports cleanly

All annual metrics for a ticker:

```sql
select *
from metrics_annual
where ticker = 'V'
order by fiscal_year, metric_code;
```

All quarterly metrics for a ticker:

```sql
select *
from metrics_quarterly
where ticker = 'V'
order by fiscal_year, fiscal_quarter, metric_code;
```

ROE history for Visa:

```sql
select fiscal_year, value, unit, confidence
from metrics_annual
where ticker = 'V'
  and metric_code = 'roe'
order by fiscal_year;
```

Latest FCF margin for a company:

```sql
select fiscal_year, fiscal_quarter, period_type, value
from (
  select fiscal_year, null as fiscal_quarter, 'annual' as period_type, filing_period, value
  from metrics_annual
  where ticker = 'V' and metric_code = 'free_cash_flow_margin'
  union all
  select fiscal_year, fiscal_quarter, 'quarterly' as period_type, filing_period, value
  from metrics_quarterly
  where ticker = 'V' and metric_code = 'free_cash_flow_margin'
)
order by filing_period desc
limit 1;
```

All warnings affecting a ticker:

```sql
select *
from metric_warnings
where ticker = 'V'
order by created_at desc;
```

All source filings used for one metric record:

```sql
select distinct source_accession, source_form
from metric_lineage
where metric_record_id = ?;
```

## Build and Update Pipeline

### Stage 1. Ingest `edgar-parser` outputs

Inputs:
- `catalog/filings.jsonl`
- normalized filing JSON paths from catalog

Rules:
- use catalog as the authoritative index
- do not crawl raw SEC folders as primary discovery
- filter `10-K`, `10-K/A`, `10-Q`, `10-Q/A` for metric computation
- ingest `8-K`, `DEF 14A`, and `13F` metadata into lineage tables only for now

### Stage 2. Resolve filing identity and amendments

Rules:
- group filings by `cik + form family + report_period`
- prefer amended filings over originals for the same period
- preserve superseded filings in `filings`
- record which accession became the primary metric source

### Stage 3. Map concepts to canonical fields

Rules:
- use a declarative concept ranking registry
- emit a `fields.json` artifact for each period
- preserve all source facts chosen
- attach warnings when using fallback concepts or proxies

### Stage 4. Quarterize periodic flows

Rules:
- detect whether a `10-Q` flow is standalone quarter or YTD
- derive standalone quarters when needed
- preserve the quarterization method on every affected field and metric

Recommended quarterization methods:
- `direct_quarter`
- `current_ytd_minus_prior_ytd`
- `annual_minus_q3_ytd`
- `unavailable`

### Stage 5. Compute metrics

Rules:
- compute metrics only from canonical fields
- apply formula registry by metric code and period type
- compute confidence and warnings explicitly
- do not impute missing required fields silently

### Stage 6. Write canonical artifacts

Write:
- period `fields.json`
- period `metrics.json`
- run manifest

### Stage 7. Write analytical exports

Write:
- annual JSONL and parquet
- quarterly JSONL and parquet
- warnings JSONL and parquet
- lineage JSONL
- definitions JSON

### Stage 8. Ingest DuckDB

Rules:
- load from exports, not directly from raw SEC or parser internals
- allow full rebuild
- allow idempotent incremental upsert by `metric_record_id`

### Stage 9. Expose query service later

Build a thin repository layer on top of DuckDB first:
- parameterized SQL only
- typed result objects
- reusable query methods

Then expose that repository through MCP tools.

## MCP-Friendly Access Plan

Do not start with arbitrary SQL execution as the public agent interface.

Start with a narrow query API:
- `get_company(ticker_or_cik)`
- `get_annual_metrics(ticker, metric_codes=None, year_from=None, year_to=None)`
- `get_quarterly_metrics(ticker, metric_codes=None, limit=None)`
- `get_metric_history(ticker, metric_code, period_type)`
- `get_latest_metric(ticker, metric_code)`
- `get_metric_warnings(ticker, metric_code=None)`
- `get_metric_lineage(metric_record_id)`
- `list_filings_for_period(ticker, fiscal_year, fiscal_quarter=None)`

Why this is MCP-friendly:
- stable tool shapes
- safe parameterization
- predictable JSON output
- easy to attach warning and lineage payloads
- easy for downstream agents to consume

Suggested output style for MCP tools:
- return metric records in the same long-form schema as canonical artifacts
- include warning summaries
- include lineage on demand, not always inline

## Recommended Repo Structure

For the code repo itself:

```text
metric-parser/
  README.md
  docs/
    phase-01-architecture.md
  src/
    metric_parser/
      ingest/
      mapping/
      quarterization/
      compute/
      artifacts/
      db/
      query/
      mcp/
  schemas/
    metric_record.schema.json
    metric_warning.schema.json
    period_fields.schema.json
    metrics_bundle.schema.json
  configs/
    concept_aliases/
    formulas/
```

Suggested module responsibilities:
- `ingest/`
  - read catalog
  - load normalized filings
  - resolve amendments
- `mapping/`
  - concept alias registry
  - canonical field selection
- `quarterization/`
  - derive standalone quarter fields
- `compute/`
  - metric formulas
  - confidence scoring
  - warning generation
- `artifacts/`
  - JSON writer
  - parquet writer
  - run manifest writer
- `db/`
  - DuckDB schema
  - loaders
  - migrations
- `query/`
  - typed repository methods
- `mcp/`
  - future MCP tool surface

## Scope Boundaries To Keep Clean

`metric-parser` should own:
- metric computation
- formula definitions
- field mapping rules
- caveat generation
- metric lineage
- canonical output artifacts
- DuckDB query layer
- MCP-friendly query access later

`metric-parser` should not own:
- SEC network retrieval
- raw SEC parsing
- free-form narrative interpretation as investment judgment
- Buffett compliance decisions
- buy, hold, or sell outputs
- labeling a metric as excellent, poor, elite, or weak
- composite scoring systems in phase 1

## Recommended Phase 1 Decision Summary

1. Treat `10-K` and `10-Q` as the only numeric metric inputs in MVP.
2. Use `8-K` and `DEF 14A` as lineage-only inputs for now.
3. Keep `13F` out of issuer-fundamentals metrics in MVP.
4. Make period-bundle JSON the canonical source of truth.
5. Emit flat JSONL and parquet as analytical exports.
6. Build DuckDB only from those artifacts.
7. Introduce an explicit canonical field layer before formulas.
8. Implement quarterization as a first-class stage, not an afterthought.
9. Carry upstream parser warnings forward unchanged.
10. Keep the repo boundary strictly analytical, not judgmental.

## Next Implementation Steps

Recommended order for phase 2 implementation:

1. create artifact schemas for:
   - `period_fields`
   - `metrics_bundle`
   - `metric_record`
   - `metric_warning`
2. implement catalog-driven filing ingestion
3. implement periodic concept mapping for the MVP field set
4. implement quarterly derivation logic
5. implement the MVP metric formulas
6. write JSON bundles and flat JSONL/parquet exports
7. build DuckDB loader and query repository
8. add MCP-facing query methods last

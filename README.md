# metric-parser

`metric-parser` sits between `edgar-parser` and a downstream investment-analysis engine.

Its job is to:
- read normalized filing outputs produced by `edgar-parser`
- map filing facts into canonical financial fields
- compute auditable financial metrics
- write canonical machine-readable artifacts
- build a derived DuckDB query layer
- support future MCP-friendly querying

It does not:
- fetch SEC filings
- parse raw SEC text
- score companies
- assign grades
- emit buy, hold, or sell decisions

Current status:
- phase 2 implementation is underway
- canonical artifact schemas are defined under `schemas/`
- typed artifact and ingestion models live under `src/metric_parser/`
- periodic filing ingestion and amendment-aware selection are implemented
- canonical field selection is implemented for the MVP field set
- fiscal-quarter inference and standalone-quarter derivation are implemented
- long-form metric bundle computation is implemented for the MVP metric set
- canonical artifact writing is implemented
- DuckDB schema creation, artifact ingestion, and query helpers are implemented

See [docs/phase-01-architecture.md](docs/phase-01-architecture.md) for the architecture proposal.
See [docs/phase-02-metric-signoff.md](docs/phase-02-metric-signoff.md) for the current validation/signoff workflow.

Current package areas:
- `src/metric_parser/ingest/`
- `src/metric_parser/mapping/`
- `src/metric_parser/quarterization/`
- `src/metric_parser/compute/`
- `src/metric_parser/artifacts/`
- `src/metric_parser/db/`
- `src/metric_parser/query/`
- `src/metric_parser/models.py`
- `schemas/*.schema.json`

Basic local test command:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
```

DuckDB review flow:

```powershell
$env:PYTHONPATH='src'
@'
from pathlib import Path
from metric_parser import (
    build_company_metric_history,
    ingest_company_artifact_directories,
    load_catalog_records,
    MetricQueryService,
    write_company_metric_artifacts,
)

root = Path(r'D:\Projects\metric-parser')
review_root = root / '.tmp-tests' / 'review'
db_path = review_root / 'metrics.duckdb'
review_root.mkdir(parents=True, exist_ok=True)

catalog_sets = {
    'nvda': [
        Path(r'D:\Projects\edgar-parser\_post2013_verify_20260329\catalog\filings.jsonl'),
        Path(r'D:\Projects\edgar-parser\_modern_form_smokes_20260329\catalog\filings.jsonl'),
    ],
    'v': [
        Path(r'D:\Projects\edgar-parser\_multi_verify_20260329\catalog\filings.jsonl'),
    ],
}
artifact_dirs = []
for ticker, catalog_paths in catalog_sets.items():
    records = []
    for catalog_path in catalog_paths:
        records.extend(load_catalog_records(catalog_path))
    records = [record for record in records if f'ticker/{ticker}/' in (record.local_normalized_path or '').replace('\\', '/').lower()]
    build = build_company_metric_history(run_id=f'review-{ticker}', records=records)
    artifact_dir = review_root / ticker
    write_company_metric_artifacts(artifact_dir, build)
    artifact_dirs.append(artifact_dir)

ingest_company_artifact_directories(db_path, artifact_dirs)
query = MetricQueryService(db_path)
print(query.get_latest_metric('NVDA', 'free_cash_flow_margin'))
print(query.get_metric_history('V', 'roe', 'annual')[-3:])
'@ | python -
```

Metric signoff flow:

```powershell
$env:PYTHONPATH='src'
@'
from pathlib import Path
from metric_parser import ValidationCompanyTarget, build_validation_report

build_validation_report(
    run_id='signoff-local',
    company_targets=[
        ValidationCompanyTarget('NVDA', [
            r'D:\Projects\edgar-parser\_post2013_verify_20260329\catalog\filings.jsonl',
            r'D:\Projects\edgar-parser\_modern_form_smokes_20260329\catalog\filings.jsonl',
        ]),
        ValidationCompanyTarget('AAPL', [r'D:\Projects\edgar-parser\_multi_verify_20260329\catalog\filings.jsonl']),
        ValidationCompanyTarget('MSFT', [r'D:\Projects\edgar-parser\_multi_verify_20260329\catalog\filings.jsonl']),
        ValidationCompanyTarget('BRK-B', [r'D:\Projects\edgar-parser\_multi_verify_20260329\catalog\filings.jsonl']),
        ValidationCompanyTarget('OXY', [r'D:\Projects\edgar-parser\_multi_verify_20260329\catalog\filings.jsonl']),
        ValidationCompanyTarget('V', [r'D:\Projects\edgar-parser\_multi_verify_20260329\catalog\filings.jsonl']),
    ],
    output_root=Path(r'D:\Projects\metric-parser\.tmp-tests\signoff'),
)
'@ | python -
```

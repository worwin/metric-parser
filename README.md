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
- phase 1 architecture and schema design

See [docs/phase-01-architecture.md](docs/phase-01-architecture.md) for the initial design proposal.

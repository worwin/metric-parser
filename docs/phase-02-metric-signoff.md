# Phase 02 Metric Signoff

`metric-parser` now includes a cohort-based signoff layer so we can validate whether a metric is ready to feed downstream analysis.

This is intentionally separate from Buffett-style scoring. The goal here is only to answer:

- does the metric compute on real company histories?
- how much recent-history coverage do we have?
- how warning-heavy is the current implementation?
- is the metric ready, caveated, or still blocked by mapping/coverage gaps?

## Validation Scope

Current validation cohort:

- `NVDA`
- `AAPL`
- `MSFT`
- `BRK-B`
- `OXY`
- `V`

Current validation windows:

- annual: latest `5` annual periods
- quarterly: latest `4` quarterly periods

Status values:

- `solid`
  Broad recent-history coverage with low approximation pressure.
- `usable_with_caveats`
  Computable and useful, but warnings or partial coverage still matter.
- `needs_refinement`
  Too much missing data or too little reliable recent-history coverage.
- `not_tested`
  Not enough relevant histories in the current cohort.

## Current Findings

The current signoff run is useful, but it does **not** yet justify calling the whole metric layer production-signed-off for Buffett-style historical analysis.

Main findings:

- latest-period annual coverage is materially better than historical continuity
  Example: `revenue`, `free_cash_flow`, `roe`, `eps_diluted`, and `net_debt` compute for most latest annual company snapshots in the cohort.
- multi-year annual history is still weak for several non-NVIDIA names
  This is most visible in older or legacy-style parsed outputs where key fields are still missing for 2021-2024 windows.
- profitability fields are especially uneven across business models
  `gross_margin` is not broadly available with the current mapping set because many filings do not expose a straightforward gross-profit structure that matches the current canonical aliases.
- quarterly signoff is not a strong gating signal yet
  The current local cohort has meaningful quarterly history mainly for `NVDA`, so quarterly validation should be treated as informative but not decisive.

In practical terms:

- `metric-parser` is now strong enough to continue validating and hardening.
- `metric-parser` is **not** yet fully signed off as the historical-metric backbone for `buffett-analyzer`.

## Review Artifacts

Current generated signoff outputs live under:

- `D:\Projects\metric-parser\.tmp-tests\signoff\metric_signoff_report.json`
- `D:\Projects\metric-parser\.tmp-tests\signoff\metric_signoff_report.md`
- `D:\Projects\metric-parser\.tmp-tests\signoff\metrics.duckdb`

Per-company refreshed artifacts live under:

- `D:\Projects\metric-parser\.tmp-tests\signoff\nvda`
- `D:\Projects\metric-parser\.tmp-tests\signoff\aapl`
- `D:\Projects\metric-parser\.tmp-tests\signoff\msft`
- `D:\Projects\metric-parser\.tmp-tests\signoff\brk-b`
- `D:\Projects\metric-parser\.tmp-tests\signoff\oxy`
- `D:\Projects\metric-parser\.tmp-tests\signoff\v`

## Run Flow

From `metric-parser`:

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

## Recommended Next Work

Before starting serious Buffett scoring logic, the next hardening steps should be:

1. Expand annual concept coverage for legacy and non-product-company filings.
2. Validate why `MSFT` latest annual revenue and several profitability fields are still not computing.
3. Improve gross-profit / cost-of-revenue mapping strategy for service and financial-style reporters.
4. Decide whether `buffett-analyzer` v1 should consume only annual metrics with explicit signoff, rather than all available metrics.

The key point is that the signoff system is now in place and repeatable, even though the current cohort results still show real coverage gaps that need work.

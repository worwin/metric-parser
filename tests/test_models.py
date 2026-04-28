from __future__ import annotations

import unittest

from metric_parser.models import CanonicalFieldRecord
from metric_parser.models import MetricRecord
from metric_parser.models import MetricSourceFact
from metric_parser.models import MetricWarningRecord
from metric_parser.models import MetricsBundleArtifact
from metric_parser.models import PeriodArtifactIdentity
from metric_parser.models import PeriodFieldsArtifact


class ModelSerializationTests(unittest.TestCase):
    def test_period_fields_artifact_serializes_expected_shape(self) -> None:
        identity = PeriodArtifactIdentity(
            ticker="NVDA",
            cik="0001045810",
            company_name="NVIDIA CORP",
            filing_period="2026-01-25",
            period_type="annual",
            fiscal_year=2026,
            fiscal_quarter=None,
            period_start="2025-01-27",
            period_end="2026-01-25",
            primary_filing_accession="0001045810-26-000021",
            source_accessions=["0001045810-26-000021"],
        )
        source_fact = MetricSourceFact(
            role="primary",
            source_accession="0001045810-26-000021",
            source_form="10-K",
            concept_local_name="Revenues",
            raw_value="130,497",
        )
        field_record = CanonicalFieldRecord(
            field_code="revenue",
            field_name="Revenue",
            value="130497",
            unit="usd_millions",
            value_type="currency",
            selection_method="concept_alias_rank_1",
            confidence="1.00",
            source_facts=[source_fact],
        )

        artifact = PeriodFieldsArtifact(
            run_id="run-001",
            identity=identity,
            parser_warnings_inherited=["missing_cash_flow_facts"],
            fields=[field_record],
        )

        data = artifact.to_dict()
        self.assertEqual(data["ticker"], "NVDA")
        self.assertEqual(data["fields"][0]["field_code"], "revenue")
        self.assertEqual(data["fields"][0]["source_facts"][0]["concept_local_name"], "Revenues")

    def test_metrics_bundle_artifact_serializes_expected_shape(self) -> None:
        identity = PeriodArtifactIdentity(
            ticker="NVDA",
            cik="0001045810",
            company_name="NVIDIA CORP",
            filing_period="2026-01-25",
            period_type="annual",
            fiscal_year=2026,
            fiscal_quarter=None,
            primary_filing_accession="0001045810-26-000021",
            source_accessions=["0001045810-26-000021"],
        )
        source_fact = MetricSourceFact(
            role="numerator",
            source_accession="0001045810-26-000021",
            source_form="10-K",
            concept_local_name="NetIncomeLoss",
            raw_value="72880",
        )
        metric_record = MetricRecord(
            metric_record_id="metric-001",
            run_id="run-001",
            ticker="NVDA",
            cik="0001045810",
            company_name="NVIDIA CORP",
            filing_period="2026-01-25",
            period_start="2025-01-27",
            period_end="2026-01-25",
            fiscal_year=2026,
            fiscal_quarter=None,
            period_type="annual",
            metric_name="Return on Equity",
            metric_code="roe",
            category="profitability",
            subcategory="returns",
            value="0.52",
            value_type="ratio",
            unit="ratio",
            formula_id="roe_v1",
            formula_version=1,
            formula_text="net_income / average_equity",
            source_facts=[source_fact],
            source_accessions=["0001045810-26-000021"],
            created_at="2026-04-02T10:00:00Z",
        )
        warning_record = MetricWarningRecord(
            warning_id="warn-001",
            metric_record_id="metric-001",
            cik="0001045810",
            ticker="NVDA",
            filing_period="2026-01-25",
            fiscal_year=2026,
            fiscal_quarter=None,
            period_type="annual",
            metric_code="roe",
            warning_code="average_balance_unavailable_used_ending_balance",
            severity="warning",
            warning_source="formula",
            message="Average equity unavailable; used ending equity.",
            created_at="2026-04-02T10:00:00Z",
        )

        artifact = MetricsBundleArtifact(
            run_id="run-001",
            identity=identity,
            metrics=[metric_record],
            warnings=[warning_record],
        )

        data = artifact.to_dict()
        self.assertEqual(data["metrics"][0]["metric_code"], "roe")
        self.assertEqual(data["warnings"][0]["warning_code"], "average_balance_unavailable_used_ending_balance")


if __name__ == "__main__":
    unittest.main()


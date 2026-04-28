from __future__ import annotations

import unittest

from metric_parser.schema_registry import get_schema_path
from metric_parser.schema_registry import list_schema_names
from metric_parser.schema_registry import load_schema


class SchemaRegistryTests(unittest.TestCase):
    def test_list_schema_names_includes_expected_contracts(self) -> None:
        names = list_schema_names()
        self.assertIn("metric_record", names)
        self.assertIn("metric_warning", names)
        self.assertIn("period_fields", names)
        self.assertIn("metrics_bundle", names)

    def test_load_schema_returns_metric_record_contract(self) -> None:
        schema = load_schema("metric_record")
        self.assertEqual(schema["title"], "Metric Record")
        self.assertIn("metric_record_id", schema["properties"])

    def test_get_schema_path_returns_existing_file(self) -> None:
        path = get_schema_path("period_fields")
        self.assertTrue(path.exists())
        self.assertEqual(path.name, "period_fields.schema.json")


if __name__ == "__main__":
    unittest.main()


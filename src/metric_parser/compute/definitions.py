from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_code: str
    metric_name: str
    category: str
    subcategory: str
    value_type: str
    unit: str | None
    formula_id: str
    formula_text: str


METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition("revenue", "Revenue", "income_statement", "top_line", "currency", "usd", "revenue_v1", "revenue"),
    MetricDefinition("revenue_growth", "Revenue Growth", "growth", "top_line", "ratio", "ratio", "revenue_growth_v1", "revenue / prior_revenue - 1"),
    MetricDefinition("gross_margin", "Gross Margin", "profitability", "margin", "ratio", "ratio", "gross_margin_v1", "gross_profit / revenue"),
    MetricDefinition("operating_margin", "Operating Margin", "profitability", "margin", "ratio", "ratio", "operating_margin_v1", "operating_income / revenue"),
    MetricDefinition("net_margin", "Net Margin", "profitability", "margin", "ratio", "ratio", "net_margin_v1", "net_income / revenue"),
    MetricDefinition("roe", "Return on Equity", "profitability", "returns", "ratio", "ratio", "roe_v1", "net_income / average_equity"),
    MetricDefinition("roa", "Return on Assets", "profitability", "returns", "ratio", "ratio", "roa_v1", "net_income / average_assets"),
    MetricDefinition("operating_cash_flow", "Operating Cash Flow", "cash_flow", "core", "currency", "usd", "operating_cash_flow_v1", "operating_cash_flow"),
    MetricDefinition("free_cash_flow", "Free Cash Flow", "cash_flow", "core", "currency", "usd", "free_cash_flow_v1", "operating_cash_flow - capital_expenditures_proxy"),
    MetricDefinition("free_cash_flow_margin", "Free Cash Flow Margin", "cash_flow", "margin", "ratio", "ratio", "free_cash_flow_margin_v1", "free_cash_flow / revenue"),
    MetricDefinition("free_cash_flow_per_share", "Free Cash Flow Per Share", "per_share", "cash_flow", "per_share", "usd_per_share", "free_cash_flow_per_share_v1", "free_cash_flow / share_base"),
    MetricDefinition("operating_cash_flow_per_share", "Operating Cash Flow Per Share", "per_share", "cash_flow", "per_share", "usd_per_share", "operating_cash_flow_per_share_v1", "operating_cash_flow / share_base"),
    MetricDefinition("book_value_per_share", "Book Value Per Share", "per_share", "balance_sheet", "per_share", "usd_per_share", "book_value_per_share_v1", "total_equity / ending_shares"),
    MetricDefinition("book_value_per_share_growth", "Book Value Per Share Growth", "growth", "per_share", "ratio", "ratio", "book_value_per_share_growth_v1", "book_value_per_share / prior_book_value_per_share - 1"),
    MetricDefinition("debt_to_capital", "Debt to Capital", "solvency", "leverage", "ratio", "ratio", "debt_to_capital_v1", "total_debt / (total_debt + total_equity)"),
    MetricDefinition("financial_leverage", "Financial Leverage", "solvency", "leverage", "ratio", "ratio", "financial_leverage_v1", "average_assets / average_equity"),
    MetricDefinition("current_ratio", "Current Ratio", "liquidity", "working_capital", "ratio", "ratio", "current_ratio_v1", "current_assets / current_liabilities"),
    MetricDefinition("quick_ratio", "Quick Ratio", "liquidity", "working_capital", "ratio", "ratio", "quick_ratio_v1", "(cash_and_equivalents + short_term_investments + accounts_receivable_net) / current_liabilities"),
    MetricDefinition("share_count_trend", "Share Count Trend", "capital_structure", "shares", "ratio", "ratio", "share_count_trend_v1", "ending_shares / prior_ending_shares - 1"),
    MetricDefinition("dividend_payout_ratio", "Dividend Payout Ratio", "capital_allocation", "dividends", "ratio", "ratio", "dividend_payout_ratio_v1", "dividends_common_cash / net_income"),
    MetricDefinition("owners_earnings_approx", "Owners Earnings Approximation", "cash_flow", "owner_earnings", "currency", "usd", "owners_earnings_approx_v1", "net_income + depreciation_and_amortization - capital_expenditures_proxy"),
)


METRIC_DEFINITION_BY_CODE = {definition.metric_code: definition for definition in METRIC_DEFINITIONS}

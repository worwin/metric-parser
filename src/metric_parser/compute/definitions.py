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
    MetricDefinition("net_income_growth", "Net Income Growth", "growth", "bottom_line", "ratio", "ratio", "net_income_growth_v1", "net_income / prior_net_income - 1"),
    MetricDefinition("gross_profit", "Gross Profit", "income_statement", "profitability", "currency", "usd", "gross_profit_v1", "gross_profit"),
    MetricDefinition("cost_of_revenue", "Cost of Revenue", "income_statement", "costs", "currency", "usd", "cost_of_revenue_v1", "cost_of_revenue"),
    MetricDefinition("selling_general_and_administrative", "Selling, General and Administrative", "income_statement", "costs", "currency", "usd", "selling_general_and_administrative_v1", "selling_general_and_administrative"),
    MetricDefinition("research_and_development", "Research and Development", "income_statement", "costs", "currency", "usd", "research_and_development_v1", "research_and_development"),
    MetricDefinition("operating_expenses", "Operating Expenses", "income_statement", "costs", "currency", "usd", "operating_expenses_v1", "operating_expenses"),
    MetricDefinition("other_income_expense", "Other Income Expense", "income_statement", "non_operating", "currency", "usd", "other_income_expense_v1", "other_income_expense"),
    MetricDefinition("gross_margin", "Gross Margin", "profitability", "margin", "ratio", "ratio", "gross_margin_v1", "gross_profit / revenue"),
    MetricDefinition("operating_margin", "Operating Margin", "profitability", "margin", "ratio", "ratio", "operating_margin_v1", "operating_income / revenue"),
    MetricDefinition("net_margin", "Net Margin", "profitability", "margin", "ratio", "ratio", "net_margin_v1", "net_income / revenue"),
    MetricDefinition("operating_expenses_to_gross_profit", "Operating Expenses to Gross Profit", "profitability", "cost_structure", "ratio", "ratio", "operating_expenses_to_gross_profit_v1", "operating_expenses / gross_profit"),
    MetricDefinition("sga_to_gross_profit", "SG&A to Gross Profit", "profitability", "cost_structure", "ratio", "ratio", "sga_to_gross_profit_v1", "selling_general_and_administrative / gross_profit"),
    MetricDefinition("r_and_d_to_gross_profit", "R&D to Gross Profit", "profitability", "cost_structure", "ratio", "ratio", "r_and_d_to_gross_profit_v1", "research_and_development / gross_profit"),
    MetricDefinition("depreciation_to_gross_profit", "Depreciation and Amortization to Gross Profit", "profitability", "cost_structure", "ratio", "ratio", "depreciation_to_gross_profit_v1", "depreciation_and_amortization / gross_profit"),
    MetricDefinition("interest_expense_to_operating_income", "Interest Expense to Operating Income", "solvency", "coverage", "ratio", "ratio", "interest_expense_to_operating_income_v1", "abs(interest_expense) / operating_income"),
    MetricDefinition("tax_rate_effective", "Effective Tax Rate", "profitability", "tax", "ratio", "ratio", "tax_rate_effective_v1", "income_tax_expense / income_before_tax"),
    MetricDefinition("roe", "Return on Equity", "profitability", "returns", "ratio", "ratio", "roe_v1", "net_income / average_equity"),
    MetricDefinition("roa", "Return on Assets", "profitability", "returns", "ratio", "ratio", "roa_v1", "net_income / average_assets"),
    MetricDefinition("roic", "Return on Invested Capital", "profitability", "returns", "ratio", "ratio", "roic_v1", "nopat / average_invested_capital"),
    MetricDefinition("operating_cash_flow", "Operating Cash Flow", "cash_flow", "core", "currency", "usd", "operating_cash_flow_v1", "operating_cash_flow"),
    MetricDefinition("cash_from_investing", "Cash From Investing", "cash_flow", "core", "currency", "usd", "cash_from_investing_v1", "cash_from_investing"),
    MetricDefinition("cash_from_financing", "Cash From Financing", "cash_flow", "core", "currency", "usd", "cash_from_financing_v1", "cash_from_financing"),
    MetricDefinition("net_change_in_cash", "Net Change In Cash", "cash_flow", "core", "currency", "usd", "net_change_in_cash_v1", "net_change_in_cash"),
    MetricDefinition("capital_expenditures", "Capital Expenditures", "cash_flow", "capital_spending", "currency", "usd", "capital_expenditures_v1", "capital_expenditures_proxy"),
    MetricDefinition("free_cash_flow", "Free Cash Flow", "cash_flow", "core", "currency", "usd", "free_cash_flow_v1", "operating_cash_flow - capital_expenditures_proxy"),
    MetricDefinition("free_cash_flow_growth", "Free Cash Flow Growth", "growth", "cash_flow", "ratio", "ratio", "free_cash_flow_growth_v1", "free_cash_flow / prior_free_cash_flow - 1"),
    MetricDefinition("free_cash_flow_margin", "Free Cash Flow Margin", "cash_flow", "margin", "ratio", "ratio", "free_cash_flow_margin_v1", "free_cash_flow / revenue"),
    MetricDefinition("cash_conversion_ocf_to_net_income", "Cash Conversion OCF to Net Income", "cash_flow", "conversion", "ratio", "ratio", "cash_conversion_ocf_to_net_income_v1", "operating_cash_flow / net_income"),
    MetricDefinition("cash_conversion_fcf_to_net_income", "Cash Conversion FCF to Net Income", "cash_flow", "conversion", "ratio", "ratio", "cash_conversion_fcf_to_net_income_v1", "free_cash_flow / net_income"),
    MetricDefinition("capex_to_net_income", "Capital Expenditures to Net Income", "cash_flow", "capital_spending", "ratio", "ratio", "capex_to_net_income_v1", "capital_expenditures_proxy / net_income"),
    MetricDefinition("free_cash_flow_per_share", "Free Cash Flow Per Share", "per_share", "cash_flow", "per_share", "usd_per_share", "free_cash_flow_per_share_v1", "free_cash_flow / share_base"),
    MetricDefinition("operating_cash_flow_per_share", "Operating Cash Flow Per Share", "per_share", "cash_flow", "per_share", "usd_per_share", "operating_cash_flow_per_share_v1", "operating_cash_flow / share_base"),
    MetricDefinition("eps_basic", "EPS Basic", "per_share", "earnings", "per_share", "usd_per_share", "eps_basic_v1", "net_income / weighted_avg_shares_basic"),
    MetricDefinition("eps_diluted", "EPS Diluted", "per_share", "earnings", "per_share", "usd_per_share", "eps_diluted_v1", "net_income / weighted_avg_shares_diluted"),
    MetricDefinition("eps_growth", "EPS Growth", "growth", "per_share", "ratio", "ratio", "eps_growth_v1", "eps_diluted / prior_eps_diluted - 1"),
    MetricDefinition("book_value_per_share", "Book Value Per Share", "per_share", "balance_sheet", "per_share", "usd_per_share", "book_value_per_share_v1", "total_equity / ending_shares"),
    MetricDefinition("book_value_per_share_growth", "Book Value Per Share Growth", "growth", "per_share", "ratio", "ratio", "book_value_per_share_growth_v1", "book_value_per_share / prior_book_value_per_share - 1"),
    MetricDefinition("tangible_book_value_per_share", "Tangible Book Value Per Share", "per_share", "balance_sheet", "per_share", "usd_per_share", "tangible_book_value_per_share_v1", "tangible_equity / ending_shares"),
    MetricDefinition("total_assets", "Total Assets", "balance_sheet", "assets", "currency", "usd", "total_assets_v1", "total_assets"),
    MetricDefinition("total_liabilities", "Total Liabilities", "balance_sheet", "liabilities", "currency", "usd", "total_liabilities_v1", "total_liabilities"),
    MetricDefinition("total_equity", "Total Equity", "balance_sheet", "equity", "currency", "usd", "total_equity_v1", "total_equity"),
    MetricDefinition("inventory", "Inventory", "balance_sheet", "working_capital", "currency", "usd", "inventory_v1", "inventory"),
    MetricDefinition("property_plant_equipment", "Property, Plant and Equipment", "balance_sheet", "assets", "currency", "usd", "property_plant_equipment_v1", "property_plant_equipment"),
    MetricDefinition("treasury_stock", "Treasury Stock", "balance_sheet", "equity", "currency", "usd", "treasury_stock_v1", "treasury_stock"),
    MetricDefinition("retained_earnings_growth", "Retained Earnings Growth", "growth", "balance_sheet", "ratio", "ratio", "retained_earnings_growth_v1", "retained_earnings / prior_retained_earnings - 1"),
    MetricDefinition("debt_to_equity", "Debt to Equity", "solvency", "leverage", "ratio", "ratio", "debt_to_equity_v1", "total_debt / total_equity"),
    MetricDefinition("adjusted_debt_to_equity", "Adjusted Debt to Equity", "solvency", "leverage", "ratio", "ratio", "adjusted_debt_to_equity_v1", "total_debt / (total_equity + abs(treasury_stock))"),
    MetricDefinition("years_to_pay_long_term_debt", "Years to Pay Long Term Debt", "solvency", "leverage", "years", "years", "years_to_pay_long_term_debt_v1", "debt_noncurrent / net_income"),
    MetricDefinition("intangibles_to_assets", "Intangibles to Assets", "balance_sheet", "asset_mix", "ratio", "ratio", "intangibles_to_assets_v1", "(goodwill + intangible_assets_excluding_goodwill) / total_assets"),
    MetricDefinition("ppe_to_assets", "PPE to Assets", "balance_sheet", "asset_mix", "ratio", "ratio", "ppe_to_assets_v1", "property_plant_equipment / total_assets"),
    MetricDefinition("ppe_to_net_income", "PPE to Net Income", "balance_sheet", "asset_intensity", "ratio", "ratio", "ppe_to_net_income_v1", "property_plant_equipment / net_income"),
    MetricDefinition("debt_to_ppe", "Debt to PPE", "solvency", "leverage", "ratio", "ratio", "debt_to_ppe_v1", "total_debt / property_plant_equipment"),
    MetricDefinition("receivables_to_revenue", "Receivables to Revenue", "balance_sheet", "working_capital", "ratio", "ratio", "receivables_to_revenue_v1", "accounts_receivable_net / revenue"),
    MetricDefinition("inventory_growth", "Inventory Growth", "growth", "working_capital", "ratio", "ratio", "inventory_growth_v1", "inventory / prior_inventory - 1"),
    MetricDefinition("goodwill_growth", "Goodwill Growth", "growth", "asset_mix", "ratio", "ratio", "goodwill_growth_v1", "goodwill / prior_goodwill - 1"),
    MetricDefinition("debt_to_capital", "Debt to Capital", "solvency", "leverage", "ratio", "ratio", "debt_to_capital_v1", "total_debt / (total_debt + total_equity)"),
    MetricDefinition("financial_leverage", "Financial Leverage", "solvency", "leverage", "ratio", "ratio", "financial_leverage_v1", "average_assets / average_equity"),
    MetricDefinition("net_debt", "Net Debt", "solvency", "leverage", "currency", "usd", "net_debt_v1", "total_debt - cash_and_equivalents - short_term_investments"),
    MetricDefinition("net_debt_to_fcf", "Net Debt to Free Cash Flow", "solvency", "leverage", "ratio", "ratio", "net_debt_to_fcf_v1", "net_debt / free_cash_flow"),
    MetricDefinition("debt_payback_years", "Debt Payback Years", "solvency", "leverage", "years", "years", "debt_payback_years_v1", "total_debt / free_cash_flow"),
    MetricDefinition("return_on_tangible_capital", "Return on Tangible Capital", "profitability", "returns", "ratio", "ratio", "return_on_tangible_capital_v1", "operating_income / average_tangible_capital"),
    MetricDefinition("current_ratio", "Current Ratio", "liquidity", "working_capital", "ratio", "ratio", "current_ratio_v1", "current_assets / current_liabilities"),
    MetricDefinition("quick_ratio", "Quick Ratio", "liquidity", "working_capital", "ratio", "ratio", "quick_ratio_v1", "(cash_and_equivalents + short_term_investments + accounts_receivable_net) / current_liabilities"),
    MetricDefinition("share_count_trend", "Share Count Trend", "capital_structure", "shares", "ratio", "ratio", "share_count_trend_v1", "ending_shares / prior_ending_shares - 1"),
    MetricDefinition("share_repurchases", "Share Repurchases", "cash_flow", "capital_allocation", "currency", "usd", "share_repurchases_v1", "share_repurchases"),
    MetricDefinition("stock_issuance", "Stock Issuance", "cash_flow", "capital_allocation", "currency", "usd", "stock_issuance_v1", "stock_issuance"),
    MetricDefinition("debt_issuance", "Debt Issuance", "cash_flow", "financing", "currency", "usd", "debt_issuance_v1", "debt_issuance"),
    MetricDefinition("debt_repayment", "Debt Repayment", "cash_flow", "financing", "currency", "usd", "debt_repayment_v1", "debt_repayment"),
    MetricDefinition("net_stock_issuance_or_retirement", "Net Stock Issuance or Retirement", "cash_flow", "capital_allocation", "currency", "usd", "net_stock_issuance_or_retirement_v1", "stock_issuance - share_repurchases"),
    MetricDefinition("net_debt_issuance_or_retirement", "Net Debt Issuance or Retirement", "cash_flow", "financing", "currency", "usd", "net_debt_issuance_or_retirement_v1", "debt_issuance - debt_repayment"),
    MetricDefinition("dividend_growth", "Dividend Growth", "growth", "dividends", "ratio", "ratio", "dividend_growth_v1", "dividends_common_cash / prior_dividends_common_cash - 1"),
    MetricDefinition("dividend_payout_ratio", "Dividend Payout Ratio", "capital_allocation", "dividends", "ratio", "ratio", "dividend_payout_ratio_v1", "dividends_common_cash / net_income"),
    MetricDefinition("interest_coverage", "Interest Coverage", "solvency", "coverage", "ratio", "ratio", "interest_coverage_v1", "operating_income / abs(interest_expense)"),
    MetricDefinition("owners_earnings_approx", "Owners Earnings Approximation", "cash_flow", "owner_earnings", "currency", "usd", "owners_earnings_approx_v1", "net_income + depreciation_and_amortization - capital_expenditures_proxy"),
)


METRIC_DEFINITION_BY_CODE = {definition.metric_code: definition for definition in METRIC_DEFINITIONS}

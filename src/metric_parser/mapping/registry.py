from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConceptAlias:
    concept_local_name: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    field_code: str
    field_name: str
    value_type: str
    period_kind: str
    category: str
    concept_aliases: tuple[ConceptAlias, ...] = ()
    statement_hint: str | None = None


FIELD_DEFINITIONS: tuple[FieldDefinition, ...] = (
    FieldDefinition(
        field_code="revenue",
        field_name="Revenue",
        value_type="currency",
        period_kind="duration",
        category="income_statement",
        statement_hint="income_statement",
        concept_aliases=(
            ConceptAlias("Revenues"),
            ConceptAlias("SalesRevenueNet"),
            ConceptAlias("RevenueFromContractWithCustomerExcludingAssessedTax"),
        ),
    ),
    FieldDefinition(
        field_code="gross_profit",
        field_name="Gross Profit",
        value_type="currency",
        period_kind="duration",
        category="income_statement",
        statement_hint="income_statement",
        concept_aliases=(ConceptAlias("GrossProfit"),),
    ),
    FieldDefinition(
        field_code="cost_of_revenue",
        field_name="Cost of Revenue",
        value_type="currency",
        period_kind="duration",
        category="income_statement",
        statement_hint="income_statement",
        concept_aliases=(
            ConceptAlias("CostOfRevenue"),
            ConceptAlias("CostOfGoodsSold"),
            ConceptAlias("CostOfSales"),
        ),
    ),
    FieldDefinition(
        field_code="operating_income",
        field_name="Operating Income",
        value_type="currency",
        period_kind="duration",
        category="income_statement",
        statement_hint="income_statement",
        concept_aliases=(
            ConceptAlias("OperatingIncomeLoss"),
            ConceptAlias("OperatingIncome"),
        ),
    ),
    FieldDefinition(
        field_code="net_income",
        field_name="Net Income",
        value_type="currency",
        period_kind="duration",
        category="income_statement",
        statement_hint="income_statement",
        concept_aliases=(
            ConceptAlias("NetIncomeLoss"),
            ConceptAlias("ProfitLoss"),
        ),
    ),
    FieldDefinition(
        field_code="income_before_tax",
        field_name="Income Before Tax",
        value_type="currency",
        period_kind="duration",
        category="income_statement",
        statement_hint="income_statement",
        concept_aliases=(
            ConceptAlias("IncomeBeforeTaxExpenseBenefit"),
            ConceptAlias("PretaxIncome"),
            ConceptAlias("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"),
        ),
    ),
    FieldDefinition(
        field_code="income_tax_expense",
        field_name="Income Tax Expense",
        value_type="currency",
        period_kind="duration",
        category="income_statement",
        statement_hint="income_statement",
        concept_aliases=(ConceptAlias("IncomeTaxExpenseBenefit"),),
    ),
    FieldDefinition(
        field_code="interest_expense",
        field_name="Interest Expense",
        value_type="currency",
        period_kind="duration",
        category="income_statement",
        statement_hint="income_statement",
        concept_aliases=(
            ConceptAlias("InterestExpenseAndDebtExpense"),
            ConceptAlias("InterestExpense"),
        ),
    ),
    FieldDefinition(
        field_code="total_assets",
        field_name="Total Assets",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(ConceptAlias("Assets"),),
    ),
    FieldDefinition(
        field_code="total_equity",
        field_name="Total Equity",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(
            ConceptAlias("StockholdersEquity"),
            ConceptAlias("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
        ),
    ),
    FieldDefinition(
        field_code="retained_earnings",
        field_name="Retained Earnings",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(ConceptAlias("RetainedEarningsAccumulatedDeficit"),),
    ),
    FieldDefinition(
        field_code="current_assets",
        field_name="Current Assets",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(ConceptAlias("AssetsCurrent"),),
    ),
    FieldDefinition(
        field_code="current_liabilities",
        field_name="Current Liabilities",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(ConceptAlias("LiabilitiesCurrent"),),
    ),
    FieldDefinition(
        field_code="cash_and_equivalents",
        field_name="Cash and Equivalents",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(ConceptAlias("CashAndCashEquivalentsAtCarryingValue"),),
    ),
    FieldDefinition(
        field_code="short_term_investments",
        field_name="Short Term Investments",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(
            ConceptAlias("ShortTermInvestments"),
            ConceptAlias("AvailableForSaleSecuritiesCurrent"),
            ConceptAlias("MarketableSecuritiesCurrent"),
        ),
    ),
    FieldDefinition(
        field_code="accounts_receivable_net",
        field_name="Accounts Receivable, Net",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(ConceptAlias("AccountsReceivableNetCurrent"),),
    ),
    FieldDefinition(
        field_code="goodwill",
        field_name="Goodwill",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(ConceptAlias("Goodwill"),),
    ),
    FieldDefinition(
        field_code="intangible_assets_excluding_goodwill",
        field_name="Intangible Assets Excluding Goodwill",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(
            ConceptAlias("FiniteLivedIntangibleAssetsNet"),
            ConceptAlias("IndefiniteLivedIntangibleAssetsExcludingGoodwill"),
            ConceptAlias("IntangibleAssetsNetExcludingGoodwill"),
        ),
    ),
    FieldDefinition(
        field_code="operating_cash_flow",
        field_name="Operating Cash Flow",
        value_type="currency",
        period_kind="duration",
        category="cash_flow",
        statement_hint="cash_flow",
        concept_aliases=(
            ConceptAlias("NetCashProvidedByUsedInOperatingActivities"),
            ConceptAlias("NetCashProvidedByOperatingActivities"),
        ),
    ),
    FieldDefinition(
        field_code="capital_expenditures_proxy",
        field_name="Capital Expenditures Proxy",
        value_type="currency",
        period_kind="duration",
        category="cash_flow",
        statement_hint="cash_flow",
        concept_aliases=(
            ConceptAlias("PaymentsToAcquirePropertyPlantAndEquipment"),
            ConceptAlias("PropertyPlantAndEquipmentAdditions"),
            ConceptAlias("CapitalExpendituresIncurredButNotYetPaid", warnings=("capex_proxy_used",)),
        ),
    ),
    FieldDefinition(
        field_code="depreciation_and_amortization",
        field_name="Depreciation and Amortization",
        value_type="currency",
        period_kind="duration",
        category="cash_flow",
        statement_hint="cash_flow",
        concept_aliases=(
            ConceptAlias("DepreciationDepletionAndAmortization"),
            ConceptAlias("Depreciation"),
            ConceptAlias("DepreciationAmortizationAndAccretionNet"),
        ),
    ),
    FieldDefinition(
        field_code="dividends_common_cash",
        field_name="Dividends Common Cash",
        value_type="currency",
        period_kind="duration",
        category="cash_flow",
        concept_aliases=(
            ConceptAlias("DividendsCommonStockCash"),
            ConceptAlias("PaymentsOfDividends"),
        ),
    ),
    FieldDefinition(
        field_code="shares_outstanding_end",
        field_name="Shares Outstanding End",
        value_type="count",
        period_kind="instant",
        category="per_share",
        concept_aliases=(
            ConceptAlias("CommonStockSharesOutstanding"),
            ConceptAlias("EntityCommonStockSharesOutstanding"),
        ),
    ),
    FieldDefinition(
        field_code="weighted_avg_shares_basic",
        field_name="Weighted Average Shares Basic",
        value_type="count",
        period_kind="duration",
        category="per_share",
        concept_aliases=(ConceptAlias("WeightedAverageNumberOfSharesOutstandingBasic"),),
    ),
    FieldDefinition(
        field_code="weighted_avg_shares_diluted",
        field_name="Weighted Average Shares Diluted",
        value_type="count",
        period_kind="duration",
        category="per_share",
        concept_aliases=(ConceptAlias("WeightedAverageNumberOfDilutedSharesOutstanding"),),
    ),
    FieldDefinition(
        field_code="debt_current",
        field_name="Debt Current",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(
            ConceptAlias("LongTermDebtCurrent"),
            ConceptAlias("CurrentPortionOfLongTermDebt"),
            ConceptAlias("ShortTermBorrowings"),
        ),
    ),
    FieldDefinition(
        field_code="debt_noncurrent",
        field_name="Debt Noncurrent",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(
            ConceptAlias("LongTermDebtNoncurrent"),
            ConceptAlias("LongTermDebtAndFinanceLeaseObligationsNoncurrent"),
            ConceptAlias("LongTermDebt"),
        ),
    ),
    FieldDefinition(
        field_code="total_debt",
        field_name="Total Debt",
        value_type="currency",
        period_kind="instant",
        category="balance_sheet",
        statement_hint="balance_sheet",
        concept_aliases=(
            ConceptAlias("DebtAndCapitalLeaseObligations"),
            ConceptAlias("LongTermDebtAndFinanceLeaseObligations"),
        ),
    ),
)


FIELD_DEFINITION_BY_CODE = {definition.field_code: definition for definition in FIELD_DEFINITIONS}

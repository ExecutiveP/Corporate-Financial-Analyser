import pandas as pd
import streamlit as st

# --- 1. PAGE CONFIGURATION (Must be the very first Streamlit command) ---
st.set_page_config(page_title="Financial Analyser",
                   page_icon="📊", layout="wide")

# --- 2. SIDEBAR CONTROLS ---
with st.sidebar:
    st.image("logo.png", use_container_width=True)
    st.header("⚙️ Dashboard Controls")
    st.write("Upload your corporate data below to generate the automated report.")
    uploaded_file = st.file_uploader("Upload financial data (CSV)", type="csv")

    st.divider()
    st.info("💡 **Tip:** Ensure your CSV contains the most recent 5 years of historical data for optimal trend mapping.")

# --- 3. MAIN DASHBOARD HEADER ---
st.title("📊 Financial Statement Analyser")
st.write("Welcome to your automated historical trend analysis tool.")
st.divider()

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file, index_col='Line_Item')

    # --- DYNAMIC YEAR LOGIC ---
    all_years = list(data.columns)
    all_years.sort()
    years = all_years[-5:]

    with st.expander("📂 View Raw Financial Data"):
        st.dataframe(data[years], use_container_width=True)

    # --- CALCULATIONS ---
    current_assets = data.loc['Inventory'] + \
        data.loc['Trade Receivables'] + data.loc['Cash and Cash Equivalents']
    current_liabilities = data.loc['Trade Payables'] + \
        data.loc['Short-Term Borrowings']
    total_debt = data.loc['Short-Term Borrowings'] + \
        data.loc['Long-Term Borrowings']
    total_equity = data.loc['Share Capital'] + data.loc['Retained Earnings']
    gross_profit = data.loc['Revenue'] + data.loc['Cost of Sales']

    current_ratio = current_assets / current_liabilities
    quick_ratio = (current_assets -
                   data.loc['Inventory']) / current_liabilities
    debt_to_equity = total_debt / total_equity
    gp_margin = (gross_profit / data.loc['Revenue']) * 100

    # DuPont Calculations
    net_profit_margin = (data.loc['Net Income'] / data.loc['Revenue']) * 100
    asset_turnover = data.loc['Revenue'] / data.loc['Total Assets']
    equity_multiplier = data.loc['Total Assets'] / total_equity
    roe = (data.loc['Net Income'] / total_equity) * 100

    # Efficiency Calculations
    inventory_days = (data.loc['Inventory'] /
                      data.loc['Cost of Sales'].abs()) * 365
    debtors_days = (data.loc['Trade Receivables'] / data.loc['Revenue']) * 365
    creditors_days = (data.loc['Trade Payables'] /
                      data.loc['Cost of Sales'].abs()) * 365
    ccc = inventory_days + debtors_days - creditors_days

    # Market & Valuation Calculations
    eps = data.loc['Net Income'] / data.loc['Number of Shares']
    dps = data.loc['Dividends Paid'].abs() / data.loc['Number of Shares']
    pe_ratio = data.loc['Market Price per Share'] / eps
    dividend_yield = (dps / data.loc['Market Price per Share']) * 100
    dividend_cover = eps / dps

    # Cash Flow & Coverage Calculations
    interest_cover = data.loc['EBIT'] / data.loc['Interest Expense'].abs()
    ocf_to_cl = data.loc['Operating Cash Flow'] / current_liabilities

    # --- DEEP MULTI-YEAR EXPLANATORY LOGIC ---
    oldest_year = years[0]
    newest_year = years[-1]

    def get_cr_verdict(val):
        if val >= 1.5:
            return "✅ Healthy"
        elif val >= 1.0:
            return "🟡 Adequate"
        else:
            return "⚠️ Warning"

    def get_qr_verdict(val):
        return "✅ Healthy" if val >= 1.0 else "⚠️ Warning"

    def get_dte_verdict(val):
        return "⚠️ High Leverage" if val > 1.0 else "✅ Balanced"

    def get_gp_verdict(val):
        return "✅ Strong" if val > 40 else "⚠️ Tight"

    def get_roe_verdict(val):
        if val >= 15:
            return "✅ Strong"
        elif val >= 10:
            return "🟡 Adequate"
        else:
            return "⚠️ Weak"

    def get_ccc_verdict(val):
        if val < 30:
            return "✅ Efficient"
        elif val < 60:
            return "🟡 Adequate"
        else:
            return "⚠️ Cash Tied Up"

    def get_pe_verdict(val):
        if val > 25:
            return "📈 High"
        elif val >= 10:
            return "🟡 Fair Value"
        else:
            return "📉 Low"

    def get_dy_verdict(val):
        if val >= 4.0:
            return "✅ Strong"
        elif val >= 2.0:
            return "🟡 Adequate"
        else:
            return "⚠️ Low Return"

    def get_dc_verdict(val):
        if val >= 2.0:
            return "✅ Safe"
        elif val >= 1.5:
            return "🟡 Adequate"
        else:
            return "⚠️ At Risk"

    def get_ic_verdict(val):
        if val >= 3.0:
            return "✅ Safe"
        elif val >= 1.5:
            return "🟡 Adequate"
        else:
            return "⚠️ At Risk"

    def get_ocf_verdict(val):
        if val >= 1.0:
            return "✅ Excellent"
        elif val >= 0.5:
            return "🟡 Adequate"
        else:
            return "⚠️ Weak"

    # Interpreters
    def interpret_current_ratio_trend(ratios, years):
        explanation = "**What this means:** The Current Ratio measures a company's overall ability to pay its short-term obligations using all of its current assets.\n\n"
        explanation += "**The Benchmarks:**\n- **> 1.5:** ✅ Healthy\n- **1.0 to 1.5:** 🟡 Adequate\n- **< 1.0:** ⚠️ Warning\n\n"
        for year in years:
            explanation += f"- **{year}:** {ratios[year]:.2f} ({get_cr_verdict(ratios[year])})\n"
        return explanation

    def interpret_quick_ratio_trend(ratios, years):
        explanation = "**What this means:** The Quick Ratio measures a company's ability to pay its short-term debts using only its most liquid assets, deliberately excluding inventory.\n\n"
        explanation += "**The Benchmarks:**\n- **>= 1.0:** ✅ Healthy\n- **< 1.0:** ⚠️ Warning\n\n"
        for year in years:
            explanation += f"- **{year}:** {ratios[year]:.2f} ({get_qr_verdict(ratios[year])})\n"
        return explanation

    def interpret_dte_trend(ratios, years):
        explanation = "**What this means:** Debt-to-Equity compares how much the company is funding its operations through borrowed money (debt) versus shareholder money (equity).\n\n"
        explanation += "**The Benchmarks:**\n- **<= 1.0:** ✅ Balanced Leverage\n- **> 1.0:** ⚠️ High Leverage\n\n"
        for year in years:
            explanation += f"- **{year}:** {ratios[year]:.2f} ({get_dte_verdict(ratios[year])})\n"
        return explanation

    def interpret_gp_trend(ratios, years):
        explanation = "**What this means:** Gross Profit Margin shows the percentage of revenue left over after paying for the direct costs of producing goods (Cost of Sales).\n\n"
        explanation += "**The Benchmarks:**\n- **> 40%:** ✅ Strong Margins\n- **<= 40%:** ⚠️ Tight Margins\n\n"
        for year in years:
            explanation += f"- **{year}:** {ratios[year]:.2f}% ({get_gp_verdict(ratios[year])})\n"
        return explanation

    def interpret_dupont_trend(ratios, years):
        explanation = "**What this means:** The DuPont Analysis breaks Return on Equity (ROE) into three distinct drivers: operating efficiency, asset use efficiency, and financial leverage.\n\n"
        explanation += "**The Benchmarks (ROE):**\n- **>= 15%:** ✅ Strong Return\n- **10% to 14.9%:** 🟡 Adequate\n- **< 10%:** ⚠️ Weak\n\n"
        for year in years:
            explanation += f"- **{year}:** {ratios[year]:.2f}% ({get_roe_verdict(ratios[year])})\n"
        return explanation

    def interpret_ccc_trend(ccc, years):
        explanation = "**What this means:** The Cash Conversion Cycle (CCC) measures how many days it takes to convert inventory investments back into cash.\n\n"
        explanation += "**The Benchmarks:**\n- **< 30 Days:** ✅ Efficient\n- **30 to 60 Days:** 🟡 Adequate\n- **> 60 Days:** ⚠️ Cash Tied Up\n\n"
        for year in years:
            explanation += f"- **{year}:** {ccc[year]:.0f} days ({get_ccc_verdict(ccc[year])})\n"
        return explanation

    def interpret_pe_trend(ratios, years):
        explanation = "**What this means:** The Price-Earnings (P/E) ratio shows how much investors are willing to pay for every $1 of earnings.\n\n"
        explanation += "**The Benchmarks:**\n- **> 25x:** 📈 High (Growth Expectations)\n- **10x to 25x:** 🟡 Fair Value\n- **< 10x:** 📉 Low (Undervalued or High Risk)\n\n"
        for year in years:
            explanation += f"- **{year}:** {ratios[year]:.2f}x ({get_pe_verdict(ratios[year])})\n"
        return explanation

    def interpret_dividend_trend(yields, covers, years):
        explanation = "**What this means:** Dividend Yield shows the cash return on investment. Dividend Cover shows how many times earnings could cover the dividend payout.\n\n"
        explanation += "**The Benchmarks (Dividend Cover):**\n- **>= 2.0x:** ✅ Safe Dividend\n- **1.5x to 1.9x:** 🟡 Adequate\n- **< 1.5x:** ⚠️ At Risk of Being Cut\n\n"
        for year in years:
            explanation += f"- **{year}:** Yield: {yields[year]:.2f}% | Cover: {covers[year]:.2f}x ({get_dc_verdict(covers[year])})\n"
        return explanation

    def interpret_ic_trend(ratios, years):
        explanation = "**What this means:** Interest Cover shows how easily a company can pay interest expenses from its operating profit (EBIT).\n\n"
        explanation += "**The Benchmarks:**\n- **>= 3.0x:** ✅ Safe\n- **1.5x to 2.9x:** 🟡 Adequate\n- **< 1.5x:** ⚠️ At Risk\n\n"
        for year in years:
            explanation += f"- **{year}:** {ratios[year]:.2f}x ({get_ic_verdict(ratios[year])})\n"
        return explanation

    def interpret_ocf_trend(ratios, years):
        explanation = "**What this means:** The Operating Cash Flow to Current Liabilities ratio shows whether a company generates enough actual physical cash to pay off its short-term debts.\n\n"
        explanation += "**The Benchmarks:**\n- **>= 1.0:** ✅ Excellent\n- **0.5 to 0.99:** 🟡 Adequate\n- **< 0.5:** ⚠️ Weak\n\n"
        for year in years:
            explanation += f"- **{year}:** {ratios[year]:.2f} ({get_ocf_verdict(ratios[year])})\n"
        return explanation

    # --- 4. DYNAMIC DASHBOARD DISPLAY ---
    st.header(f"Financial Health Dashboard ({len(years)}-Year Trend)")

    st.subheader("1. Liquidity Analysis")
    cr_cols = st.columns(len(years))
    for i, year in enumerate(years):
        cr_cols[i].metric(label=f"{year}", value=f"{current_ratio[year]:.2f}")
    st.line_chart(current_ratio)
    st.info(interpret_current_ratio_trend(current_ratio, years))

    qr_cols = st.columns(len(years))
    for i, year in enumerate(years):
        qr_cols[i].metric(label=f"{year}", value=f"{quick_ratio[year]:.2f}")
    st.line_chart(quick_ratio)
    st.info(interpret_quick_ratio_trend(quick_ratio, years))
    st.divider()

    st.subheader("2. Efficiency & Working Capital")
    ccc_cols = st.columns(len(years))
    for i, year in enumerate(years):
        ccc_cols[i].metric(label=f"{year}", value=f"{ccc[year]:.0f}")
    st.line_chart(ccc)
    st.info(interpret_ccc_trend(ccc, years))
    st.divider()

    st.subheader("3. Solvency Analysis")
    dte_cols = st.columns(len(years))
    for i, year in enumerate(years):
        dte_cols[i].metric(
            label=f"{year}", value=f"{debt_to_equity[year]:.2f}")
    st.line_chart(debt_to_equity)
    st.info(interpret_dte_trend(debt_to_equity, years))
    st.divider()

    st.subheader("4. Profitability Analysis")
    gp_cols = st.columns(len(years))
    for i, year in enumerate(years):
        gp_cols[i].metric(label=f"{year}", value=f"{gp_margin[year]:.2f}%")
    st.line_chart(gp_margin)
    st.info(interpret_gp_trend(gp_margin, years))
    st.divider()

    st.subheader("5. DuPont Analysis (Return on Equity)")
    roe_cols = st.columns(len(years))
    for i, year in enumerate(years):
        roe_cols[i].metric(label=f"{year}", value=f"{roe[year]:.2f}%")
    st.line_chart(roe)
    st.info(interpret_dupont_trend(roe, years))
    st.divider()

    st.subheader("6. Market & Valuation Analysis")
    pe_cols = st.columns(len(years))
    for i, year in enumerate(years):
        pe_cols[i].metric(
            label=f"P/E Ratio ({year})", value=f"{pe_ratio[year]:.2f}")
    st.line_chart(pe_ratio)
    st.info(interpret_pe_trend(pe_ratio, years))

    dy_cols = st.columns(len(years))
    for i, year in enumerate(years):
        dy_cols[i].metric(
            label=f"Div Yield ({year})", value=f"{dividend_yield[year]:.2f}%")
    st.line_chart(dividend_yield)
    st.info(interpret_dividend_trend(dividend_yield, dividend_cover, years))
    st.divider()

    st.subheader("7. Cash Flow & Coverage Analysis")
    ic_cols = st.columns(len(years))
    for i, year in enumerate(years):
        ic_cols[i].metric(
            label=f"Interest Cover ({year})", value=f"{interest_cover[year]:.2f}")
    st.line_chart(interest_cover)
    st.info(interpret_ic_trend(interest_cover, years))

    ocf_cols = st.columns(len(years))
    for i, year in enumerate(years):
        ocf_cols[i].metric(
            label=f"OCF to Liabilities ({year})", value=f"{ocf_to_cl[year]:.2f}")
    st.line_chart(ocf_to_cl)
    st.info(interpret_ocf_trend(ocf_to_cl, years))

else:
    st.info("Please upload a multi-year CSV file using the sidebar on the left to generate your analysis.")

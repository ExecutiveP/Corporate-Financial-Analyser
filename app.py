import pandas as pd
import numpy as np
import streamlit as st
import google.generativeai as genai
import PyPDF2
import io
import plotly.express as px

# Configure the AI using the hidden secrets file
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Financial Analyser",
                   page_icon="📊", layout="wide")

# --- 2. SIDEBAR CONTROLS ---
with st.sidebar:
    st.image("logo.png", use_container_width=True)
    st.header("⚙️ Dashboard Controls")
    st.write("Upload your corporate data below to generate the automated report.")
    uploaded_file = st.file_uploader("Upload financial data (CSV)", type="csv")

    st.divider()
    st.info("💡 **Tip:** Ensure your CSV or PDF contains the most recent 5 years of historical data for optimal trend mapping.")

# --- 3. MAIN DASHBOARD HEADER ---
st.title("📊 Financial Statement Analyser")
st.write("Welcome to your automated historical trend analysis tool.")
st.divider()

# --- DATA TRAFFIC CONTROLLER ---
data = None

if 'financial_data' in st.session_state:
    data = st.session_state['financial_data']
    st.sidebar.success("✅ Using AI Extracted Data!")
    if st.sidebar.button("Clear AI Data"):
        del st.session_state['financial_data']
        st.rerun()

elif uploaded_file is not None:
    data = pd.read_csv(uploaded_file, index_col='Line_Item')

# --- MAIN DASHBOARD LOGIC ---
if data is not None:

    # Sort columns chronologically so charts draw correctly left-to-right
    data = data.sort_index(axis=1)

    all_years = list(data.columns)
    all_years.sort()
    years = all_years[-5:]

    with st.expander("📂 View Raw Financial Data"):
        st.dataframe(data[years], use_container_width=True)

    st.header("📈 Advanced Financial Ratios & DuPont Analysis")

    try:
        def get_val(name):
            return data.loc[name] if name in data.index else pd.Series(0, index=data.columns)

        # Extraction
        revenue = get_val('Revenue')
        cogs = get_val('Cost of Sales').abs()
        gross_profit = get_val('Gross Profit')
        op_profit = get_val('Operating Profit')
        finance_costs = get_val('Finance Costs').abs()
        net_income = get_val('Net Income')
        inventory = get_val('Inventory')
        receivables = get_val('Trade and Other Receivables')
        cash = get_val('Cash and Cash Equivalents')
        current_assets = get_val('Current Assets')
        total_assets = get_val('Total Assets')
        payables = get_val('Trade and Other Payables')
        current_liabilities = get_val('Current Liabilities')
        total_debt = get_val('Total Liabilities')
        total_equity = get_val('Total Equity')
        depreciation = get_val('Depreciation and Amortization').abs()
        dividends = get_val('Dividends Paid').abs()
        operating_cash_flow = get_val('Operating Cash Flow')
        shares = get_val('Number of Shares').replace(0, np.nan)
        market_price = get_val('Market Price per Share').replace(0, np.nan)

        ebitda = op_profit + depreciation

        # Safe Divisors
        safe_cogs = cogs.replace(0, np.nan)
        safe_rev = revenue.replace(0, np.nan)
        safe_assets = total_assets.replace(0, np.nan)
        safe_equity = total_equity.replace(0, np.nan)
        safe_liab = current_liabilities.replace(0, np.nan)
        safe_finance = finance_costs.replace(0, np.nan)
        safe_net_inc = net_income.replace(0, np.nan)

        # Calculations
        current_ratio = current_assets / safe_liab
        quick_ratio = (current_assets - inventory) / safe_liab
        debt_to_equity = total_debt / safe_equity
        gp_margin = (gross_profit / safe_rev) * 100
        net_profit_margin = net_income / safe_rev
        asset_turnover = revenue / safe_assets
        equity_multiplier = total_assets / safe_equity
        roe = (net_profit_margin * asset_turnover * equity_multiplier) * 100
        ebitda_margin = (ebitda / safe_rev) * 100
        inventory_days = (inventory / safe_cogs) * 365
        debtors_days = (receivables / safe_rev) * 365
        creditors_days = (payables / safe_cogs) * 365
        ccc = inventory_days + debtors_days - creditors_days
        eps = net_income / shares
        dps = dividends / shares
        pe_ratio = market_price / eps.replace(0, np.nan)
        dividend_yield = (dps / market_price) * 100
        div_cover = net_income / dividends.replace(0, np.nan)
        interest_cover = op_profit / safe_finance
        ebitda_coverage = ebitda / safe_finance
        ocf_to_cl = operating_cash_flow / safe_liab

        advanced_ratios = pd.DataFrame({
            "Inventory Days": inventory_days,
            "Interest Cover (x)": interest_cover,
            "EBITDA Coverage (x)": ebitda_coverage,
            "EBITDA Margin (%)": ebitda_margin,
            "Dividend Payout Ratio (%)": (dividends / safe_net_inc) * 100,
            "Dividend Cover (x)": div_cover,
            "DuPont: Net Profit Margin (%)": net_profit_margin * 100,
            "DuPont: Asset Turnover (x)": asset_turnover,
            "DuPont: Equity Multiplier (x)": equity_multiplier,
            "DuPont: Implied ROE (%)": roe
        }).T

        st.write("### Calculated Metrics")
        st.dataframe(advanced_ratios.style.format("{:.2f}", na_rep="N/A"))

    except Exception as e:
        st.error(f"Calculation Error: {e}")

    # --- PLOTLY CHART HELPER FUNCTION ---
    def create_chart(series, title, y_label="", is_pct=False):
        df_plot = series.dropna().reset_index()
        df_plot.columns = ['Year', 'Value']
        df_plot['Year'] = df_plot['Year'].astype(str)

        fig = px.line(df_plot, x='Year', y='Value', markers=True, title=title)
        fig.update_traces(line_color='#1f77b4', marker=dict(
            size=8, color='#1f77b4'), line=dict(width=3))
        fig.update_layout(
            xaxis_title="",
            yaxis_title=y_label,
            margin=dict(l=0, r=0, t=40, b=0),
            hovermode="x unified",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
        )
        return fig

    # --- DEEP MULTI-YEAR EXPLANATORY LOGIC ---
    def is_invalid(val):
        return pd.isna(val) or val == float('inf') or val == float('-inf')

    def fmt_num(val, is_pct=False):
        if is_invalid(val):
            return "N/A"
        return f"{val:.2f}%" if is_pct else f"{val:.2f}"

    def fmt_whole(val):
        if is_invalid(val):
            return "N/A"
        return f"{val:.0f}"

    def get_cr_verdict(val):
        if is_invalid(val):
            return "N/A"
        if val >= 1.5:
            return "✅ Healthy"
        elif val >= 1.0:
            return "🟡 Adequate"
        else:
            return "⚠️ Warning"

    def get_qr_verdict(val):
        if is_invalid(val):
            return "N/A"
        return "✅ Healthy" if val >= 1.0 else "⚠️ Warning"

    def get_dte_verdict(val):
        if is_invalid(val):
            return "N/A"
        return "⚠️ High Leverage" if val > 1.0 else "✅ Balanced"

    def get_gp_verdict(val):
        if is_invalid(val):
            return "N/A"
        return "✅ Strong" if val > 40 else "⚠️ Tight"

    def get_roe_verdict(val):
        if is_invalid(val):
            return "N/A"
        if val >= 15:
            return "✅ Strong"
        elif val >= 10:
            return "🟡 Adequate"
        else:
            return "⚠️ Weak"

    def get_ccc_verdict(val):
        if is_invalid(val):
            return "N/A"
        if val < 30:
            return "✅ Efficient"
        elif val < 60:
            return "🟡 Adequate"
        else:
            return "⚠️ Cash Tied Up"

    def get_pe_verdict(val):
        if is_invalid(val):
            return "N/A"
        if val > 25:
            return "📈 High"
        elif val >= 10:
            return "🟡 Fair Value"
        else:
            return "📉 Low"

    def get_dy_verdict(val):
        if is_invalid(val):
            return "N/A"
        if val >= 4.0:
            return "✅ Strong"
        elif val >= 2.0:
            return "🟡 Adequate"
        else:
            return "⚠️ Low Return"

    def get_dc_verdict(val):
        if is_invalid(val):
            return "N/A"
        if val >= 2.0:
            return "✅ Safe"
        elif val >= 1.5:
            return "🟡 Adequate"
        else:
            return "⚠️ At Risk"

    def get_ic_verdict(val):
        if is_invalid(val):
            return "N/A"
        if val >= 3.0:
            return "✅ Safe"
        elif val >= 1.5:
            return "🟡 Adequate"
        else:
            return "⚠️ At Risk"

    def get_ocf_verdict(val):
        if is_invalid(val):
            return "N/A"
        if val >= 1.0:
            return "✅ Excellent"
        elif val >= 0.5:
            return "🟡 Adequate"
        else:
            return "⚠️ Weak"

    # Deep Interpreters
    def interpret_current_ratio_trend(ratios, years):
        explanation = "**What this means:** The Current Ratio measures a company's ability to pay its short-term obligations due within a year. *(Formula: Current Assets ÷ Current Liabilities)*\n\n"
        explanation += "**The Benchmarks:**\n- **> 1.5:** ✅ Healthy (Strong liquidity buffer)\n- **1.0 to 1.5:** 🟡 Adequate (Can pay debts, but limited cushion)\n- **< 1.0:** ⚠️ Warning (Current liabilities exceed current assets)\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_num(ratios[year])} ({get_cr_verdict(ratios[year])})\n"
        return explanation

    def interpret_quick_ratio_trend(ratios, years):
        explanation = "**What this means:** The Acid-Test (Quick) Ratio is a stricter measure of liquidity. It excludes inventory, focusing only on the most liquid assets available to cover short-term debts. *(Formula: [Current Assets - Inventory] ÷ Current Liabilities)*\n\n"
        explanation += "**The Benchmarks:**\n- **>= 1.0:** ✅ Healthy (Can clear obligations without selling inventory)\n- **< 1.0:** ⚠️ Warning (Reliant on inventory sales to meet short-term debt)\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_num(ratios[year])} ({get_qr_verdict(ratios[year])})\n"
        return explanation

    def interpret_dte_trend(ratios, years):
        explanation = "**What this means:** Debt-to-Equity compares how much the company is funding its operations through borrowed money (debt) versus shareholder money (equity). *(Formula: Total Liabilities ÷ Total Equity)*\n\n"
        explanation += "**The Benchmarks:**\n- **<= 1.0:** ✅ Balanced (More equity than debt)\n- **> 1.0:** ⚠️ High Leverage (Heavily reliant on creditors)\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_num(ratios[year])} ({get_dte_verdict(ratios[year])})\n"
        return explanation

    def interpret_gp_trend(ratios, years):
        explanation = "**What this means:** Gross Profit Margin shows the percentage of revenue left over after deducting the direct costs of production/sales. It reflects pricing power and production efficiency. *(Formula: Gross Profit ÷ Revenue)*\n\n"
        explanation += "**The Benchmarks:**\n- **> 40%:** ✅ Strong (High markup or low production cost)\n- **<= 40%:** ⚠️ Tight (Lower margin for operating expenses)\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_num(ratios[year], True)} ({get_gp_verdict(ratios[year])})\n"
        return explanation

    def interpret_dupont_trend(ratios, years):
        explanation = "**What this means:** DuPont Analysis breaks Return on Equity (ROE) into three drivers: Profitability (Net Margin), Efficiency (Asset Turnover), and Leverage (Equity Multiplier). It shows *how* the return is being generated.\n\n"
        explanation += "**The Benchmarks (ROE):**\n- **>= 15%:** ✅ Strong Shareholder Return\n- **10% to 14.9%:** 🟡 Adequate Return\n- **< 10%:** ⚠️ Weak Return\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_num(ratios[year], True)} ({get_roe_verdict(ratios[year])})\n"
        return explanation

    def interpret_ccc_trend(ccc, years):
        explanation = "**What this means:** The Cash Conversion Cycle (CCC) measures the number of days it takes a company to convert its investments in inventory back into cash from sales. *(Formula: Inventory Days + Debtors Days - Creditors Days)*\n\n"
        explanation += "**The Benchmarks:**\n- **< 30 Days:** ✅ Efficient (Rapid cash turnover)\n- **30 to 60 Days:** 🟡 Adequate\n- **> 60 Days:** ⚠️ Cash Tied Up (Potential working capital stress)\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_whole(ccc[year])} days ({get_ccc_verdict(ccc[year])})\n"
        return explanation

    def interpret_pe_trend(ratios, years):
        explanation = "**What this means:** The P/E ratio reflects market sentiment, showing how much investors are willing to pay for every $1 of company earnings. *(Formula: Market Price ÷ Earnings per Share)*\n\n"
        explanation += "**The Benchmarks:**\n- **> 25x:** 📈 High (Market expects strong future growth)\n- **10x to 25x:** 🟡 Fair Value\n- **< 10x:** 📉 Low (Potentially undervalued, or market perceives high risk)\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_num(ratios[year])}x ({get_pe_verdict(ratios[year])})\n"
        return explanation

    def interpret_dividend_trend(yields, covers, years):
        explanation = "**What this means:** Dividend Yield is the cash return on the current share price. Dividend Cover shows how many times the company's net income can pay the dividend, measuring dividend safety.\n\n"
        explanation += "**The Benchmarks (Dividend Cover):**\n- **>= 2.0x:** ✅ Safe (Dividends easily covered by earnings)\n- **1.5x to 1.9x:** 🟡 Adequate\n- **< 1.5x:** ⚠️ At Risk (Dividend may be cut if earnings drop)\n\n"
        for year in years:
            explanation += f"- **{year}:** Yield: {fmt_num(yields[year], True)} | Cover: {fmt_num(covers[year])}x ({get_dc_verdict(covers[year])})\n"
        return explanation

    def interpret_ic_trend(ratios, years):
        explanation = "**What this means:** Interest Cover assesses a company's ability to pay interest expenses on outstanding debt using its operating profit. *(Formula: Operating Profit ÷ Finance Costs)*\n\n"
        explanation += "**The Benchmarks:**\n- **>= 3.0x:** ✅ Safe (Comfortable buffer for debt servicing)\n- **1.5x to 2.9x:** 🟡 Adequate\n- **< 1.5x:** ⚠️ At Risk (Vulnerable to profit dips or interest rate hikes)\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_num(ratios[year])}x ({get_ic_verdict(ratios[year])})\n"
        return explanation

    def interpret_ocf_trend(ratios, years):
        explanation = "**What this means:** Operating Cash Flow to Current Liabilities reveals whether a company's actual physical cash generation is sufficient to cover its short-term debts. *(Formula: Operating Cash Flow ÷ Current Liabilities)*\n\n"
        explanation += "**The Benchmarks:**\n- **>= 1.0:** ✅ Excellent (Operations fully cover short-term debt)\n- **0.5 to 0.99:** 🟡 Adequate\n- **< 0.5:** ⚠️ Weak (Reliant on refinancing or asset sales)\n\n"
        for year in years:
            explanation += f"- **{year}:** {fmt_num(ratios[year])} ({get_ocf_verdict(ratios[year])})\n"
        return explanation

    # --- 4. DYNAMIC DASHBOARD DISPLAY ---
    if 'current_ratio' in locals():
        st.header(f"Financial Health Dashboard ({len(years)}-Year Trend)")

        st.header("1. Liquidity Analysis", divider="blue")
        cr_cols = st.columns(len(years))
        for i, year in enumerate(years):
            cr_cols[i].metric(
                label=f"{year}", value=fmt_num(current_ratio[year]))
        st.plotly_chart(create_chart(
            current_ratio, "Current Ratio Trend"), use_container_width=True)
        st.info(interpret_current_ratio_trend(current_ratio, years))

        qr_cols = st.columns(len(years))
        for i, year in enumerate(years):
            qr_cols[i].metric(
                label=f"{year}", value=fmt_num(quick_ratio[year]))
        st.plotly_chart(create_chart(
            quick_ratio, "Quick Ratio Trend"), use_container_width=True)
        st.info(interpret_quick_ratio_trend(quick_ratio, years))
        st.divider()

        st.header("2. Efficiency & Working Capital", divider="blue")
        ccc_cols = st.columns(len(years))
        for i, year in enumerate(years):
            ccc_cols[i].metric(label=f"{year}", value=fmt_whole(ccc[year]))
        st.plotly_chart(create_chart(
            ccc, "Cash Conversion Cycle (Days)"), use_container_width=True)
        st.info(interpret_ccc_trend(ccc, years))
        st.divider()

        st.header("3. Solvency Analysis", divider="blue")
        dte_cols = st.columns(len(years))
        for i, year in enumerate(years):
            dte_cols[i].metric(
                label=f"{year}", value=fmt_num(debt_to_equity[year]))
        st.plotly_chart(create_chart(
            debt_to_equity, "Debt-to-Equity Ratio"), use_container_width=True)
        st.info(interpret_dte_trend(debt_to_equity, years))
        st.divider()

        st.header("4. Profitability Analysis", divider="blue")
        gp_cols = st.columns(len(years))
        for i, year in enumerate(years):
            gp_cols[i].metric(
                label=f"{year}", value=fmt_num(gp_margin[year], True))
        st.plotly_chart(create_chart(
            gp_margin, "Gross Profit Margin (%)"), use_container_width=True)
        st.info(interpret_gp_trend(gp_margin, years))
        st.divider()

        st.header("5. DuPont Analysis (Return on Equity)", divider="blue")
        roe_cols = st.columns(len(years))
        for i, year in enumerate(years):
            roe_cols[i].metric(label=f"{year}", value=fmt_num(roe[year], True))
        st.plotly_chart(create_chart(roe, "Implied ROE (%)"),
                        use_container_width=True)
        st.info(interpret_dupont_trend(roe, years))
        st.divider()

        st.header("6. Market & Valuation Analysis", divider="blue")
        pe_cols = st.columns(len(years))
        for i, year in enumerate(years):
            pe_cols[i].metric(
                label=f"P/E Ratio ({year})", value=fmt_num(pe_ratio[year]))
        st.plotly_chart(create_chart(
            pe_ratio, "Price-Earnings Multiple"), use_container_width=True)
        st.info(interpret_pe_trend(pe_ratio, years))

        dy_cols = st.columns(len(years))
        for i, year in enumerate(years):
            dy_cols[i].metric(label=f"Div Yield ({year})", value=fmt_num(
                dividend_yield[year], True))
        st.plotly_chart(create_chart(
            dividend_yield, "Dividend Yield (%)"), use_container_width=True)
        st.info(interpret_dividend_trend(dividend_yield, div_cover, years))
        st.divider()

        st.header("7. Cash Flow & Coverage Analysis", divider="blue")
        ic_cols = st.columns(len(years))
        for i, year in enumerate(years):
            ic_cols[i].metric(
                label=f"Interest Cover ({year})", value=fmt_num(interest_cover[year]))
        st.plotly_chart(create_chart(
            interest_cover, "Interest Coverage Multiple"), use_container_width=True)
        st.info(interpret_ic_trend(interest_cover, years))

        ocf_cols = st.columns(len(years))
        for i, year in enumerate(years):
            ocf_cols[i].metric(
                label=f"OCF to Liabilities ({year})", value=fmt_num(ocf_to_cl[year]))
        st.plotly_chart(create_chart(
            ocf_to_cl, "OCF to Current Liabilities"), use_container_width=True)
        st.info(interpret_ocf_trend(ocf_to_cl, years))

else:
    st.info("Please upload a multi-year CSV file or Annual Report PDF to generate your analysis.")

# --- 5. AI PDF EXTRACTION ENGINE ---
st.divider()
st.header("🤖 AI-Powered Annual Report Extraction")

# Clearer instructions for the user
st.info("💡 **Pro Tip:** If your document has more than 20 pages, please specify the exact page range where the financial statements (Income Statement, Balance Sheet, Cash Flow) are located. This saves processing time and prevents the AI from hitting token limits on massive reports!")

# Smart Page Range Selector
col1, col2 = st.columns(2)
start_page = col1.number_input(
    "Start Page (e.g., 27)", min_value=1, value=1, step=1)
end_page = col2.number_input(
    "End Page (e.g., 30)", min_value=1, value=20, step=1)

pdf_file = st.file_uploader("Upload Annual Report (PDF)", type="pdf")

if pdf_file is not None and 'financial_data' not in st.session_state:
    with st.spinner(f"The AI is reading pages {start_page} to {end_page}. This might take a minute..."):
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        pdf_text = ""

        # Safely handle page limits (Python uses 0-based indexing)
        start_idx = int(max(0, start_page - 1))
        end_idx = int(min(len(pdf_reader.pages), end_page))

        # Only read the specific pages the user asked for
        for i in range(start_idx, end_idx):
            page = pdf_reader.pages[i]
            if page.extract_text():
                pdf_text += page.extract_text()

        model = genai.GenerativeModel('gemini-3.5-flash')

        prompt = f"""
        You are a senior financial auditor extracting data from an IFRS-compliant corporate annual report. 
        Your job is to find the historical financial data for the most recent 3 to 5 years.
        Account for IFRS terminology variations (e.g., 'Turnover' vs 'Revenue').
        
        CRITICAL INDUSTRY INSTRUCTION:
        If this is an insurance, banking, or financial services company, you MUST map their specific terminology to the standard line items requested below. 
        - For "Revenue", look for "Insurance Revenue", "Net Investment Income", or "Total Income".
        - For "Cost of Sales", look for "Insurance Service Expenses", "Claims Incurred", or "Interest Expense".
        - If a concept genuinely does not exist (like 'Inventory' for an insurer), extract it with a value of 0.
        
        Extract the following line items and standardise their exact names in the 'Line_Item' column:
        - Revenue
        - Cost of Sales
        - Gross Profit
        - Operating Profit
        - Depreciation and Amortization
        - Finance Costs
        - Profit Before Tax
        - Income Tax Expense
        - Net Income
        - Dividends Paid
        - Operating Cash Flow
        - Non-Current Assets
        - Inventory
        - Trade and Other Receivables
        - Cash and Cash Equivalents
        - Current Assets
        - Total Assets
        - Trade and Other Payables
        - Current Liabilities
        - Non-Current Liabilities
        - Total Liabilities
        - Total Equity
        - Number of Shares
        - Market Price per Share
        
        Format the output STRICTLY as CSV text with the first column as 'Line_Item' and the subsequent columns as the years (e.g., 2025, 2024, 2023).
        Do NOT include any markdown formatting, conversational text, or explanations. Just the raw CSV data.
        
        Here is the raw text from the report:
        {pdf_text}
        """

        response = model.generate_content(prompt)
        st.success("Extraction Complete!")

        ai_data_stream = io.StringIO(response.text)
        try:
            df = pd.read_csv(ai_data_stream)
            df.set_index('Line_Item', inplace=True)

            st.write("### Extracted Financial Data")
            st.dataframe(df)

            st.session_state['financial_data'] = df
            st.rerun()

        except Exception as e:
            st.error(f"The AI returned formatting we couldn't read: {e}")
            st.code(response.text)


import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from io import StringIO
import base64

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="AMAZON SALES DASHBOARD",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# FILE PATHS
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "Amazon.csv"
LOGO_PATH = BASE_DIR / "logo.jpg"

# =========================================================
# DARK THEME AND STYLING
# =========================================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #080d19 0%, #111827 100%);
    color: #f8fafc;
}
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
    max-width: 1600px;
}
h1, h2, h3, p, label {
    color: #f8fafc;
}
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #18243a, #202d45);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 5px 18px rgba(0,0,0,0.25);
}
div[data-testid="stMetricLabel"] {
    color: #cbd5e1;
}
div[data-testid="stMetricValue"] {
    color: #ffffff;
}
div[data-testid="stPlotlyChart"] {
    background: #111827;
    border-radius: 12px;
}
.stDownloadButton button {
    background: linear-gradient(90deg, #0891b2, #2563eb);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: bold;
}
.stDownloadButton button:hover {
    color: white;
    border: 1px solid #38bdf8;
}
hr {
    border-color: #334155;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# ROBUST CSV LOADER
# =========================================================
@st.cache_data
def load_csv_robust(file_path, modified_time):
    raw = Path(file_path).read_bytes()

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
    last_error = None

    for encoding in encodings:
        try:
            text = raw.decode(encoding)
            df = pd.read_csv(StringIO(text))
            break
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            last_error = exc
    else:
        raise ValueError(f"Could not read CSV. Last error: {last_error}")

    df.columns = [
        str(col).replace("\xa0", " ").strip()
        for col in df.columns
    ]

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = (
            df[col]
            .astype("string")
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )

    return df

# =========================================================
# LOAD DATA AUTOMATICALLY
# =========================================================
if not CSV_PATH.exists():
    st.error(
        f"CSV file not found: {CSV_PATH}\n\n"
        "Place amazon.csv in the same folder as amazon.py."
    )
    st.stop()

try:
    df = load_csv_robust(
        str(CSV_PATH),
        CSV_PATH.stat().st_mtime
    )
except Exception as exc:
    st.error(f"Unable to read CSV: {exc}")
    st.stop()

# =========================================================
# VALIDATE COLUMNS
# =========================================================
required_columns = [
    "Order ID", "Order Date", "Geography", "Category",
    "Product Name", "Sales", "Quantity", "Profit"
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    st.error("Missing required columns: " + ", ".join(missing_columns))
    st.info("Check the column names in amazon.csv.")
    st.stop()

# =========================================================
# CLEAN NUMERIC COLUMNS
# =========================================================
for col in ["Sales", "Quantity", "Profit"]:
    cleaned = (
        df[col].astype("string")
        .str.replace(",", "", regex=False)
        .str.replace("₹", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("€", "", regex=False)
        .str.replace("£", "", regex=False)
        .str.strip()
    )
    df[col] = pd.to_numeric(cleaned, errors="coerce")

# =========================================================
# PARSE DATES
# =========================================================
df["Order Date"] = pd.to_datetime(
    df["Order Date"], errors="coerce", dayfirst=False
)

if "Ship Date" in df.columns:
    df["Ship Date"] = pd.to_datetime(
        df["Ship Date"], errors="coerce", dayfirst=False
    )

# =========================================================
# REMOVE INVALID ROWS
# =========================================================
df = df.dropna(
    subset=[
        "Order ID", "Order Date", "Geography", "Category",
        "Product Name", "Sales", "Quantity", "Profit"
    ]
).copy()

if df.empty:
    st.error("No valid sales records were found in the CSV.")
    st.stop()

# =========================================================
# CENTERED LOGO
# =========================================================
if LOGO_PATH.exists():
    with open(LOGO_PATH, "rb") as logo_file:
        logo_base64 = base64.b64encode(
            logo_file.read()
        ).decode("utf-8")

    st.markdown(
        f"""
        <div style="
            width:100%;
            display:flex;
            justify-content:center;
            align-items:center;
            margin:0 auto 12px auto;
        ">
            <img
                src="data:image/jpeg;base64,{logo_base64}"
                alt="Amazon Logo"
                style="
                    display:block;
                    width:180px;
                    max-width:100%;
                    height:auto;
                    object-fit:contain;
                    margin:0 auto;
                "
            />
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<div style='text-align:center;font-size:48px;'>📦</div>",
        unsafe_allow_html=True
    )

# =========================================================
# DASHBOARD TITLE
# =========================================================
st.markdown("""
<h1 style="
    text-align:center;
    color:#38bdf8;
    font-size:36px;
    font-weight:800;
    margin-bottom:5px;
">AMAZON SALES DASHBOARD</h1>

<p style="
    text-align:center;
    color:#94a3b8;
    font-size:15px;
    margin-top:0;
">Sales Performance • Profitability • Product Analytics</p>
""", unsafe_allow_html=True)

st.divider()

# =========================================================
# TWO FILTERS
# =========================================================
st.subheader("🔎 Dashboard Filters")

filter1, filter2 = st.columns(2)

categories = sorted(df["Category"].dropna().unique().tolist())
geographies = sorted(df["Geography"].dropna().unique().tolist())

with filter1:
    selected_categories = st.multiselect(
        "Category",
        options=categories,
        default=categories,
        key="category_filter"
    )

with filter2:
    selected_geographies = st.multiselect(
        "Geography",
        options=geographies,
        default=geographies,
        key="geography_filter"
    )

filtered_df = df[
    df["Category"].isin(selected_categories)
    & df["Geography"].isin(selected_geographies)
].copy()

if filtered_df.empty:
    st.warning(
        "No records match these filters. "
        "Select at least one category and geography."
    )
    st.stop()

# =========================================================
# KPI CALCULATIONS
# =========================================================
total_sales = filtered_df["Sales"].sum()
total_profit = filtered_df["Profit"].sum()
total_quantity = filtered_df["Quantity"].sum()
total_orders = filtered_df["Order ID"].nunique()

average_sales = filtered_df["Sales"].mean()
average_profit = filtered_df["Profit"].mean()
total_products = filtered_df["Product Name"].nunique()

# =========================================================
# COLORFUL KPI CARDS
# =========================================================
st.markdown("## 📊 Key Performance Indicators")

kpi_colors = ["#38bdf8", "#34d399", "#fbbf24", "#c084fc"]
kpi_columns = st.columns(4)

kpi_data = [
    ("💰 Total Sales", f"{total_sales:,.2f}", kpi_colors[0]),
    ("📈 Total Profit", f"{total_profit:,.2f}", kpi_colors[1]),
    ("📦 Total Quantity", f"{total_quantity:,.0f}", kpi_colors[2]),
    ("🛒 Total Orders", f"{total_orders:,}", kpi_colors[3])
]

for col, (label, value, color) in zip(kpi_columns, kpi_data):
    with col:
        st.markdown(
            f"""
            <div style="
                background:linear-gradient(135deg,#172033,#202d45);
                border:1px solid {color};
                border-left:5px solid {color};
                padding:18px;
                border-radius:14px;
                min-height:125px;
                box-shadow:0 5px 18px rgba(0,0,0,0.25);
            ">
                <div style="color:{color};font-size:15px;font-weight:700;">
                    {label}
                </div>
                <div style="
                    color:#ffffff;
                    font-size:27px;
                    font-weight:800;
                    margin-top:14px;
                    overflow-wrap:anywhere;
                ">{value}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# =========================================================
# REUSABLE GAUGE CHART
# =========================================================
def create_gauge(title, value, color, suffix=""):
    upper = max(abs(float(value)) * 1.25, 1.0)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(value),
            number={
                "valueformat": ",.2f",
                "suffix": suffix,
                "font": {"size": 25, "color": "#f8fafc"}
            },
            title={
                "text": title,
                "font": {"size": 17, "color": "#f8fafc"}
            },
            gauge={
                "axis": {
                    "range": [0, upper],
                    "tickcolor": "#cbd5e1"
                },
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "#111827",
                "borderwidth": 1,
                "bordercolor": "#334155",
                "steps": [
                    {"range": [0, upper * 0.33], "color": "#253047"},
                    {"range": [upper * 0.33, upper * 0.66], "color": "#1e3a4b"},
                    {"range": [upper * 0.66, upper], "color": "#164e63"}
                ],
                "threshold": {
                    "line": {"color": "#f8fafc", "width": 3},
                    "thickness": 0.8,
                    "value": float(value)
                }
            }
        )
    )

    fig.update_layout(
        height=260,
        margin=dict(l=25, r=25, t=55, b=15),
        paper_bgcolor="#111827",
        font_color="#f8fafc"
    )
    return fig

# =========================================================
# THREE GAUGE CHARTS
# =========================================================
st.markdown("## 🎯 Performance Gauges")

g1, g2, g3 = st.columns(3)

with g1:
    st.plotly_chart(
        create_gauge("Average Sales", average_sales, "#38bdf8"),
        use_container_width=True
    )

with g2:
    st.plotly_chart(
        create_gauge("Average Profit", average_profit, "#34d399"),
        use_container_width=True
    )

with g3:
    st.plotly_chart(
        create_gauge("Total Products", total_products, "#c084fc"),
        use_container_width=True
    )

# =========================================================
# DEFAULT PLOTLY STYLE
# =========================================================
PLOT_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#111827",
    plot_bgcolor="#111827",
    font=dict(color="#f8fafc"),
    margin=dict(l=35, r=25, t=65, b=40),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0
    )
)

# =========================================================
# TOP 5 GEOGRAPHIES BY SALES - PIE CHART
# VERTICAL LEGEND ON THE RIGHT
# =========================================================
st.markdown("## 🌍 Sales by Geography")

geo_sales = (
    filtered_df.groupby("Geography", as_index=False)["Sales"]
    .sum()
    .sort_values("Sales", ascending=False)
    .head(5)
)

fig_geo = px.pie(
    geo_sales,
    names="Geography",
    values="Sales",
    title="Top 5 Geographies by Sales",
    color_discrete_sequence=[
        "#38bdf8", "#34d399", "#fbbf24",
        "#c084fc", "#fb7185"
    ],
    hole=0.35
)

fig_geo.update_traces(
    textposition="inside",
    textinfo="percent",
    showlegend=True,
    hovertemplate=(
        "<b>%{label}</b><br>"
        "Sales: %{value:,.2f}<br>"
        "Share: %{percent}<extra></extra>"
    )
)

# Override the default horizontal legend for this chart only
fig_geo.update_layout(
    template="plotly_dark",
    paper_bgcolor="#111827",
    plot_bgcolor="#111827",
    font=dict(color="#f8fafc"),
    title=dict(
        text="Top 5 Geographies by Sales",
        x=0.02,
        xanchor="left"
    ),
    legend=dict(
        orientation="v",
        title=dict(text="Geography"),
        x=1.02,
        xanchor="left",
        y=0.5,
        yanchor="middle",
        font=dict(size=13, color="#f8fafc")
    ),
    margin=dict(l=20, r=160, t=65, b=25),
    height=420
)

st.plotly_chart(fig_geo, use_container_width=True)

# =========================================================
# MONTHLY SALES TREND
# =========================================================
st.markdown("## 📈 Sales Trend")

trend_df = filtered_df.copy()
trend_df["Order Month"] = (
    trend_df["Order Date"].dt.to_period("M").dt.to_timestamp()
)

monthly_sales = (
    trend_df.groupby("Order Month", as_index=False)["Sales"]
    .sum()
    .sort_values("Order Month")
)

fig_trend = px.line(
    monthly_sales,
    x="Order Month",
    y="Sales",
    markers=True,
    title="Monthly Sales Trend",
    color_discrete_sequence=["#38bdf8"]
)

fig_trend.update_traces(
    line=dict(width=3),
    marker=dict(size=7),
    hovertemplate=(
        "Month: %{x|%b %Y}<br>"
        "Sales: %{y:,.2f}<extra></extra>"
    )
)

fig_trend.update_layout(**PLOT_LAYOUT, height=420)
fig_trend.update_xaxes(title="Month")
fig_trend.update_yaxes(title="Sales")
st.plotly_chart(fig_trend, use_container_width=True)

# =========================================================
# CATEGORY ANALYSIS: SALES AND PROFIT
# =========================================================
st.markdown("## 📊 Category Analysis")

category_analysis = (
    filtered_df.groupby("Category", as_index=False)
    .agg(
        Sales=("Sales", "sum"),
        Profit=("Profit", "sum")
    )
    .sort_values("Sales", ascending=False)
)

fig_category = go.Figure()

fig_category.add_trace(
    go.Bar(
        x=category_analysis["Category"],
        y=category_analysis["Sales"],
        name="Sales by Category",
        marker_color="#38bdf8",
        hovertemplate="%{x}<br>Sales: %{y:,.2f}<extra></extra>"
    )
)

fig_category.add_trace(
    go.Bar(
        x=category_analysis["Category"],
        y=category_analysis["Profit"],
        name="Profit by Category",
        marker_color="#34d399",
        hovertemplate="%{x}<br>Profit: %{y:,.2f}<extra></extra>"
    )
)

fig_category.update_layout(
    **PLOT_LAYOUT,
    title="Sales and Profit by Category",
    barmode="group",
    height=450,
    xaxis_title="Category",
    yaxis_title="Amount"
)

st.plotly_chart(fig_category, use_container_width=True)

# =========================================================
# QUANTITY BY CATEGORY
# =========================================================
st.markdown("## 📦 Quantity by Category")

quantity_category = (
    filtered_df.groupby("Category", as_index=False)["Quantity"]
    .sum()
    .sort_values("Quantity", ascending=False)
)

fig_quantity = px.bar(
    quantity_category,
    x="Category",
    y="Quantity",
    title="Total Quantity by Category",
    text_auto=".0f",
    color="Quantity",
    color_continuous_scale=["#164e63", "#38bdf8", "#c084fc"]
)

fig_quantity.update_layout(
    **PLOT_LAYOUT,
    height=420,
    xaxis_title="Category",
    yaxis_title="Total Quantity",
    coloraxis_showscale=False
)

st.plotly_chart(fig_quantity, use_container_width=True)

# =========================================================
# TOP 20 PRODUCTS BY SALES
# =========================================================
st.markdown("## 🏆 Top 20 Products by Sales")

product_sales = (
    filtered_df.groupby("Product Name", as_index=False)["Sales"]
    .sum()
    .sort_values("Sales", ascending=False)
    .head(20)
    .sort_values("Sales", ascending=True)
)

fig_products = px.bar(
    product_sales,
    x="Sales",
    y="Product Name",
    orientation="h",
    title="Top 20 Products by Total Sales",
    text_auto=".2s",
    color="Sales",
    color_continuous_scale=["#164e63", "#2563eb", "#38bdf8"]
)

fig_products.update_layout(
    **PLOT_LAYOUT,
    height=max(500, len(product_sales) * 28),
    xaxis_title="Total Sales",
    yaxis_title="Product",
    coloraxis_showscale=False
)

st.plotly_chart(fig_products, use_container_width=True)

# =========================================================
# DOWNLOAD OPTIONS
# =========================================================
st.divider()
st.markdown("## 📥 Download Data")

download1, download2 = st.columns(2)

with download1:
    st.download_button(
        label="⬇️ Download Filtered Sales Data (CSV)",
        data=filtered_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="amazon_filtered_sales.csv",
        mime="text/csv",
        use_container_width=True
    )

with download2:
    st.download_button(
        label="⬇️ Download Full Sales Data (CSV)",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="amazon_full_sales.csv",
        mime="text/csv",
        use_container_width=True
    )

# =========================================================
# FOOTER
# =========================================================
st.markdown("""
<hr>
<p style="
    text-align:center;
    color:#94a3b8;
    font-size:13px;
">
Submitted by MELVIN PRASAD
    AMAZON SALES DASHBOARD | Built with Python,
    Streamlit, Pandas and Plotly
    
</p>
""", unsafe_allow_html=True)

"""
⚡ BESS Trading Terminal — Streamlit App
Battery Energy Storage System Optimizer for European Electricity Markets
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
from datetime import date

from engine import generate_prices, run_optimizer, allocate_reserves, compute_financials
from report import build_report

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚡ BESS Trading Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Barlow+Condensed:wght@400;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace !important;
}

/* Header */
.main-header {
    background: linear-gradient(135deg, #0a1525 0%, #0d1f38 100%);
    border: 1px solid #162840;
    border-radius: 4px;
    padding: 16px 24px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.main-title {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 28px; font-weight: 900;
    color: #f59e0b; letter-spacing: 0.06em;
    margin: 0;
}
.market-tag {
    display: inline-block;
    font-size: 11px; padding: 2px 8px;
    border: 1px solid #4ade8055; color: #4ade80;
    border-radius: 2px; margin-right: 4px;
}

/* KPI Cards */
.kpi-card {
    background: #0e1d30;
    border: 1px solid #162840;
    border-radius: 4px;
    padding: 14px 16px;
    text-align: left;
}
.kpi-label {
    font-size: 9px; color: #4a7090;
    letter-spacing: 0.1em; text-transform: uppercase;
    margin-bottom: 4px;
}
.kpi-value {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 26px; font-weight: 700;
    line-height: 1;
}
.kpi-sub { font-size: 9px; color: #4a7090; margin-top: 3px; }

/* Section labels */
.sec-label {
    display: flex; align-items: center; gap: 8px;
    font-size: 9px; color: #f59e0b;
    letter-spacing: 0.12em; text-transform: uppercase;
    margin-bottom: 10px; margin-top: 4px;
}
.sec-line { flex: 1; height: 1px;
    background: linear-gradient(to right, #92610a, transparent); }

/* Callout boxes */
.callout { border-radius: 4px; padding: 12px 16px; margin: 10px 0; }
.callout-green  { background: #052e16; border-left: 4px solid #4ade80; }
.callout-amber  { background: #1c1106; border-left: 4px solid #f59e0b; }
.callout-red    { background: #1c0707; border-left: 4px solid #f87171; }
.callout-blue   { background: #0c1a2e; border-left: 4px solid #22d3ee; }
.callout-title  { font-weight: 700; font-size: 11px; margin-bottom: 4px; }
.callout-body   { font-size: 10px; color: #c4ddf0; white-space: pre-line; }

/* Cycle progress bar */
.cycle-track {
    height: 22px; background: #162840;
    border-radius: 3px; overflow: hidden; position: relative;
    border: 1px solid #1d3450;
}
.cycle-fill {
    height: 100%; transition: width 0.5s ease;
    border-radius: 2px;
}
.cycle-label {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; color: #e8f4ff;
    font-family: 'Barlow Condensed', sans-serif;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0a1525 !important;
    border-right: 1px solid #162840;
}
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stNumberInput label,
section[data-testid="stSidebar"] .stSelectbox label { font-size: 10px !important; }

/* Tables */
.dataframe { font-size: 11px !important; }
.stDataFrame { border: 1px solid #162840 !important; }

/* Streamlit overrides */
div[data-testid="metric-container"] { background: #0e1d30; border: 1px solid #162840; border-radius: 4px; padding: 12px; }
.element-container { animation: fadeUp 0.25s ease; }
@keyframes fadeUp { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# PLOTLY DARK THEME
# ─────────────────────────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="#050b14",
    plot_bgcolor="#0a1525",
    font=dict(family="JetBrains Mono", size=10, color="#c4ddf0"),
    legend=dict(bgcolor="#0a1525", bordercolor="#162840", borderwidth=1, font=dict(size=9)),
    margin=dict(l=50, r=30, t=30, b=40),
    height=280,
)

def apply_theme(fig, **kwargs):
    fig.update_layout(**PLOT_LAYOUT, **kwargs)
    fig.update_xaxes(gridcolor="#162840", linecolor="#162840")
    fig.update_yaxes(gridcolor="#162840", linecolor="#162840")
    return fig

AMBER   = "#f59e0b"
CYAN    = "#22d3ee"
GREEN   = "#4ade80"
RED     = "#f87171"
PURPLE  = "#a78bfa"
BLUE    = "#60a5fa"
WHITE   = "#e8f4ff"
DIM     = "#4a7090"

# ─────────────────────────────────────────────────────────────────
# HELPER: KPI CARD HTML
# ─────────────────────────────────────────────────────────────────
def kpi_card(label, value, unit="", sub="", color=WHITE):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color:{color}">{value}<span style="font-size:13px;font-weight:400;color:{DIM};margin-left:3px">{unit}</span></div>
        {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>"""

def callout(label, text, variant="blue"):
    return f"""<div class="callout callout-{variant}">
        <div class="callout-title" style="color:{'#4ade80' if variant=='green' else '#f59e0b' if variant=='amber' else '#f87171' if variant=='red' else '#22d3ee'}">{label}</div>
        <div class="callout-body">{text}</div>
    </div>"""

def sec_label(text):
    return f'<div class="sec-label"><div style="width:12px;height:1px;background:#f59e0b"></div>{text}<div class="sec-line"></div></div>'

# ─────────────────────────────────────────────────────────────────
# SIDEBAR INPUTS
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-family:\'Barlow Condensed\',sans-serif;font-size:20px;font-weight:900;color:#f59e0b;letter-spacing:0.06em;margin:0">⚡ BESS TERMINAL</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:9px;color:#4a7090;margin-top:-4px">v2.4.1 · DE-LU · EPEX SPOT · ENTSO-E</p>', unsafe_allow_html=True)
    st.divider()

    # ── Battery ─────────────────────────────────────────────────
    st.markdown("**🔋 Battery Configuration**")
    cap_mwh      = st.slider("Capacity (MWh)",    1.0, 100.0, 10.0, 1.0)
    pwr_mw       = st.slider("Max Power (MW)",     0.5,  50.0,  5.0, 0.5)
    min_soc_pct  = st.slider("Min SOC (%)",          0,    40,   10,   5)
    max_soc_pct  = st.slider("Max SOC (%)",         60,   100,   90,   5)
    eta          = st.slider("Round-Trip Eff. (%)", 75,    99,   92,   1)
    deg_cost     = st.slider("Degradation (€/MWh)", 0.5,  8.0,  2.5, 0.1)

    # ── Cycles per day ──────────────────────────────────────────
    st.divider()
    st.markdown("**🔄 Cycles Per Day**")
    cycles_per_day = st.slider("Daily Cycle Limit", 0.25, 3.0, 1.0, 0.25)
    c1, c2 = st.columns(2)
    c1.metric("Max Throughput", f"{cycles_per_day*cap_mwh*2:.1f} MWh/d", label_visibility="visible")
    c2.metric("C-Rate", f"{pwr_mw/cap_mwh:.2f}C", label_visibility="visible")
    c1.metric("Duration", f"{cap_mwh/pwr_mw:.1f} h", label_visibility="visible")
    c2.metric("Usable", f"{(max_soc_pct-min_soc_pct)/100*cap_mwh:.1f} MWh", label_visibility="visible")

    # ── Markets ─────────────────────────────────────────────────
    st.divider()
    st.markdown("**📊 Market Participation**")
    col1, col2 = st.columns(2)
    m_da   = col1.checkbox("Day-Ahead",   value=True)
    m_fcr  = col2.checkbox("FCR",         value=True)
    m_afrr = col1.checkbox("aFRR",        value=True)
    m_mfrr = col2.checkbox("mFRR",        value=True)

    st.markdown("**📈 Price Scenario**")
    scenario = st.selectbox("Scenario", [
        "normal", "high", "low", "volatile", "neg"
    ], format_func=lambda s: {
        "normal":   "◆ Normal (avg €80/MWh)",
        "high":     "◆ High Prices (€120/MWh)",
        "low":      "◆ Low / RE Surplus (€50/MWh)",
        "volatile": "◆ High Volatility (±€40 std)",
        "neg":      "◆ Negative Price Events",
    }[s])
    seed = st.number_input("Simulation Seed", min_value=1, max_value=99999, value=42)

    # ── Financial & Loan ────────────────────────────────────────
    st.divider()
    st.markdown("**💰 Financial & Loan Parameters**")
    capex_per_kwh   = st.number_input("CAPEX (€/kWh)",    150, 700, 350, 10)
    equity_pct      = st.slider("Equity (%)",               10, 100,  30,   5)
    loan_rate       = st.number_input("Loan Rate (% p.a.)", 1.0, 15.0, 5.5, 0.1, format="%.1f")
    loan_term_yrs   = st.number_input("Loan Term (years)",    3,   20,  12,   1)
    annual_om_pct   = st.number_input("Annual O&M (% CAPEX)", 0.5, 5.0, 1.5, 0.1, format="%.1f")
    insurance_pct   = st.number_input("Insurance (% CAPEX)",  0.1, 2.0, 0.5, 0.1, format="%.1f")
    discount_rate   = st.number_input("Discount Rate (%)",     3.0,20.0, 8.0, 0.5, format="%.1f")
    project_life    = st.number_input("Project Life (years)",    5,   25,  15,   1)
    ann_deg_pct     = st.number_input("Annual Degradation (%)",  0.5, 5.0, 2.0, 0.1, format="%.1f")

    total_capex_disp = capex_per_kwh * cap_mwh * 1000
    st.markdown(f'<p style="font-size:9px;color:#4a7090">Total CAPEX: <b style="color:#f59e0b">€{total_capex_disp:,.0f}</b> | Equity: <b style="color:#22d3ee">€{total_capex_disp*equity_pct/100:,.0f}</b></p>', unsafe_allow_html=True)

    st.divider()
    run_btn = st.button("▶  RUN OPTIMIZER", type="primary", use_container_width=True)


# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <span class="main-title">⚡ BESS TRADING TERMINAL</span>
  <span style="font-size:9px;color:#4a7090">DE-LU · EPEX SPOT · ENTSO-E · v2.4.1</span>
  <div style="flex:1"></div>
  <span class="market-tag">● FCR</span>
  <span class="market-tag">● aFRR</span>
  <span class="market-tag">● mFRR</span>
  <span class="market-tag">● EPEX</span>
  <span class="market-tag">● DP-OPT</span>
  <span style="font-size:9px;color:#4a7090;margin-left:8px">""" + date.today().strftime("%d %b %Y") + """</span>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────
if "sim_done" not in st.session_state:
    st.session_state.sim_done     = False
    st.session_state.prices_df    = None
    st.session_state.schedule_df  = None
    st.session_state.reserves     = None
    st.session_state.throughput   = None
    st.session_state.actual_cycles= None
    st.session_state.fin          = None
    st.session_state.bat_snap     = None
    st.session_state.fin_snap     = None
    st.session_state.scenario_snap= None


# ─────────────────────────────────────────────────────────────────
# RUN OPTIMIZER
# ─────────────────────────────────────────────────────────────────
if run_btn:
    markets_dict = {"da": m_da, "fcr": m_fcr, "afrr": m_afrr, "mfrr": m_mfrr}
    bat_dict = dict(
        cap_mwh=cap_mwh, pwr_mw=pwr_mw,
        min_soc_pct=min_soc_pct, max_soc_pct=max_soc_pct,
        eta=eta, deg_cost=deg_cost, cycles_per_day=cycles_per_day
    )
    fin_dict = dict(
        capex_per_kwh=capex_per_kwh, equity_pct=equity_pct,
        loan_rate=float(loan_rate), loan_term_yrs=int(loan_term_yrs),
        annual_om_pct=float(annual_om_pct), insurance_pct=float(insurance_pct),
        discount_rate=float(discount_rate), project_life_yrs=int(project_life),
        annual_deg_pct=float(ann_deg_pct)
    )

    with st.spinner("⟳  Running Dynamic Programming optimizer…"):
        prices_df = generate_prices(scenario, seed)
        schedule_df, reserves, throughput = run_optimizer(
            cap_mwh, pwr_mw, min_soc_pct, max_soc_pct, eta, deg_cost, cycles_per_day,
            prices_df, markets_dict
        )
        actual_cycles = throughput / (cap_mwh * 2)
        net_day = schedule_df["net"].sum()

        fin = compute_financials(
            cap_mwh, pwr_mw,
            capex_per_kwh, equity_pct, float(loan_rate), int(loan_term_yrs),
            float(annual_om_pct), float(insurance_pct), float(discount_rate), int(project_life),
            float(ann_deg_pct),
            net_day, throughput
        )

        st.session_state.sim_done      = True
        st.session_state.prices_df     = prices_df
        st.session_state.schedule_df   = schedule_df
        st.session_state.reserves      = reserves
        st.session_state.throughput    = throughput
        st.session_state.actual_cycles = actual_cycles
        st.session_state.fin           = fin
        st.session_state.bat_snap      = bat_dict
        st.session_state.fin_snap      = fin_dict
        st.session_state.scenario_snap = scenario
        st.session_state.markets_snap  = markets_dict


# ─────────────────────────────────────────────────────────────────
# DISPLAY RESULTS
# ─────────────────────────────────────────────────────────────────
if not st.session_state.sim_done:
    st.markdown("""
    <div style="text-align:center;padding:80px 20px;color:#1e3a5a">
      <div style="font-size:72px;opacity:0.15">⚡</div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:28px;color:#4a7090;margin-top:16px">
        Configure battery and click RUN OPTIMIZER
      </div>
      <div style="font-size:11px;color:#1d3450;margin-top:12px;line-height:1.8;max-width:480px;margin-left:auto;margin-right:auto">
        Set battery specs, cycles/day limit, loan parameters and market selection.<br>
        The DP engine will produce an optimal dispatch schedule and full financial analysis.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Unpack session state ────────────────────────────────────────
prices_df     = st.session_state.prices_df
schedule_df   = st.session_state.schedule_df
reserves      = st.session_state.reserves
throughput    = st.session_state.throughput
actual_cycles = st.session_state.actual_cycles
fin           = st.session_state.fin
bat_snap      = st.session_state.bat_snap
fin_snap      = st.session_state.fin_snap
scenario_snap = st.session_state.scenario_snap
markets_snap  = st.session_state.markets_snap

net_day    = schedule_df["net"].sum()
total_da   = schedule_df["da_rev"].sum()
total_fcr  = schedule_df["fcr_rev"].sum()
total_afrr = schedule_df["afrr_rev"].sum()
total_mfrr = schedule_df["mfrr_rev"].sum()
total_deg  = schedule_df["deg_cost"].sum()

# ─────────────────────────────────────────────────────────────────
# KPI BAR
# ─────────────────────────────────────────────────────────────────
cols = st.columns(9)
kpi_data = [
    ("Net Daily Profit",   f"€{abs(net_day):,.0f}",   "",       f"€{net_day*365:,.0f}/yr",   GREEN if net_day>=0 else RED),
    ("Day-Ahead Rev",      f"€{total_da:,.0f}",        "",       f"€{total_da*365:,.0f}/yr",  AMBER),
    ("FCR Revenue",        f"€{total_fcr:,.0f}",       "",       f"€{total_fcr*365:,.0f}/yr", CYAN),
    ("aFRR Revenue",       f"€{total_afrr:,.0f}",      "",       f"€{total_afrr*365:,.0f}/yr",GREEN),
    ("Cycles/Day",         f"{actual_cycles:.2f}",     f"/{bat_snap['cycles_per_day']}x", f"{throughput:.1f} MWh throughput", AMBER if actual_cycles > bat_snap['cycles_per_day']*0.95 else GREEN),
    ("Equity IRR",         f"{fin['irr_equity']:.1f}", "%",      f"NPV €{fin['npv_equity']/1000:.0f}k", GREEN if fin["irr_equity"]>=10 else AMBER if fin["irr_equity"]>=7 else RED),
    ("Min DSCR",           f"{fin['min_dscr']:.2f}",   "x",      f"Payback {fin['payback']:.1f} yr",    GREEN if fin["min_dscr"]>=1.25 else AMBER if fin["min_dscr"]>=1.1 else RED),
    ("LCOS",               f"€{fin['lcos']:.1f}",      "/MWh",   f"{int(project_life)} yr life",         WHITE),
    ("Total CAPEX",        f"€{fin['total_capex']/1000:.0f}k", "", f"{equity_pct}% eq / {100-equity_pct}% debt", WHITE),
]
for c, (lbl, val, unit, sub, col) in zip(cols, kpi_data):
    c.markdown(kpi_card(lbl, val, unit, sub, col), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────
tab_prices, tab_dispatch, tab_soc, tab_revenue, tab_financial, tab_report = st.tabs([
    "📈 PRICES", "⚡ DISPATCH", "🔋 SOC", "💶 REVENUE", "💰 FINANCIAL", "📄 REPORT"
])


# ─── PRICES TAB ─────────────────────────────────────────────────
with tab_prices:
    st.markdown(sec_label("EPEX Day-Ahead Prices — DE-LU"), unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=prices_df["time"], y=prices_df["da"],
        name="DA Price", line=dict(color=AMBER, width=2),
        fill="tozeroy", fillcolor="rgba(245,158,11,0.12)"
    ))
    fig.add_hline(y=0, line_color=RED, line_dash="dash", line_width=1)
    fig.update_layout(**PLOT_LAYOUT, yaxis_title="€/MWh", height=230)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(sec_label("FCR Capacity Price"), unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=prices_df["time"], y=prices_df["fcr"],
            name="FCR", line=dict(color=CYAN, width=2, shape="hv")))
        fig2.update_layout(**PLOT_LAYOUT, yaxis_title="€/MW/h", height=180)
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.markdown(sec_label("aFRR Capacity Prices"), unsafe_allow_html=True)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=prices_df["time"], y=prices_df["afrr_u"],
            name="aFRR↑", line=dict(color=GREEN, width=2)))
        fig3.add_trace(go.Scatter(x=prices_df["time"], y=prices_df["afrr_d"],
            name="aFRR↓", line=dict(color=PURPLE, width=2)))
        fig3.update_layout(**PLOT_LAYOUT, yaxis_title="€/MW/h", height=180)
        st.plotly_chart(fig3, use_container_width=True)

    with c3:
        st.markdown(sec_label("Market Summary"), unsafe_allow_html=True)
        summary = pd.DataFrame({
            "Metric": ["DA Peak", "DA Valley", "DA Average", "DA Spread", "FCR Avg", "aFRR↑ Avg", "aFRR↓ Avg", "mFRR Avg"],
            "Value": [
                f"€{prices_df['da'].max():.1f}/MWh",
                f"€{prices_df['da'].min():.1f}/MWh",
                f"€{prices_df['da'].mean():.1f}/MWh",
                f"€{prices_df['da'].max()-prices_df['da'].min():.1f}/MWh",
                f"€{prices_df['fcr'].mean():.2f}/MW/h",
                f"€{prices_df['afrr_u'].mean():.2f}/MW/h",
                f"€{prices_df['afrr_d'].mean():.2f}/MW/h",
                f"€{prices_df['mfrr_c'].mean():.2f}/MW/h",
            ]
        })
        st.dataframe(summary, hide_index=True, use_container_width=True, height=215)


# ─── DISPATCH TAB ───────────────────────────────────────────────
with tab_dispatch:
    st.markdown(sec_label(f"Power Dispatch — Cycles Used: {actual_cycles:.2f}/{bat_snap['cycles_per_day']}x per day"), unsafe_allow_html=True)

    # Cycle progress bar
    pct_used = min(100, actual_cycles / bat_snap["cycles_per_day"] * 100)
    bar_color = "#f87171" if pct_used > 97 else "#f59e0b" if pct_used > 80 else "#4ade80"
    st.markdown(f"""
    <div class="cycle-track">
      <div class="cycle-fill" style="width:{pct_used:.1f}%;background:linear-gradient(to right,#4ade80,{bar_color})"></div>
      <div class="cycle-label">{actual_cycles:.3f}x / {bat_snap['cycles_per_day']}x limit  ({pct_used:.1f}% used)  —  {throughput:.2f} MWh total throughput</div>
    </div>
    <br>
    """, unsafe_allow_html=True)

    # Main dispatch chart
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=schedule_df["time"], y=-schedule_df["chg"],
        name="Charging", marker_color=CYAN, opacity=0.85), secondary_y=False)
    fig.add_trace(go.Bar(x=schedule_df["time"], y=schedule_df["dch"],
        name="Discharge", marker_color=AMBER, opacity=0.85), secondary_y=False)
    fig.add_trace(go.Bar(x=schedule_df["time"], y=schedule_df["fcr_mw"],
        name="FCR Reserved", marker_color=CYAN, opacity=0.3), secondary_y=False)
    fig.add_trace(go.Bar(x=schedule_df["time"], y=schedule_df["afrr_u_mw"],
        name="aFRR↑ Reserved", marker_color=GREEN, opacity=0.3), secondary_y=False)
    fig.add_trace(go.Scatter(x=schedule_df["time"], y=schedule_df["da_price"],
        name="DA Price", line=dict(color=AMBER, width=1.5, dash="dot"),
        opacity=0.9), secondary_y=True)
    fig.add_hline(y=0, line_color="#1d3450", line_width=2, secondary_y=False)
    fig.update_layout(**PLOT_LAYOUT, barmode="relative", height=300,
                      yaxis_title="Power (MW)", yaxis2_title="DA Price (€/MWh)")
    fig.update_layout(paper_bgcolor="#050b14", plot_bgcolor="#0a1525")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(sec_label("Cumulative Cycles Progress"), unsafe_allow_html=True)
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=schedule_df["time"], y=schedule_df["cum_cycles"],
            name="Cum. Cycles", line=dict(color=AMBER, width=2),
            fill="tozeroy", fillcolor="rgba(245,158,11,0.1)"))
        fig4.add_hline(y=bat_snap["cycles_per_day"], line_color=RED,
                       line_dash="dash", line_width=1.5,
                       annotation_text="Limit", annotation_position="top right")
        fig4.update_layout(**PLOT_LAYOUT, yaxis_title="Cycles", height=200)
        st.plotly_chart(fig4, use_container_width=True)

    with c2:
        st.markdown(sec_label("Reserve Allocation"), unsafe_allow_html=True)
        fig5 = go.Figure()
        for col, name, clr in [("fcr_mw","FCR",CYAN),("afrr_u_mw","aFRR↑",GREEN),("afrr_d_mw","aFRR↓",PURPLE),("mfrr_mw","mFRR",BLUE)]:
            fig5.add_trace(go.Bar(x=schedule_df["time"], y=schedule_df[col],
                name=name, marker_color=clr, opacity=0.85))
        fig5.update_layout(**PLOT_LAYOUT, barmode="stack", height=200, yaxis_title="MW")
        st.plotly_chart(fig5, use_container_width=True)

    # Schedule table
    with st.expander("📋 Hourly Dispatch Schedule"):
        disp = schedule_df[["time","da_price","soc_pct","dch","chg","fcr_mw","afrr_u_mw","da_rev","fcr_rev","afrr_rev","net","cum_net"]].copy()
        disp.columns = ["Hour","DA Price","SOC%","Discharge MW","Charge MW","FCR MW","aFRR↑ MW","DA Rev","FCR Rev","aFRR Rev","Net","Cum P&L"]
        st.dataframe(disp.style.format({
            "DA Price": "€{:.1f}", "SOC%": "{:.1f}%",
            "Discharge MW": "{:.3f}", "Charge MW": "{:.3f}",
            "FCR MW": "{:.2f}", "aFRR↑ MW": "{:.2f}",
            "DA Rev": "€{:.2f}", "FCR Rev": "€{:.2f}",
            "aFRR Rev": "€{:.2f}", "Net": "€{:.2f}", "Cum P&L": "€{:.2f}"
        }), use_container_width=True)


# ─── SOC TAB ────────────────────────────────────────────────────
with tab_soc:
    st.markdown(sec_label("State of Charge — 24-Hour Profile"), unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=schedule_df["time"], y=schedule_df["soc_pct"],
        name="SOC", line=dict(color=CYAN, width=2.5),
        fill="tozeroy", fillcolor="rgba(34,211,238,0.12)"))
    fig.add_hline(y=bat_snap["max_soc_pct"], line_color=RED, line_dash="dash",
                  annotation_text=f"Max {bat_snap['max_soc_pct']}%", annotation_position="top right")
    fig.add_hline(y=bat_snap["min_soc_pct"], line_color=PURPLE, line_dash="dash",
                  annotation_text=f"Min {bat_snap['min_soc_pct']}%", annotation_position="bottom right")
    fig.add_hline(y=50, line_color=DIM, line_dash="dot", line_width=1)
    fig.update_layout(**PLOT_LAYOUT, yaxis=dict(range=[0,105], title="SOC (%)"), height=260)
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(sec_label("SOC Energy (MWh)"), unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=schedule_df["time"], y=schedule_df["soc"],
            name="SOC (MWh)", line=dict(color=GREEN, width=2),
            fill="tozeroy", fillcolor="rgba(74,222,128,0.1)"))
        fig2.update_layout(**PLOT_LAYOUT, yaxis_title="MWh", height=200)
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        st.markdown(sec_label("SOC Statistics"), unsafe_allow_html=True)
        soc_stats = pd.DataFrame({
            "Metric": ["Initial SOC", "Final SOC", "Min SOC Reached", "Max SOC Reached",
                       "Average SOC", "Total Discharged", "Total Charged",
                       "Throughput", "Actual Cycles", "Cycles Limit"],
            "Value": [
                "50.0%",
                f"{schedule_df['soc_pct'].iloc[-1]:.1f}%",
                f"{schedule_df['soc_pct'].min():.1f}%",
                f"{schedule_df['soc_pct'].max():.1f}%",
                f"{schedule_df['soc_pct'].mean():.1f}%",
                f"{schedule_df['dch'].sum():.2f} MWh",
                f"{schedule_df['chg'].sum():.2f} MWh",
                f"{throughput:.2f} MWh",
                f"{actual_cycles:.3f}x",
                f"{bat_snap['cycles_per_day']}x/day",
            ]
        })
        st.dataframe(soc_stats, hide_index=True, use_container_width=True, height=360)


# ─── REVENUE TAB ────────────────────────────────────────────────
with tab_revenue:
    st.markdown(sec_label("Hourly P&L Breakdown + Cumulative Profit"), unsafe_allow_html=True)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for col, name, clr in [("da_rev","DA Revenue",AMBER),("fcr_rev","FCR Revenue",CYAN),
                            ("afrr_rev","aFRR Revenue",GREEN),("mfrr_rev","mFRR Revenue",PURPLE),
                            ("deg_cost","Degradation",RED)]:
        fig.add_trace(go.Bar(x=schedule_df["time"], y=schedule_df[col],
            name=name, marker_color=clr, opacity=0.85), secondary_y=False)
    fig.add_trace(go.Scatter(x=schedule_df["time"], y=schedule_df["cum_net"],
        name="Cum. P&L", line=dict(color=WHITE, width=2)), secondary_y=True)
    fig.add_hline(y=0, line_color="#1d3450", secondary_y=False)
    fig.update_layout(**PLOT_LAYOUT, barmode="relative", height=300,
                      yaxis_title="€/hour", yaxis2_title="Cumulative €")
    fig.update_layout(paper_bgcolor="#050b14", plot_bgcolor="#0a1525")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val, clr in [
        (c1, "Day-Ahead Revenue", total_da,   AMBER),
        (c2, "FCR Revenue",       total_fcr,  CYAN),
        (c3, "aFRR Revenue",      total_afrr, GREEN),
        (c4, "mFRR Revenue",      total_mfrr, PURPLE),
    ]:
        col.markdown(kpi_card(lbl, f"€{val:.2f}", "", f"€{val*365:,.0f}/yr", clr), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    # Pie chart
    pie_data = {k: v for k, v in [
        ("Day-Ahead", total_da), ("FCR", total_fcr), ("aFRR", total_afrr), ("mFRR", total_mfrr)
    ] if v > 0}
    if pie_data:
        c1, c2 = st.columns([1, 2])
        with c1:
            fig_pie = go.Figure(go.Pie(
                labels=list(pie_data.keys()),
                values=list(pie_data.values()),
                hole=0.45,
                marker_colors=[AMBER, CYAN, GREEN, PURPLE],
            ))
            fig_pie.update_layout(paper_bgcolor="#050b14", font=dict(color="#c4ddf0", size=10),
                                  height=220, margin=dict(l=10,r=10,t=20,b=10),
                                  legend=dict(bgcolor="#0a1525", bordercolor="#162840"))
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            rev_summary = pd.DataFrame({
                "Revenue Stream": ["Day-Ahead Arbitrage", "FCR Capacity", "aFRR (cap+act)", "mFRR (cap+act)", "Degradation Cost", "NET PROFIT"],
                "Daily": [f"€{total_da:.2f}", f"€{total_fcr:.2f}", f"€{total_afrr:.2f}", f"€{total_mfrr:.2f}", f"(€{abs(total_deg):.2f})", f"€{net_day:.2f}"],
                "Annual Est.": [f"€{total_da*365:,.0f}", f"€{total_fcr*365:,.0f}", f"€{total_afrr*365:,.0f}", f"€{total_mfrr*365:,.0f}", f"(€{abs(total_deg)*365:,.0f})", f"€{net_day*365:,.0f}"],
                "Share": [f"{total_da/max(net_day,1)*100:.1f}%", f"{total_fcr/max(net_day,1)*100:.1f}%", f"{total_afrr/max(net_day,1)*100:.1f}%", f"{total_mfrr/max(net_day,1)*100:.1f}%", "—", "100%"],
            })
            st.dataframe(rev_summary, hide_index=True, use_container_width=True)


# ─── FINANCIAL TAB ──────────────────────────────────────────────
with tab_financial:
    irr_color_css = "#4ade80" if fin["irr_equity"] >= 10 else "#f59e0b" if fin["irr_equity"] >= 7 else "#f87171"
    dscr_color_css= "#4ade80" if fin["min_dscr"] >= 1.25 else "#f59e0b" if fin["min_dscr"] >= 1.1 else "#f87171"
    npv_color_css = "#4ade80" if fin["npv_project"] >= 0 else "#f87171"

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(sec_label("Capital Structure"), unsafe_allow_html=True)
        cap_df = pd.DataFrame({
            "Item": ["Total CAPEX", "Equity", "Senior Debt", "Annual Debt Service",
                     "Loan Rate", "Loan Term", "Annual O&M", "Annual Insurance", "Total Fixed Costs"],
            "Value": [
                f"€{fin['total_capex']:,.0f}",
                f"€{fin['equity']:,.0f} ({equity_pct}%)",
                f"€{fin['loan_amt']:,.0f} ({100-equity_pct}%)",
                f"€{fin['ann_ds']:,.0f}/yr",
                f"{loan_rate:.1f}% p.a.",
                f"{loan_term_yrs} years",
                f"€{fin['ann_om']:,.0f}/yr",
                f"€{fin['ann_ins']:,.0f}/yr",
                f"€{fin['ann_fixed']:,.0f}/yr",
            ]
        })
        st.dataframe(cap_df, hide_index=True, use_container_width=True)

    with c2:
        st.markdown(sec_label("Investment KPIs"), unsafe_allow_html=True)
        kpi_df = pd.DataFrame({
            "KPI": ["Project NPV", "Equity NPV", "Project IRR", "Equity IRR",
                    "Simple Payback", "Min DSCR", "Avg DSCR", "LCOS"],
            "Value": [
                f"€{fin['npv_project']:,.0f}",
                f"€{fin['npv_equity']:,.0f}",
                f"{fin['irr_project']:.1f}%",
                f"{fin['irr_equity']:.1f}%",
                f"{fin['payback']:.1f} years",
                f"{fin['min_dscr']:.2f}x",
                f"{fin['avg_dscr']:.2f}x",
                f"€{fin['lcos']:.1f}/MWh",
            ],
            "Signal": [
                "✅" if fin["npv_project"] >= 0 else "❌",
                "✅" if fin["npv_equity"] >= 0 else "❌",
                "✅" if fin["irr_project"] >= 8 else "⚠️",
                "✅" if fin["irr_equity"] >= 10 else ("⚠️" if fin["irr_equity"] >= 7 else "❌"),
                "✅" if fin["payback"] <= 12 else "⚠️",
                "✅" if fin["min_dscr"] >= 1.25 else ("⚠️" if fin["min_dscr"] >= 1.1 else "❌"),
                "✅" if fin["avg_dscr"] >= 1.4 else "⚠️",
                "ℹ️",
            ]
        })
        st.dataframe(kpi_df, hide_index=True, use_container_width=True)

    # Cashflow chart
    st.markdown(sec_label("Annual Free Cashflow + DSCR Projection"), unsafe_allow_html=True)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    cf = fin["cf_df"]
    yr_labels = [f"Y{y}" for y in cf["year"]]
    fig.add_trace(go.Bar(x=yr_labels, y=cf["revenue"],
        name="Revenue", marker_color=AMBER, opacity=0.75), secondary_y=False)
    fig.add_trace(go.Bar(x=yr_labels, y=-cf["om"],
        name="O&M", marker_color=PURPLE, opacity=0.75), secondary_y=False)
    fig.add_trace(go.Bar(x=yr_labels, y=-cf["ds"],
        name="Debt Service", marker_color=RED, opacity=0.75), secondary_y=False)
    fig.add_trace(go.Scatter(x=yr_labels, y=cf["dscr"],
        name="DSCR", line=dict(color=CYAN, width=2.5)), secondary_y=True)
    fig.add_hline(y=0, line_color="#1d3450", secondary_y=False)
    fig.add_hline(y=1.25, line_color=GREEN, line_dash="dash",
                  annotation_text="1.25x floor", annotation_position="top right", secondary_y=True)
    fig.update_layout(**PLOT_LAYOUT, barmode="relative", height=280,
                      yaxis_title="€/year", yaxis2_title="DSCR (x)")
    fig.update_layout(paper_bgcolor="#050b14", plot_bgcolor="#0a1525")
    st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        # Loan amortisation
        st.markdown(sec_label("Loan Amortisation Schedule"), unsafe_allow_html=True)
        loan = fin["loan_df"].copy()
        loan.columns = ["Year", "Opening Bal", "Interest", "Principal", "Payment", "Closing Bal"]
        loan["Year"] = loan["Year"].apply(lambda y: f"Y{int(y)}")
        for col2 in ["Opening Bal", "Interest", "Principal", "Payment", "Closing Bal"]:
            loan[col2] = loan[col2].apply(lambda x: f"€{x:,.0f}")
        st.dataframe(loan, hide_index=True, use_container_width=True)

    with c2:
        # Annual FCF table
        st.markdown(sec_label("Annual Free Cashflow Table"), unsafe_allow_html=True)
        cf_show = cf[["year", "revenue", "om", "ebitda", "ds", "fcf", "dscr"]].copy()
        cf_show.columns = ["Year", "Revenue", "O&M", "EBITDA", "Debt Svc", "Free CF", "DSCR"]
        cf_show["Year"] = cf_show["Year"].apply(lambda y: f"Y{int(y)}")
        for col2 in ["Revenue", "O&M", "EBITDA", "Debt Svc", "Free CF"]:
            cf_show[col2] = cf_show[col2].apply(lambda x: f"€{x:,.0f}")
        cf_show["DSCR"] = cf_show["DSCR"].apply(lambda x: f"{x:.2f}x")
        st.dataframe(cf_show, hide_index=True, use_container_width=True)

    # DSCR / IRR signal
    dscr_sig = "STRONG" if fin["min_dscr"] >= 1.3 else ("ACCEPTABLE" if fin["min_dscr"] >= 1.1 else "AT RISK")
    irr_sig  = "ATTRACTIVE" if fin["irr_equity"] >= 12 else ("ACCEPTABLE" if fin["irr_equity"] >= 8 else "BELOW TARGET")
    dscr_var = "green" if dscr_sig == "STRONG" else ("amber" if dscr_sig == "ACCEPTABLE" else "red")
    irr_var  = "green" if irr_sig == "ATTRACTIVE" else ("amber" if irr_sig == "ACCEPTABLE" else "red")

    st.markdown(callout(
        f"DEBT SERVICEABILITY: {dscr_sig}",
        f"Min DSCR: {fin['min_dscr']:.2f}x  |  Avg DSCR: {fin['avg_dscr']:.2f}x\n"
        + ("Lenders typically require ≥1.25x — this project MEETS standard requirements." if fin["min_dscr"] >= 1.25
           else "Marginally meets minimum requirements — consider higher equity or cash reserves." if fin["min_dscr"] >= 1.1
           else "Does NOT meet standard DSCR requirements — restructure financing."),
        dscr_var
    ), unsafe_allow_html=True)

    st.markdown(callout(
        f"EQUITY IRR: {irr_sig} ({fin['irr_equity']:.1f}%)",
        f"Equity NPV: €{fin['npv_equity']:,.0f}  |  Project NPV: €{fin['npv_project']:,.0f}  |  Payback: {fin['payback']:.1f} years\n"
        + ("IRR exceeds 10–12% equity return threshold — proceed." if fin["irr_equity"] >= 10
           else "IRR meets 8–10% minimum — marginal viability." if fin["irr_equity"] >= 8
           else "IRR below typical thresholds — review project economics."),
        irr_var
    ), unsafe_allow_html=True)


# ─── REPORT TAB ─────────────────────────────────────────────────
with tab_report:
    st.markdown(sec_label("10–12 Page Investor Simulation Report"), unsafe_allow_html=True)
    irr_sig = "ATTRACTIVE" if fin["irr_equity"] >= 12 else ("ACCEPTABLE" if fin["irr_equity"] >= 8 else "BELOW TARGET")
    irr_var = "green" if irr_sig == "ATTRACTIVE" else ("amber" if irr_sig == "ACCEPTABLE" else "red")

    st.markdown(callout(
        f"📄 SIMULATION REPORT READY — RECOMMENDATION: {irr_sig}",
        f"Battery: {bat_snap['cap_mwh']} MWh / {bat_snap['pwr_mw']} MW  |  Scenario: {scenario_snap.upper()}  |  Date: {date.today().strftime('%d %B %Y')}\n"
        f"Net Daily Profit: €{net_day:,.2f}  |  Annual Est.: €{net_day*365:,.0f}  |  Equity IRR: {fin['irr_equity']:.1f}%  |  Min DSCR: {fin['min_dscr']:.2f}x\n"
        f"FCR: {reserves['fcr']:.2f} MW  |  aFRR↑: {reserves['afrr_u']:.2f} MW  |  Actual Cycles: {actual_cycles:.2f}x / {bat_snap['cycles_per_day']}x limit",
        irr_var
    ), unsafe_allow_html=True)

    # Report sections preview
    col1, col2, col3 = st.columns(3)
    for c, items in [(col1, ["Cover Page", "Executive Summary (8 KPIs)", "Battery Configuration (12 params)", "FCR SOC Constraint"]),
                     (col2, ["Market Results (DA + FCR + aFRR + mFRR)", "Full P&L Breakdown", "Capital Structure", "Investment KPIs (NPV/IRR/DSCR/LCOS)"]),
                     (col3, ["Loan Amortisation Schedule", "12-Year Cashflow Projection", "SOC & Dispatch Profile", "Sensitivity + Risk Register", "Model Trustworthiness", "Final Recommendation"])]:
        with c:
            for item in items:
                st.markdown(f'<div style="font-size:10px;color:#c4ddf0;padding:4px 0;border-bottom:1px solid #162840">✓ {item}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Generate PDF
    with st.spinner("Generating PDF report…"):
        try:
            pdf_bytes = build_report(
                bat=bat_snap,
                fin_params=fin_snap,
                prices=prices_df,
                schedule=schedule_df,
                reserves=reserves,
                throughput=throughput,
                actual_cycles=actual_cycles,
                fin=fin,
                scenario=scenario_snap,
                markets=markets_snap,
            )
            fname = f"BESS_Report_{bat_snap['cap_mwh']}MWh_{scenario_snap}_{date.today().strftime('%Y%m%d')}.pdf"
            st.download_button(
                label="⬇  DOWNLOAD PDF REPORT",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
            st.success(f"✅ PDF generated: {fname}  ({len(pdf_bytes)/1024:.0f} KB)  |  ~10–12 pages")
        except Exception as e:
            st.error(f"PDF generation error: {e}")
            st.info("If fpdf2 is not installed, run: pip install fpdf2")

    # Also provide CSV export
    st.markdown("---")
    st.markdown(sec_label("Export Raw Data"), unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        csv_sched = schedule_df.to_csv(index=False)
        st.download_button("📥 Schedule CSV", csv_sched,
            f"schedule_{date.today()}.csv", "text/csv", use_container_width=True)
    with c2:
        csv_prices = prices_df.to_csv(index=False)
        st.download_button("📥 Prices CSV", csv_prices,
            f"prices_{date.today()}.csv", "text/csv", use_container_width=True)
    with c3:
        cf_csv = fin["cf_df"].to_csv(index=False)
        st.download_button("📥 Cashflow CSV", cf_csv,
            f"cashflow_{date.today()}.csv", "text/csv", use_container_width=True)


# ─────────────────────────────────────────────────────────────────
# STATUS BAR
# ─────────────────────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="font-size:8px;color:#1d3450;display:flex;gap:24px;flex-wrap:wrap">
  <span>⚡ BESS Terminal v2.4.1 · DE-LU · EPEX SPOT + ENTSO-E</span>
  <span>Cycles: {actual_cycles:.3f}x / {bat_snap['cycles_per_day']}x · Throughput: {throughput:.2f} MWh</span>
  <span>IRR: {fin['irr_equity']:.1f}% · NPV: €{fin['npv_project']/1000:.0f}k · DSCR: {fin['min_dscr']:.2f}x min</span>
  <span style="margin-left:auto">Optimizer: Dynamic Programming · 17 SOC states · SOGL Art.156 / EB GL Art.18</span>
</div>
""", unsafe_allow_html=True)

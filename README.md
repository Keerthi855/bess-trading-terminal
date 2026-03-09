# ⚡ BESS Trading Terminal

> **Battery Energy Storage System Optimizer for European Electricity Markets**  
> Dynamic Programming · EPEX Spot · FCR · aFRR · mFRR · DE-LU · Investor-Grade PDF Reports

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-name.streamlit.app)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🚀 Live Demo

**[Launch App →](https://your-app-name.streamlit.app)**

---

## What It Does

The BESS Trading Terminal computes the **optimal 24-hour dispatch schedule** for a Battery Energy Storage System participating simultaneously in:

| Market | Product | Settlement |
|--------|---------|-----------|
| EPEX Day-Ahead | Hourly energy (MWh) | Energy revenue |
| FCR | Symmetric ±MW (daily) | Capacity payment |
| aFRR | Up/Down MW (hourly) | Capacity + Activation |
| mFRR | Up MW (4h blocks) | Capacity + Activation |

---

## Features

- **⚙️ Dynamic Programming Optimizer** — 17 SOC states, 24h horizon, globally optimal
- **🔄 Cycles/Day Control** — hard throughput constraint enforced in optimizer
- **💰 Full Financial Model** — NPV, IRR, DSCR, LCOS, loan amortisation
- **📄 PDF Report** — 10–12 page investor-grade report (auto-generated)
- **📊 Interactive Charts** — Plotly: prices, dispatch, SOC, P&L, cashflows
- **📥 CSV Export** — schedule, prices, cashflow data
- **5 Market Scenarios** — Normal / High / Low / Volatile / Negative prices
- **🌑 Dark Terminal Theme** — Bloomberg-style interface

---

## Quick Start (Local)

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/bess-trading-terminal.git
cd bess-trading-terminal

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run app.py
# → Opens at http://localhost:8501
```

---

## Project Structure

```
bess-trading-terminal/
├── app.py              ← Streamlit UI (700+ lines)
├── engine.py           ← DP optimizer + financial engine
├── report.py           ← PDF report generator (fpdf2)
├── requirements.txt    ← Pinned dependencies
├── .streamlit/
│   └── config.toml     ← Dark theme + server config
└── README.md
```

---

## Regulatory Framework

| Regulation | Scope |
|-----------|-------|
| SOGL Art. 156 (EU 2017/1485) | FCR symmetric ±MW, SOC window 25–75% |
| EB GL Art. 18 (EU 2017/2195) | aFRR hourly products, capacity + activation |
| EB GL Art. 25 (EU 2017/2195) | mFRR 4h blocks, min 5 MW |
| EPEX Spot Trading Rules v4.2 | DA hourly auction, gate closure 12:00 CET D-1 |
| EnWG §13 (German Energy Act) | TSO grid obligation |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | 1.35.0 | Web UI |
| plotly | 5.22.0 | Interactive charts |
| pandas | 2.2.2 | Data handling |
| numpy | 1.26.4 | Numerical computation |
| fpdf2 | 2.7.9 | PDF report generation |

---

## Deploy to Streamlit Cloud

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect GitHub → Select this repo → `app.py`
4. Click **Deploy**

---

## License

MIT License — see [LICENSE](LICENSE)

---

*Powered by BESS Trading Simulator Engine v2.4.1*  
*Markets: DE-LU Bidding Zone · TSOs: 50Hertz, TenneT, Amprion, TransnetBW*

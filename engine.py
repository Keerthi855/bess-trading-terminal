"""
BESS Trading Simulator — Core Engine
Optimizer: Dynamic Programming (backward induction)
Markets: EPEX DA, FCR, aFRR, mFRR (DE-LU)
"""

import math
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ─────────────────────────────────────────────
# PRICE GENERATOR
# ─────────────────────────────────────────────
DA_SHAPE  = [32,27,24,22,21,26,50,90,118,124,116,106,98,93,98,112,132,150,134,108,82,64,50,38]
FCR_SHAPE = [10.2,10.0,9.8,9.7,9.6,9.9,10.5,11.2,11.8,11.5,11.0,10.7,
             10.5,10.4,10.5,11.0,11.6,12.1,11.9,11.3,10.8,10.4,10.2,10.0]

class SeededRng:
    def __init__(self, seed: int):
        self.s = ((seed * 1664525 + 1013904223) & 0xFFFFFFFF)

    def __call__(self) -> float:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.s / 0xFFFFFFFF


def generate_prices(scenario: str, seed: int) -> pd.DataFrame:
    r = SeededRng(seed * 31 + 7)
    mult  = {"high": 1.45, "low": 0.62, "neg": 0.35}.get(scenario, 1.0)
    vol   = 36 if scenario == "volatile" else (20 if scenario == "neg" else 14)
    neg_floor = -120 if scenario == "neg" else -5

    rows = []
    for h in range(24):
        da    = max(neg_floor, DA_SHAPE[h] * mult + (r() - 0.5) * vol * 2)
        fcr   = max(3.0, FCR_SHAPE[h] + (r() - 0.5) * 1.5)
        afrr_u = max(2.0, 6.5 + (r() - 0.5) * 2.5)
        afrr_d = max(1.0, 4.8 + (r() - 0.5) * 2.0)
        afrr_au = max(30.0, 105 + (r() - 0.5) * 60)
        afrr_ad = max(20.0, 65  + (r() - 0.5) * 40)
        afrr_pu = 0.12 + r() * 0.22
        afrr_pd = 0.10 + r() * 0.18
        mfrr_p  = 0.04 + r() * 0.09
        mfrr_a  = max(40.0, 120 + (r() - 0.5) * 70)
        mfrr_c  = max(1.0, 3.8 + (r() - 0.5) * 1.8)

        rows.append({
            "h": h,
            "time": f"{h:02d}:00",
            "da": round(da, 2),
            "fcr": round(fcr, 3),
            "afrr_u": round(afrr_u, 3),
            "afrr_d": round(afrr_d, 3),
            "afrr_au": round(afrr_au, 2),
            "afrr_ad": round(afrr_ad, 2),
            "afrr_pu": round(afrr_pu, 4),
            "afrr_pd": round(afrr_pd, 4),
            "mfrr_p":  round(mfrr_p, 4),
            "mfrr_a":  round(mfrr_a, 2),
            "mfrr_c":  round(mfrr_c, 3),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# RESERVE PRE-ALLOCATION
# ─────────────────────────────────────────────
def allocate_reserves(pwr_mw: float, markets: dict) -> dict:
    fcr  = 0.0
    afru = 0.0
    afrd = 0.0
    mfrr = 0.0

    if markets.get("fcr") and pwr_mw >= 1.0:
        fcr = min(pwr_mw * 0.48, math.floor(max(1.0, pwr_mw * 0.48) * 10) / 10)

    rem = pwr_mw - fcr
    if markets.get("afrr") and rem >= 1.0:
        afru = min(math.floor(rem * 0.32 * 10) / 10, pwr_mw * 0.22)
        afrd = min(math.floor(rem * 0.24 * 10) / 10, pwr_mw * 0.18)

    rem2 = pwr_mw - fcr - afru - afrd
    if markets.get("mfrr") and pwr_mw >= 5.0 and rem2 >= 1.0:
        mfrr = min(math.floor(rem2 * 0.30 * 10) / 10, pwr_mw * 0.15)

    avail = max(0.0, pwr_mw - fcr - afru - afrd - mfrr)

    return {"fcr": fcr, "afrr_u": afru, "afrr_d": afrd, "mfrr": mfrr, "avail": avail}


# ─────────────────────────────────────────────
# DYNAMIC PROGRAMMING OPTIMIZER
# ─────────────────────────────────────────────
def run_optimizer(
    cap_mwh: float,
    pwr_mw: float,
    min_soc_pct: float,
    max_soc_pct: float,
    eta: float,
    deg_cost: float,
    cycles_per_day: float,
    prices: pd.DataFrame,
    markets: dict,
) -> pd.DataFrame:

    sqe = math.sqrt(eta / 100.0)
    min_e = cap_mwh * min_soc_pct / 100.0
    max_e = cap_mwh * max_soc_pct / 100.0
    e_range = max_e - min_e
    max_throughput = cycles_per_day * cap_mwh * 2.0

    res = allocate_reserves(pwr_mw, markets)
    avail_mw = res["avail"]

    N = 17
    soc_pts = np.linspace(min_e, max_e, N)
    dp  = np.zeros((25, N))
    pol = np.zeros((24, N))

    FRACS = [-1.0, -0.66, -0.33, 0.0, 0.33, 0.66, 1.0]

    # Backward induction
    for h in range(23, -1, -1):
        p_da = prices.loc[h, "da"]
        for si in range(N):
            soc = soc_pts[si]
            max_d = min(avail_mw, (soc - min_e) * sqe)
            max_c = min(avail_mw, (max_e - soc) / sqe)
            best_v, best_a = -1e15, 0.0

            for f in FRACS:
                a_mw = f * max_d if f > 0 else (f * max_c if f < 0 else 0.0)
                if a_mw > 0.001:
                    new_soc = max(min_e, soc - a_mw / sqe)
                elif a_mw < -0.001:
                    new_soc = min(max_e, soc + (-a_mw) * sqe)
                else:
                    new_soc = soc

                nsi = int(round(((new_soc - min_e) / e_range) * (N - 1)))
                nsi = max(0, min(N - 1, nsi))

                rev = a_mw * p_da if markets.get("da") else 0.0
                deg = abs(a_mw) * deg_cost
                v = rev - deg + dp[h + 1, nsi]

                if v > best_v:
                    best_v, best_a = v, a_mw

            dp[h, si] = max(best_v, 0) if best_v < -1e13 else best_v
            pol[h, si] = best_a

    # Forward pass
    soc = cap_mwh * 0.5
    throughput = 0.0
    rows = []

    for h in range(24):
        si = int(round(((soc - min_e) / e_range) * (N - 1)))
        si = max(0, min(N - 1, si))
        act = pol[h, si]

        # Enforce cycle cap
        rem_cap = max(0.0, max_throughput - throughput)
        if abs(act) > rem_cap:
            act = math.copysign(rem_cap, act)

        dch = max(0.0, act)
        chg = max(0.0, -act)
        new_soc = max(min_e, soc - dch / sqe) if dch > 0.001 else (
                  min(max_e, soc + chg * sqe) if chg > 0.001 else soc)
        throughput += dch + chg

        p = prices.loc[h]
        da_rev    = (dch - chg) * p["da"]   if markets.get("da")   else 0.0
        fcr_rev   = res["fcr"]   * p["fcr"] if markets.get("fcr")  else 0.0
        afrr_cap  = (res["afrr_u"] * p["afrr_u"] + res["afrr_d"] * p["afrr_d"]) if markets.get("afrr") else 0.0
        afrr_act  = (res["afrr_u"] * p["afrr_pu"] * p["afrr_au"] * 0.25 +
                     res["afrr_d"] * p["afrr_pd"] * p["afrr_ad"] * 0.25) if markets.get("afrr") else 0.0
        afrr_rev  = afrr_cap + afrr_act
        mfrr_rev  = res["mfrr"] * (p["mfrr_c"] + p["mfrr_p"] * p["mfrr_a"] * 0.20) if markets.get("mfrr") else 0.0
        deg_cost_h = (dch + chg) * deg_cost
        net = da_rev + fcr_rev + afrr_rev + mfrr_rev - deg_cost_h

        rows.append({
            "h": h, "time": f"{h:02d}:00",
            "soc": round(new_soc, 4),
            "soc_pct": round((new_soc / cap_mwh) * 100, 2),
            "dch": round(dch, 4), "chg": round(chg, 4),
            "chg_neg": round(-chg, 4),
            "da_price": round(p["da"], 2),
            "fcr_price": round(p["fcr"], 3),
            "fcr_mw": res["fcr"], "afrr_u_mw": res["afrr_u"],
            "afrr_d_mw": res["afrr_d"], "mfrr_mw": res["mfrr"],
            "da_rev": round(da_rev, 4), "fcr_rev": round(fcr_rev, 4),
            "afrr_rev": round(afrr_rev, 4), "mfrr_rev": round(mfrr_rev, 4),
            "deg_cost": round(-deg_cost_h, 4),
            "net": round(net, 4),
        })
        soc = new_soc

    df = pd.DataFrame(rows)
    df["cum_net"] = df["net"].cumsum().round(4)
    df["cum_cycles"] = ((df["dch"] + df["chg"]).cumsum() / (cap_mwh * 2)).round(5)

    return df, res, throughput


# ─────────────────────────────────────────────
# FINANCIAL MODEL
# ─────────────────────────────────────────────
def _npv(rate: float, cashflows: list) -> float:
    return sum(cf / (1 + rate) ** (t + 1) for t, cf in enumerate(cashflows))


def _irr(cashflows: list) -> float:
    """
    cashflows[0] must be the initial outlay (negative).
    Returns decimal IRR capped at 5.0 (500%).
    Returns 0.0 if no valid IRR found.
    """
    if not cashflows or cashflows[0] >= 0:
        return 0.0
    lo, hi = -0.99, 5.0
    npv_lo = _npv(lo, cashflows)
    npv_hi = _npv(hi, cashflows)
    if npv_lo * npv_hi > 0:
        return 0.0
    for _ in range(400):
        mid = (lo + hi) / 2
        v = _npv(mid, cashflows)
        if abs(v) < 1:
            return mid
        if v > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def annual_debt_service(principal: float, annual_rate: float, term_years: int) -> float:
    if annual_rate == 0 or principal == 0:
        return principal / term_years if term_years > 0 else 0
    r = annual_rate / 12
    n = term_years * 12
    monthly = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return monthly * 12


def compute_lcos(capex, annual_om, annual_deg_pct, annual_mwh, life_years, discount_rate):
    total_cost_pv = capex
    total_mwh_pv  = 0.0
    for y in range(1, life_years + 1):
        df = (1 + discount_rate) ** y
        total_cost_pv += annual_om / df
        total_mwh_pv  += (annual_mwh * (1 - annual_deg_pct) ** (y - 1)) / df
    return total_cost_pv / max(total_mwh_pv, 1)


def compute_financials(
    cap_mwh, pwr_mw,
    capex_per_kwh, equity_pct, loan_rate, loan_term_yrs,
    annual_om_pct, insurance_pct, discount_rate, project_life_yrs,
    annual_deg_pct,
    net_day, throughput_day
):
    total_capex  = capex_per_kwh * cap_mwh * 1000
    equity       = total_capex * equity_pct / 100
    loan_amt     = total_capex - equity
    ann_ds       = annual_debt_service(loan_amt, loan_rate / 100, loan_term_yrs)
    ann_om       = total_capex * annual_om_pct / 100
    ann_ins      = total_capex * insurance_pct / 100
    ann_fixed    = ann_om + ann_ins
    base_ann_rev = net_day * 365
    annual_mwh   = throughput_day * 365

    # Year cashflows
    cfs = []
    for y in range(1, project_life_yrs + 1):
        deg_fac = (1 - annual_deg_pct / 100) ** (y - 1)
        rev     = base_ann_rev * deg_fac
        om      = ann_fixed
        ds      = ann_ds if y <= loan_term_yrs else 0.0
        ebitda  = rev - om
        fcf     = rev - om - ds
        dscr    = ebitda / max(ds, 1.0)
        cfs.append({"year": y, "revenue": rev, "om": om, "ds": ds,
                    "ebitda": ebitda, "fcf": fcf, "dscr": dscr,
                    "deg_factor": round(deg_fac, 4)})
    cf_df = pd.DataFrame(cfs)

    eq_cfs    = [c["fcf"] for c in cfs]
    proj_cfs  = [c["ebitda"] for c in cfs]
    npv_eq    = _npv(discount_rate / 100, eq_cfs) - equity
    npv_proj  = _npv(discount_rate / 100, proj_cfs) - total_capex
    # IRR needs initial outlay as year-0 negative cashflow
    irr_eq    = (_irr([-equity] + eq_cfs) or 0.0) * 100
    irr_proj  = (_irr([-total_capex] + proj_cfs) or 0.0) * 100

    # Payback
    cum = 0.0
    payback = float(project_life_yrs + 1)
    for y, row in enumerate(cfs):
        cum += row["fcf"]
        if cum >= 0:
            payback = y + 1 - (cum - row["fcf"]) / max(row["fcf"], 1)
            break

    lcos_val  = compute_lcos(total_capex, ann_fixed + ann_ds,
                             annual_deg_pct / 100, annual_mwh,
                             project_life_yrs, discount_rate / 100)

    avg_dscr  = cf_df["dscr"].mean()
    min_dscr  = cf_df["dscr"].min()

    # Loan schedule
    loan_rows = []
    bal = loan_amt
    for y in range(1, loan_term_yrs + 1):
        interest  = bal * (loan_rate / 100)
        principal = ann_ds - interest
        new_bal   = max(0.0, bal - principal)
        loan_rows.append({
            "year": y,
            "opening": round(bal, 2),
            "interest": round(interest, 2),
            "principal": round(principal, 2),
            "payment": round(ann_ds, 2),
            "closing": round(new_bal, 2),
        })
        bal = new_bal

    return {
        "total_capex": total_capex, "equity": equity, "loan_amt": loan_amt,
        "ann_ds": ann_ds, "ann_om": ann_om, "ann_ins": ann_ins, "ann_fixed": ann_fixed,
        "base_ann_rev": base_ann_rev, "annual_mwh": annual_mwh,
        "cf_df": cf_df, "loan_df": pd.DataFrame(loan_rows),
        "npv_equity": npv_eq, "npv_project": npv_proj,
        "irr_equity": irr_eq, "irr_project": irr_proj,
        "payback": payback, "lcos": lcos_val,
        "avg_dscr": avg_dscr, "min_dscr": min_dscr,
        "loan_rate": loan_rate, "loan_term_yrs": loan_term_yrs,
        "project_life_yrs": project_life_yrs, "equity_pct": equity_pct,
    }

"""Turn detected patterns into recommendations, each with its evidence and an estimated, annualised saving.

Targets come from the meter's OWN best observed behaviour (e.g. its best 25% of nights), so each
recommendation is achievable by construction, not an arbitrary benchmark.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _annual(hours_in_data: int) -> float:
    return 8760.0 / max(hours_in_data, 1)


def recommend(res: dict, tariff: float, co2: float, demand_charge: float) -> list[dict]:
    recs: list[dict] = []

    def add(**kw):
        kwh = kw.get("kwh_year", 0.0) or 0.0
        kw.setdefault("inr_year", kwh * tariff)
        kw.setdefault("co2_t_year", kwh * co2 / 1000)
        recs.append(kw)

    for meter, r in res["meters"].items():
        y = r["y"]
        ann = _annual(len(y))
        shape = r["shape"]

        # 1) Night baseload vs own best nights
        night = y[(y.index.hour <= 4)]
        nightly = night.resample("D").mean().dropna()
        if len(nightly) > 14:
            target = nightly.quantile(0.25)
            gap = nightly.mean() - target
            gap_pct = gap / nightly.mean() * 100
            if gap_pct > 5:
                add(meter=meter, category="Baseload", priority=gap_pct,
                    title=f"{meter}: cut night-time baseload to the level of your best nights",
                    evidence=[f"Night (00–05h) average load {nightly.mean():,.0f} kW vs {target:,.0f} kW on the best 25% of nights (−{gap_pct:.0f}%).",
                              f"Night load is {shape['night_day_ratio'] * 100:.0f}% of weekday daytime load."],
                    action="Audit equipment left running overnight (HVAC, pumps, lighting, idle IT) and add schedules or auto-off.",
                    kwh_year=gap * 5 * 365, confidence="High" if len(nightly) > 90 else "Medium")

        # 2) Weekend load vs own best weekends
        wk = y[y.index.dayofweek >= 5].resample("D").sum(min_count=20).dropna()
        if len(wk) > 8 and shape["weekend_weekday_ratio"] > 0.6:
            target = wk.quantile(0.25)
            gap = wk.mean() - target
            if gap / wk.mean() > 0.05:
                add(meter=meter, category="Scheduling", priority=gap / wk.mean() * 100,
                    title=f"{meter}: apply a weekend setback schedule",
                    evidence=[f"Weekend daily use is {shape['weekend_weekday_ratio'] * 100:.0f}% of weekday use.",
                              f"Average weekend day {wk.mean():,.0f} kWh vs {target:,.0f} kWh on the best 25% of weekend days."],
                    action="If the facility is mostly unoccupied on weekends, set HVAC and lighting to setback and enable only the occupied zones.",
                    kwh_year=gap * 104, confidence="Medium")

        # 3) Cooling sensitivity from change-point model
        cp = r.get("cp")
        if cp and cp["cool_kwh_per_c_day"] > 0 and cp["r2"] > 0.3 and cp["weather_share"] > 3:
            saved = cp["cool_kwh_per_c_day"] * cp["cooling_days"] * _annual(cp["n_days"] * 24)
            add(meter=meter, category="HVAC / weather", priority=cp["weather_share"],
                title=f"{meter}: raise the cooling setpoint by 1 °C",
                evidence=[f"Change-point model: above {cp['balance_c']:.1f} °C, each extra °C adds {cp['cool_kwh_per_c_day']:,.0f} kWh/day (R²={cp['r2']:.2f}).",
                          f"About {cp['weather_share']:.0f}% of energy is weather-driven; {cp['cooling_days']} cooling days observed."],
                action="Raise the cooling setpoint by 1 °C. The estimate assumes this shifts the balance point up by about 1 °C. Pre-cool before peak hours if needed.",
                kwh_year=saved, confidence="High" if cp["r2"] > 0.6 else "Medium")

        # 4) Anomaly events (measured excess, not modelled)
        ev = r["events"]
        if len(ev):
            pos = ev[ev.excess_kwh > 0]
            for etype, g in pos.groupby("type"):
                kwh = g.excess_kwh.sum()
                starts = pd.to_datetime(g.start)
                common = starts.dt.hour.mode()
                add(meter=meter, category="Anomaly", priority=kwh / y.sum() * 100 * 10,
                    title=f"{meter}: fix the recurring cause of {len(g)} '{etype}' event(s)",
                    evidence=[f"{len(g)} events, {g.hours.sum()} h in total, {kwh:,.0f} kWh above expected (measured).",
                              f"Largest: {g.iloc[0]['why'][:160]}",
                              f"Most common start hour: {int(common.iloc[0]):02d}:00." if len(common) else ""],
                    action="Open the events in the Anomalies tab, check the equipment logs for those windows, and fix the root cause.",
                    kwh_year=kwh * ann, confidence="High" if len(g) >= 3 else "Medium")

        # 5) Weather-normalised drift
        d = r["drift"]
        if len(d) >= 4 and d.tail(2).mean() > 3:
            add(meter=meter, category="Performance drift", priority=d.tail(2).mean(),
                title=f"{meter}: weather-normalised consumption is drifting up",
                evidence=[f"Last 2 months ran {d.tail(2).mean():.1f}% above the model's expectation for the same conditions."],
                action="Check for added equipment, degraded HVAC efficiency or schedule changes in the recent period.",
                kwh_year=None, confidence="Medium")

    # 6) Peak demand (system level)
    pk = res["peaks"]
    total = pk["total"]
    over = (total - pk["threshold"]).clip(lower=0)
    red_kw = pk["peak_kw"] - pk["threshold"]
    hh = pk["peak_hour_hist"]
    top_hours = hh.sort_values(ascending=False).head(3).index.tolist()
    add(meter="All meters", category="Peak demand", priority=pk["par"] * 10,
        title=f"Shave the top {100 - 95}% of hours: cap demand at {pk['threshold']:,.0f} kW",
        evidence=[f"Peak {pk['peak_kw']:,.0f} kW on {pk['peak_time']:%d %b %Y %H:%M}; peak-to-average ratio {pk['par']:.2f}, load factor {pk['load_factor']:.2f}.",
                  f"{pk['hours_above_thr']} hours exceed the 95th percentile, mostly at {', '.join(f'{h:02d}:00' for h in sorted(top_hours))}.",
                  f"Only {over.sum():,.0f} kWh ({over.sum() / total.sum() * 100:.2f}% of energy) must be shifted to cut peak demand by {red_kw:,.0f} kW ({red_kw / pk['peak_kw'] * 100:.0f}%)."],
        action="Stagger large loads (chillers, pumps, EV charging) out of those hours, pre-cool, or use storage. This shifts energy rather than saving it, and cuts demand charges.",
        kwh_year=0.0, inr_year=red_kw * demand_charge * 12, co2_t_year=0.0,
        confidence="High")

    recs.sort(key=lambda r: -(r["inr_year"] or 0))
    for r in recs:
        r["evidence"] = [e for e in r["evidence"] if e]
    return recs

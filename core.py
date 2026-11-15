"""Data model + calculations for the Alustrian Palace demo dashboard (no Streamlit here)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
ANC_COLS = ["fb_revenue", "spa_revenue", "excursions_revenue", "transfers_revenue"]
ANC_LABELS = {"fb_revenue": "F&B", "spa_revenue": "Spa", "excursions_revenue": "Excursions",
              "transfers_revenue": "Transfers"}
COST_COLS = ["payroll", "electricity", "water_gas", "commissions", "fb_cost", "maintenance", "other_opex"]
COST_LABELS = {"payroll": "Payroll", "electricity": "Electricity", "water_gas": "Water & gas",
               "commissions": "Commissions", "fb_cost": "F&B cost of sales", "maintenance": "Maintenance",
               "other_opex": "Other operating"}
OTA = ["Booking.com", "Expedia", "Airbnb"]
SEASONS = ["High season", "Shoulder", "Low / hurricane"]
DOWS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ROOM_TYPES = ["Garden View", "Ocean View", "Suite", "Villa"]
CHANNELS = ["Direct website", "Booking.com", "Expedia", "Airbnb", "Travel agents/wholesalers", "Walk-in"]
SEGMENTS = ["Couples & honeymoon", "Families", "Groups & weddings", "Corporate"]
MARKETS = ["US", "Canada", "UK", "Europe", "Caribbean"]


def season_of(dates: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    m = pd.DatetimeIndex(dates).month
    return np.where(np.isin(m, [12, 1, 2, 3, 4]), "High season",
                    np.where(np.isin(m, [8, 9, 10]), "Low / hurricane", "Shoulder"))


# ------------------------------------------------------------------ loading
def load_all(data_dir: Path = DATA_DIR) -> dict:
    meta = json.loads((data_dir / "meta.json").read_text())
    n = pd.read_csv(data_dir / "stay_nights.csv", parse_dates=["stay_date", "booking_date"])
    n["season"] = season_of(n["stay_date"])
    n["dow"] = n["stay_date"].dt.day_of_week.map(dict(enumerate(DOWS)))
    n["ancillary_revenue"] = n[ANC_COLS].sum(axis=1)
    res = pd.read_csv(data_dir / "reservations.csv",
                      parse_dates=["booking_date", "arrival_date", "departure_date", "cancel_date"])
    res["season"] = season_of(res["arrival_date"])
    res["dow"] = res["arrival_date"].dt.day_of_week.map(dict(enumerate(DOWS)))
    costs = pd.read_csv(data_dir / "costs_daily.csv", parse_dates=["date"])
    budget = pd.read_csv(data_dir / "budget_monthly.csv", parse_dates=["month"])
    # expand monthly budget to days so any date range can be prorated
    rows = []
    for b in budget.itertuples():
        dd = pd.date_range(b.month, b.month + pd.offsets.MonthEnd(0))
        k = len(dd)
        rows.append(pd.DataFrame({"date": dd, "property": b.property, "b_rn": b.budget_room_nights / k,
                                  "b_room_rev": b.budget_room_revenue / k, "b_anc": b.budget_ancillary_revenue / k,
                                  "b_total": b.budget_total_revenue / k, "b_gop": b.budget_gop / k}))
    budget_daily = pd.concat(rows, ignore_index=True)
    comp = pd.read_csv(data_dir / "compset_daily.csv", parse_dates=["date"])
    reviews = pd.read_csv(data_dir / "reviews.csv", parse_dates=["review_date"])
    topics = pd.read_csv(data_dir / "review_topics.csv").merge(
        reviews[["review_id", "review_date", "property", "platform"]], on="review_id")
    inv = pd.read_csv(data_dir / "inventory.csv")
    raw = {p.stem: pd.read_csv(p, dtype=str, keep_default_na=False) for p in sorted((data_dir / "raw_samples").glob("*.csv"))}
    return dict(meta=meta, as_of=pd.Timestamp(meta["as_of"]), start=pd.Timestamp(meta["data_start"]),
                nights=n, res=res, costs=costs, budget=budget, budget_daily=budget_daily, comp=comp,
                reviews=reviews, topics=topics, inv=inv, raw=raw)


# ------------------------------------------------------------------ filters
@dataclass
class Filters:
    properties: list
    start: pd.Timestamp
    end: pd.Timestamp
    room_types: list = field(default_factory=list)
    channels: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    markets: list = field(default_factory=list)
    seasons: list = field(default_factory=list)
    dows: list = field(default_factory=list)

    @property
    def has_dims(self) -> bool:
        return bool(self.room_types or self.channels or self.segments or self.markets)

    def shifted(self, years: int = 1) -> "Filters":
        off = pd.DateOffset(years=years)
        return Filters(self.properties, self.start - off, self.end - off, self.room_types, self.channels,
                       self.segments, self.markets, self.seasons, self.dows)

    def with_dates(self, start, end) -> "Filters":
        return Filters(self.properties, pd.Timestamp(start), pd.Timestamp(end), self.room_types, self.channels,
                       self.segments, self.markets, self.seasons, self.dows)


def calendar(f: Filters) -> pd.DataFrame:
    d = pd.DataFrame({"date": pd.date_range(f.start, f.end, freq="D")})
    d["season"] = season_of(d["date"])
    d["dow"] = d["date"].dt.day_of_week.map(dict(enumerate(DOWS)))
    if f.seasons:
        d = d[d["season"].isin(f.seasons)]
    if f.dows:
        d = d[d["dow"].isin(f.dows)]
    return d


def rooms(data, f: Filters, by_type: bool = True) -> int:
    inv = data["inv"][data["inv"]["property"].isin(f.properties)]
    if by_type and f.room_types:
        inv = inv[inv["room_type"].isin(f.room_types)]
    return int(inv["rooms"].sum())


def nights(data, f: Filters, dims: bool = True, actual_only: bool = True) -> pd.DataFrame:
    n = data["nights"]
    m = n["property"].isin(f.properties) & n["stay_date"].between(f.start, f.end)
    if actual_only:
        m &= n["stay_date"] <= data["as_of"]
    if f.seasons:
        m &= n["season"].isin(f.seasons)
    if f.dows:
        m &= n["dow"].isin(f.dows)
    if dims:
        for col, vals in (("room_type", f.room_types), ("channel", f.channels), ("segment", f.segments),
                          ("source_market", f.markets)):
            if vals:
                m &= n[col].isin(vals)
    return n[m]


def _cal_filter(df, f, col):
    m = df["property"].isin(f.properties) & df[col].between(f.start, f.end)
    if f.seasons:
        m &= np.isin(season_of(df[col]), f.seasons)
    if f.dows:
        m &= df[col].dt.day_of_week.map(dict(enumerate(DOWS))).isin(f.dows)
    return df[m]


def costs(data, f):
    return _cal_filter(data["costs"], f, "date")


def covered(data, f: Filters) -> bool:
    """True if the whole range has actual data (used to blank out comparisons with no history)."""
    return f.start >= data["start"] and f.end <= data["as_of"]


# ------------------------------------------------------------------ KPIs
def kpis(data, f: Filters) -> dict | None:
    if not covered(data, f):
        return None
    cal = calendar(f)
    days = len(cal)
    if days == 0:
        return None
    n = nights(data, f)
    n_all = nights(data, f, dims=False)
    avail = rooms(data, f) * days
    avail_all = rooms(data, f, by_type=False) * days
    rn = len(n)
    room_rev = n["room_revenue"].sum()
    anc = n["ancillary_revenue"].sum()
    total_all = n_all["room_revenue"].sum() + n_all["ancillary_revenue"].sum()
    c = costs(data, f)
    cost = c[COST_COLS].sum().sum()
    gop = total_all - cost
    return dict(days=days, avail=avail, avail_all=avail_all, rn=rn, room_rev=room_rev, anc=anc,
                total=room_rev + anc, occ=rn / avail if avail else np.nan, adr=room_rev / rn if rn else np.nan,
                revpar=room_rev / avail if avail else np.nan, total_all=total_all, cost=cost, gop=gop,
                goppar=gop / avail_all if avail_all else np.nan,
                gop_margin=gop / total_all if total_all else np.nan,
                commission=n["commission"].sum(), orn_all=len(n_all),
                cpor=(cost / len(n_all)) if len(n_all) else np.nan)


def budget_kpis(data, f: Filters) -> dict | None:
    if f.has_dims:
        return None
    b = _cal_filter(data["budget_daily"], f, "date")
    days = len(calendar(f))
    if b.empty or days == 0:
        return None
    avail = rooms(data, f, by_type=False) * days
    rn, rr, tot, gop = b["b_rn"].sum(), b["b_room_rev"].sum(), b["b_total"].sum(), b["b_gop"].sum()
    return dict(occ=rn / avail, adr=rr / rn, revpar=rr / avail, total=tot, goppar=gop / avail, gop=gop,
                room_rev=rr, anc=b["b_anc"].sum(), gop_margin=gop / tot)


def freq_for(f: Filters) -> str:
    days = (f.end - f.start).days + 1
    return "D" if days <= 45 else ("W-SUN" if days <= 200 else "MS")


def period_table(data, f: Filters, freq: str | None = None) -> pd.DataFrame:
    """KPIs per period (day / week / month) for the filtered selection."""
    freq = freq or freq_for(f)
    end = min(f.end, data["as_of"])
    f2 = f.with_dates(f.start, end)
    cal = calendar(f2)
    if cal.empty:
        return pd.DataFrame()
    key = lambda s: s.dt.to_period(freq.split("-")[0] if freq != "MS" else "M").dt.start_time
    cal["p"] = key(cal["date"])
    t = cal.groupby("p").size().rename("days").to_frame()
    t["avail"] = t["days"] * rooms(data, f2)
    t["avail_all"] = t["days"] * rooms(data, f2, by_type=False)
    n = nights(data, f2)
    g = n.groupby(key(n["stay_date"]))
    t["rn"] = g.size()
    t["room_rev"] = g["room_revenue"].sum()
    t["anc"] = g["ancillary_revenue"].sum()
    t["commission"] = g["commission"].sum()
    na = nights(data, f2, dims=False)
    ga = na.groupby(key(na["stay_date"]))
    t["total_all"] = ga["room_revenue"].sum() + ga["ancillary_revenue"].sum()
    t["orn_all"] = ga.size()
    c = costs(data, f2)
    gc = c.groupby(key(c["date"]))
    for col in COST_COLS:
        t[col] = gc[col].sum()
    t["electricity_kwh"] = gc["electricity_kwh"].sum()
    t = t.fillna(0)
    t["total"] = t["room_rev"] + t["anc"]
    t["occ"] = t["rn"] / t["avail"]
    t["adr"] = t["room_rev"] / t["rn"].replace(0, np.nan)
    t["revpar"] = t["room_rev"] / t["avail"]
    t["cost"] = t[COST_COLS].sum(axis=1)
    t["gop"] = t["total_all"] - t["cost"]
    t["goppar"] = t["gop"] / t["avail_all"]
    t["gop_margin"] = t["gop"] / t["total_all"].replace(0, np.nan)
    t["cpor"] = t["cost"] / t["orn_all"].replace(0, np.nan)
    return t


def budget_period(data, f: Filters, freq: str) -> pd.DataFrame:
    b = _cal_filter(data["budget_daily"], f.with_dates(f.start, min(f.end, data["as_of"])), "date")
    if b.empty:
        return pd.DataFrame()
    key = b["date"].dt.to_period("M" if freq == "MS" else freq.split("-")[0]).dt.start_time
    t = b.groupby(key)[["b_rn", "b_room_rev", "b_anc", "b_total", "b_gop"]].sum()
    days = b.groupby(key)["date"].nunique()
    avail = days * rooms(data, f, by_type=False)
    t["occ"] = t["b_rn"] / avail
    t["adr"] = t["b_room_rev"] / t["b_rn"]
    t["revpar"] = t["b_room_rev"] / avail
    t["total"] = t["b_total"]
    t["goppar"] = t["b_gop"] / avail
    return t


# ------------------------------------------------------------------ pricing
def whatif(base_occ: float, base_adr: float, rate_change: float, elasticity: float, cap: float = 0.98) -> dict:
    """Constant-elasticity assumption: % change in room nights = elasticity x % change in rate."""
    occ = float(np.clip(base_occ * (1 + elasticity * rate_change), 0, cap))
    adr = base_adr * (1 + rate_change)
    return dict(occ=occ, adr=adr, revpar=occ * adr, base_revpar=base_occ * base_adr)


def pace(data, f: Filters, months: int = 4) -> pd.DataFrame:
    """Room nights on the books now vs same time last year, by stay month (property + room-type filters)."""
    as_of = data["as_of"]
    n = data["nights"]
    m = n["property"].isin(f.properties)
    if f.room_types:
        m &= n["room_type"].isin(f.room_types)
    n = n[m]
    out = []
    start = as_of + pd.Timedelta(days=1)
    for k in range(months):
        ms = (start + pd.offsets.MonthBegin(k)) if k else start
        me = (ms + pd.offsets.MonthEnd(0))
        ly_s, ly_e, ly_asof = ms - pd.DateOffset(years=1), me - pd.DateOffset(years=1), as_of - pd.DateOffset(years=1)
        now = n[n["stay_date"].between(ms, me)]
        ly = n[n["stay_date"].between(ly_s, ly_e)]
        out.append(dict(month=ms.strftime("%b %Y") + (" (from %d)" % ms.day if ms.day > 1 else ""),
                        otb=len(now), otb_rev=now["room_revenue"].sum(),
                        ly_otb=int((ly["booking_date"] <= ly_asof).sum()), ly_final=len(ly)))
    return pd.DataFrame(out)


def forecast(data, f: Filters, horizon: int = 90) -> pd.DataFrame:
    """90-day occupancy forecast: blend of (a) seasonal baseline from the last two years, trend-adjusted, and
    (b) pick-up method = rooms on the books today + the pick-up seen at the same lead time last year."""
    as_of = data["as_of"]
    cap = rooms(data, f)
    n = data["nights"]
    m = n["property"].isin(f.properties)
    if f.room_types:
        m &= n["room_type"].isin(f.room_types)
    n = n[m]
    occ = (n.groupby("stay_date").size().reindex(pd.date_range(data["start"], n["stay_date"].max()), fill_value=0) / cap)
    hist = occ[occ.index <= as_of]
    smooth = hist.rolling(15, center=True, min_periods=5).mean()

    def seasonal(d):
        vals, w = [], []
        for yrs, wt in ((1, 0.6), (2, 0.4)):
            dd = d - pd.DateOffset(years=yrs)
            if dd in smooth.index and not np.isnan(smooth.get(dd, np.nan)):
                vals.append(smooth[dd]); w.append(wt)
        return np.average(vals, weights=w) if vals else np.nan

    last90 = hist.index[-90:]
    trend = np.nanmean([hist[d] - seasonal(d) for d in last90])
    resid = np.array([hist[d] - seasonal(d) for d in hist.index[-365:]])
    sigma = np.nanstd(resid)
    fut = pd.date_range(as_of + pd.Timedelta(days=1), periods=horizon)
    rows = []
    for i, d in enumerate(fut, start=1):
        otb = occ.get(d, 0.0)
        ly = d - pd.DateOffset(years=1)
        ly_n = n[n["stay_date"] == ly]
        ly_final = len(ly_n) / cap
        ly_otb = (ly_n["booking_date"] <= as_of - pd.DateOffset(years=1)).sum() / cap
        pickup = otb + max(ly_final - ly_otb, 0)
        base = seasonal(d) + 0.5 * trend
        fc = float(np.clip(0.5 * base + 0.5 * pickup if not np.isnan(base) else pickup, otb, max(otb, 0.97)))
        s = sigma * (0.45 + 0.55 * min(i / horizon, 1)) * (1 - otb) / max(1 - fc + 0.15, 0.3)
        rows.append(dict(date=d, otb=otb, forecast=fc, lo=max(otb, fc - 1.28 * s), hi=min(1.0, fc + 1.28 * s),
                         ly_actual=ly_final))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ insights
def fmt_money(x, dec=None) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    a = abs(x)
    sign = "-" if x < 0 else ""
    if a >= 1e6:
        return f"{sign}${a / 1e6:.{2 if dec is None else dec}f}M"
    if a >= 1e4:
        return f"{sign}${a / 1e3:.{0 if dec is None else dec}f}K"
    return f"{sign}${a:,.0f}"


def channel_mix(n: pd.DataFrame) -> pd.DataFrame:
    g = n.groupby("channel").agg(rn=("room_revenue", "size"), revenue=("room_revenue", "sum"),
                                 commission=("commission", "sum"))
    g = g.reindex([c for c in CHANNELS if c in g.index])
    g["adr"] = g["revenue"] / g["rn"]
    g["net_adr"] = (g["revenue"] - g["commission"]) / g["rn"]
    g["share_rn"] = g["rn"] / g["rn"].sum()
    g["share_rev"] = g["revenue"] / g["revenue"].sum()
    return g


DIRECT_COST = 0.07   # booking engine + card fees + direct marketing
STORM = dict(start=pd.Timestamp("2025-09-13"), end=pd.Timestamp("2025-09-17"), month=pd.Timestamp("2025-09-01"),
             label="Storm closure 13–17 Sep 2025")


def commission_savings(n: pd.DataFrame, shift: float, direct_cost: float = DIRECT_COST) -> dict:
    ota = n[n["channel"].isin(OTA + ["Travel agents/wholesalers"])]
    if ota.empty:
        return dict(saving=0.0, nights=0, ota_rate=0.0)
    rate = ota["commission"].sum() / ota["room_revenue"].sum()
    moved_rev = ota["room_revenue"].sum() * shift
    return dict(saving=moved_rev * (rate - direct_cost), nights=len(ota) * shift, ota_rate=rate,
                moved_rev=moved_rev)


def insights(data, f: Filters, k: dict, ly: dict | None, bud: dict | None) -> list[str]:
    out = []
    if ly:
        d_rp = k["revpar"] / ly["revpar"] - 1
        d_occ = (k["occ"] - ly["occ"]) * 100
        d_adr = k["adr"] / ly["adr"] - 1
        driver = "rate (ADR)" if abs(d_adr) * 100 > abs(d_occ) else "occupancy"
        out.append(f"RevPAR is **{'up' if d_rp >= 0 else 'down'} {abs(d_rp):.1%}** on last year, driven mainly by "
                   f"**{driver}**: ADR {d_adr:+.1%}, occupancy {d_occ:+.1f} pts.")
    n = nights(data, f)
    if not n.empty:
        mix = channel_mix(n)
        direct = mix["share_rn"].get("Direct website", 0)
        msg = f"Direct website bookings are **{direct:.0%}** of room nights"
        if ly:
            nly = nights(data, f.shifted())
            if not nly.empty:
                dly = channel_mix(nly)["share_rn"].get("Direct website", 0)
                msg += f", **{(direct - dly) * 100:+.1f} pts** vs last year"
        out.append(msg + ".")
        cs = commission_savings(n, 0.10)
        if cs["nights"] > 0:
            out.append(f"Moving **10% of OTA & wholesale nights** ({cs['nights']:,.0f} room nights) to direct would save "
                       f"about **{fmt_money(cs['saving'])}** in commissions over this period "
                       f"(avg. {cs['ota_rate']:.1%} commission vs ~{DIRECT_COST:.0%} direct booking cost).")
        rt = n.groupby("room_type")["room_revenue"].sum()
        if len(rt) > 1:
            av = data["inv"][data["inv"]["property"].isin(f.properties)].groupby("room_type")["rooms"].sum() * k["days"]
            rp = (rt / av).dropna().sort_values()
            out.append(f"**{rp.index[-1]}** earns the highest RevPAR ({fmt_money(rp.iloc[-1])}/night) and "
                       f"**{rp.index[0]}** the lowest ({fmt_money(rp.iloc[0])}) – a pricing & upsell opportunity.")
    if bud:
        v = k["total"] / bud["total"] - 1
        out.append(f"Total revenue is **{abs(v):.1%} {'ahead of' if v >= 0 else 'behind'} budget** "
                   f"({fmt_money(k['total'] - bud['total'])}); GOP margin {k['gop_margin']:.1%} vs budget "
                   f"{bud['gop_margin']:.1%}.")
    c = costs(data, f)
    if not c.empty and k["total_all"]:
        e = c["electricity"].sum() / k["total_all"]
        out.append(f"Electricity is **{e:.1%} of revenue** (**{fmt_money(c['electricity'].sum() / max(k['orn_all'], 1))} "
                   f"per occupied room**) – a solar or energy audit may pay back quickly; worth testing.")
    return out


def reservations(data, f: Filters, statuses=("Checked out", "Cancelled", "No-show")) -> pd.DataFrame:
    r = data["res"]
    m = r["property"].isin(f.properties) & r["arrival_date"].between(f.start, f.end) & r["status"].isin(statuses)
    m &= r["arrival_date"] <= data["as_of"]
    if f.seasons:
        m &= r["season"].isin(f.seasons)
    if f.dows:
        m &= r["dow"].isin(f.dows)
    for col, vals in (("room_type", f.room_types), ("channel", f.channels), ("segment", f.segments),
                      ("source_market", f.markets)):
        if vals:
            m &= r[col].isin(vals)
    return r[m]


def compset_index(data, f: Filters, freq="MS") -> pd.DataFrame:
    """Indicative comp-set ADR index (ours / comp set x 100), whole-hotel basis."""
    f2 = f.with_dates(f.start, min(f.end, data["as_of"]))
    n = nights(data, f2, dims=False)
    c = _cal_filter(data["comp"], f2, "date").merge(
        data["inv"].groupby("property")["rooms"].sum().rename("w"), left_on="property", right_index=True)
    per = "M" if freq == "MS" else freq.split("-")[0]
    ours = n.groupby(n["stay_date"].dt.to_period(per).dt.start_time)["room_revenue"].agg(["sum", "size"])
    c["wadr"] = c["compset_adr"] * c["w"]
    comp = c.groupby(c["date"].dt.to_period(per).dt.start_time)[["wadr", "w"]].sum()
    t = pd.DataFrame({"our_adr": ours["sum"] / ours["size"], "comp_adr": comp["wadr"] / comp["w"]}).dropna()
    t["index"] = t["our_adr"] / t["comp_adr"] * 100
    return t


def recommendations(data, f: Filters, k: dict, ly: dict | None) -> list[str]:
    """Up to 3 plain-English recommended actions, chosen by simple rules on the data."""
    recs = []
    n = nights(data, f)
    if n.empty:
        return recs
    mix = channel_mix(n)
    ota_share = mix["share_rn"].reindex(OTA + ["Travel agents/wholesalers"]).fillna(0).sum()
    cs = commission_savings(n, 0.10)
    per_month = cs["saving"] * 30.4 / max(k["days"], 1)
    if ota_share > 0.35:
        recs.append(f"**Grow direct bookings:** {ota_share:.0%} of nights come via OTAs & wholesalers. A book-direct perk "
                    f"(e.g. free transfer or breakfast) that moves 10% of them is worth ~{fmt_money(per_month)} a month.")
    ci = compset_index(data, f)
    if len(ci):
        idx = ci["our_adr"].mean() / ci["comp_adr"].mean() * 100
        if idx < 100:
            recs.append(f"**Test a rate increase:** ADR is running at {idx:.0f}% of the comp set. Trial +3–5% on Fri–Sat "
                        f"and festive dates and track pick-up weekly.")
    pc = pace(data, f, 3)
    if len(pc):
        gap = (pc["otb"] - pc["ly_otb"]) / pc["ly_otb"].replace(0, np.nan)
        worst = gap.idxmin()
        if gap[worst] < -0.05:
            recs.append(f"**Fill {pc.loc[worst, 'month']}:** on-the-books nights are {abs(gap[worst]):.0%} behind last year; "
                        f"launch a targeted offer to past guests now (pace as of {data['as_of']:%d %b %Y}).")
        else:
            best = gap.idxmax()
            recs.append(f"**Protect rate in {pc.loc[best, 'month']}:** bookings are {gap[best]:.0%} ahead of last year – "
                        f"close discounted rate plans and raise BAR on peak nights (pace as of {data['as_of']:%d %b %Y}).")
    c = costs(data, f)
    if not c.empty and k["total_all"]:
        e = c["electricity"].sum() / k["total_all"]
        recs.append(f"**Get an energy audit / solar quote:** electricity is {e:.1%} of revenue "
                    f"({fmt_money(c['electricity'].sum() / max(k['orn_all'], 1))} per occupied room).")
    return recs[:3]


def data_quality(raw: dict) -> dict:
    """Data-quality issues found & fixed in the raw sample files (computed, not hard-coded)."""
    import re
    pms = raw["pms_export_sample"]
    bdc = raw["ota_bookingcom_sample"]
    bud = raw["budget_spreadsheet_sample"]
    blank = (pms.apply(lambda r: "".join(r.astype(str)).strip() == "", axis=1))
    pms_nb = pms[~blank]
    dups = int(pms_nb.duplicated().sum())
    date_fmts = set()
    for v in pms_nb["Arr Date"]:
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v):
            date_fmts.add("MM/DD/YYYY")
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            date_fmts.add("ISO")
        elif re.fullmatch(r"\d{2} \w{3} \d{2}", v):
            date_fmts.add("DD Mon YY")
    text_nums = int(pms_nb["Nts"].str.contains(r"[a-z]", regex=True).sum()
                    + pms_nb["Rate"].str.contains(r"\$", regex=True).sum()
                    + bdc["Price"].str.startswith("USD").sum()
                    + bud.iloc[:, 1:].apply(lambda c: c.str.contains(r"%|k$|,", regex=True)).sum().sum())
    missing = int((pms_nb["Rate"] == "").sum() + (bdc["Commission amount"] == "").sum())
    return dict(
        sources=3, rows_in=len(pms) + len(bdc) + len(bud), duplicates=dups, blank_rows=int(blank.sum()),
        missing=missing, date_formats=len(date_fmts) + 1,   # + Booking.com long-form dates
        room_codes=pms_nb["Rm Type"].str.strip().nunique(), channel_codes=pms_nb["Src"].nunique(),
        text_numbers=text_nums, hours_saved=12)              # hours: illustrative estimate

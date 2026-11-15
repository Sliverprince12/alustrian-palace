"""Alustrian Palace — boutique hotel performance dashboard (DEMO, fictional property & data).

Run locally:  streamlit run app.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import core
import report
import ui
from ui import CORAL, GOLD, MUTED, NAVY, SAND, SEA, SLATE, TEAL

st.set_page_config(page_title="Alustrian Palace · Performance Dashboard", page_icon="🌴", layout="wide",
                   initial_sidebar_state="auto")
st.markdown(ui.CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading demo data…")
def get_data():
    return core.load_all()


D = get_data()
AS_OF, DATA_START = D["as_of"], D["start"]
money = core.fmt_money

PAGES = {"overview": "Executive overview", "pricing": "Pricing & revenue", "season": "Seasonality & forecast",
         "channels": "Channels & guests", "costs": "Costs & profitability", "reputation": "Reputation & operations",
         "built": "How it's built"}
PAGE_ICONS = {"overview": "◆", "pricing": "◆", "season": "◆", "channels": "◆", "costs": "◆", "reputation": "◆",
              "built": "✧"}

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### Dashboard")
    keys = list(PAGES)
    qp = st.query_params.get("page", "overview")
    page = st.radio("View", keys, index=keys.index(qp) if qp in keys else 0, format_func=PAGES.get,
                    key="page", label_visibility="collapsed")
    if st.query_params.get("page") != page:
        st.query_params["page"] = page

    st.markdown("### Filters")
    prop_opt = st.selectbox("Property", ["Alustrian Palace", "Alustrian Villas", "Portfolio (both properties)"],
                            key="property",
                            help="Alustrian Villas is a fictional sister villa property, included to show multi-property roll-ups.")
    props = ["Alustrian Palace", "Alustrian Villas"] if prop_opt.startswith("Portfolio") else [prop_opt]

    preset = st.selectbox("Date range", ["Last 12 months", "YTD", "MTD", "Custom"], key="preset")
    if preset == "Last 12 months":
        start, end = AS_OF - pd.DateOffset(years=1) + pd.Timedelta(days=1), AS_OF
    elif preset == "YTD":
        start, end = pd.Timestamp(AS_OF.year, 1, 1), AS_OF
    elif preset == "MTD":
        start, end = AS_OF.replace(day=1), AS_OF
    else:
        rng_in = st.date_input("Custom range", value=((AS_OF - pd.Timedelta(days=89)).date(), AS_OF.date()),
                               min_value=DATA_START.date(), max_value=AS_OF.date(), key="custom")
        if isinstance(rng_in, (tuple, list)) and len(rng_in) == 2:
            start, end = pd.Timestamp(rng_in[0]), pd.Timestamp(rng_in[1])
        else:
            start = end = pd.Timestamp(rng_in[0] if isinstance(rng_in, (tuple, list)) else rng_in)
    st.caption(f"{start:%d %b %Y} → {end:%d %b %Y}")
    compare = st.radio("Compare against", ["Last year", "Budget"], horizontal=True, key="compare")
    st.caption("ⓘ **Revenue basis: net.** Room revenue is shown net of government accommodation tax and hotel "
               "service charge (both collected for pass-through, not hotel income).")

    with st.expander("Refine: rooms, channels, guests, season", expanded=False):
        room_types = st.multiselect("Room type", [r for r in core.ROOM_TYPES
                                                  if r in set(D["inv"][D["inv"].property.isin(props)].room_type)],
                                    placeholder="All room types", key="room_types")
        channels = st.multiselect("Channel", core.CHANNELS, placeholder="All channels", key="channels")
        segments = st.multiselect("Guest segment", core.SEGMENTS, placeholder="All segments", key="segments")
        markets = st.multiselect("Source market", core.MARKETS, placeholder="All markets", key="markets")
        seasons = st.multiselect("Season", core.SEASONS, placeholder="All seasons", key="seasons",
                                 help="High Dec–Apr · Shoulder May–Jul & Nov · Low / hurricane Aug–Oct")
        dows = st.multiselect("Day of week", core.DOWS, placeholder="All days", key="dows")

F = core.Filters(props, start, end, room_types, channels, segments, markets, seasons, dows)
LOCATION = (D["meta"]["properties"][props[0]]["location"].split(" (")[0] if len(props) == 1
            else "Turks & Caicos + Barbados portfolio")

st.markdown(ui.header(LOCATION, AS_OF), unsafe_allow_html=True)

K = core.kpis(D, F)
if K is None or K["rn"] == 0 and page not in ("built", "reputation"):
    st.warning("No stays match these filters — widen the date range or clear some filters.")
    st.markdown(ui.footer(), unsafe_allow_html=True)
    st.stop()
LY = core.kpis(D, F.shifted()) if core.covered(D, F.shifted()) else None
BUD = core.budget_kpis(D, F)
FREQ = core.freq_for(F)
PT = core.period_table(D, F, FREQ)
CMP_LABEL = "vs LY" if compare == "Last year" else "vs budget"


def note_dims():
    if F.has_dims:
        st.caption("ⓘ Room-type / channel / segment / market filters apply to room & ancillary figures. Costs, GOP and "
                   "budget are held at property level, so budget comparisons are hidden while these filters are on.")


def card(label, key, value, kind="pct", good_up=True, spark=None, ref_ly=None, ref_bud=None):
    ly_v = ref_ly if ref_ly is not None else (LY or {}).get(key)
    bud_v = ref_bud if ref_bud is not None else (BUD or {}).get(key)
    has_budget = ref_bud is not None or key in ("occ", "adr", "revpar", "total", "goppar", "gop", "gop_margin")
    dl = ui.delta_html(K.get(key) if key in K else value, ly_v, kind, "vs LY", good_up)
    db = ui.delta_html(K.get(key) if key in K else value, bud_v, kind, "vs budget", good_up)
    deltas = ([dl, db] if compare == "Last year" else [db, dl]) if has_budget else [dl]
    sp = ui.sparkline(spark, TEAL if good_up else CORAL) if spark is not None else ""
    return dict(label=label, value=value, deltas=deltas, spark=sp)


def plain_card(label, value, sub="", spark=None, color=TEAL):
    return dict(label=label, value=value, deltas=[f'<span class="flat">{sub}</span>'] if sub else [],
                spark=ui.sparkline(spark, color) if spark is not None else "")


def chart(fig, title, sub="", height=None):
    with st.container(border=True):
        st.markdown(ui.chart_title(title, sub), unsafe_allow_html=True)
        if height:
            fig.update_layout(height=height)
        st.plotly_chart(fig, width="stretch", config=ui.PLOTLY_CONFIG, theme=None)


def pct_axis(fig, secondary=None, **kw):
    if secondary is None:
        fig.update_yaxes(tickformat=".0%", **kw)
    else:
        fig.update_yaxes(tickformat=".0%", secondary_y=secondary, **kw)


def nice_money_axis(fig, vmax, secondary=True, prefix="$"):
    """Round-number $ ticks for a secondary axis (avoids odd auto ticks like $147, $293)."""
    if vmax is None or np.isnan(vmax) or vmax <= 0:
        return
    raw = vmax * 1.15 / 4
    mag = 10 ** np.floor(np.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=raw)
    fig.update_yaxes(range=[0, step * 4.4], dtick=step, tickprefix=prefix, tickformat=",.0f",
                     secondary_y=secondary, showgrid=False)


PARTIAL_LEGEND = "Part-month (incomplete)"


def partial_mask(idx) -> np.ndarray:
    """True for periods that are only partly inside the selected range (first/last month or week)."""
    if FREQ == "D" or len(idx) == 0:
        return np.zeros(len(idx), bool)
    end_eff = min(F.end, AS_OF)
    span = (lambda p: p + pd.offsets.MonthEnd(0)) if FREQ == "MS" else (lambda p: p + pd.Timedelta(days=6))
    return np.array([(p < F.start) or (span(p) > end_eff) for p in idx])


def bar_marker(color, mask):
    """Solid bars for full periods; faded + hatched bars for part-periods."""
    return dict(color=color, opacity=[0.38 if m else 1.0 for m in mask],
                pattern=dict(shape=["/" if m else "" for m in mask], fgcolor="#FFFFFF", size=6, solidity=0.35))


def add_bars(fig, x, y, name, color, mask, **kw):
    """Bar trace with part-period styling; the legend shows a clean solid swatch."""
    fig.add_bar(x=x, y=y, name=name, marker=bar_marker(color, mask), legendgroup=name, showlegend=False, **kw)
    swatch = color[0] if isinstance(color, list) else color
    fig.add_bar(x=[None], y=[None], name=name, marker_color=swatch, legendgroup=name, **kw)


def add_partial_legend(fig, mask, **kw):
    if mask.any():
        fig.add_bar(x=[None], y=[None], name=PARTIAL_LEGEND, marker=dict(color="#B9C1CB",
                    pattern=dict(shape="/", fgcolor="#FFFFFF", solidity=0.35)), **kw)


def partial_note(mask):
    return " · hatched = part-period (incomplete)" if mask.any() else ""


def add_storm(fig, x_values, daily=False):
    """Annotate the fictional Sep 2025 storm closure if it falls inside the chart's x range."""
    if "Alustrian Palace" not in props or len(x_values) == 0:
        return
    sm = core.STORM
    lo, hi = pd.Timestamp(min(x_values)), pd.Timestamp(max(x_values))
    if daily:
        if hi < sm["start"] or lo > sm["end"]:
            return
        fig.add_shape(type="rect", xref="x", yref="paper", x0=sm["start"], x1=sm["end"] + pd.Timedelta(days=1),
                      y0=0, y1=1, fillcolor=CORAL, opacity=0.12, line_width=0, layer="below")
        x = sm["start"]
    else:
        if not (lo <= sm["month"] <= hi):
            return
        x = sm["month"]
        fig.add_shape(type="line", xref="x", yref="paper", x0=x, x1=x, y0=0, y1=1,
                      line=dict(color=CORAL, width=1.2, dash="dot"))
    fig.add_annotation(x=x, y=1.0, xref="x", yref="paper", text="⚑ storm closure", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(size=10, color=CORAL), bgcolor="rgba(255,255,255,0.8)")


def storm_note(x_values, daily=False):
    if "Alustrian Palace" not in props or len(x_values) == 0:
        return ""
    sm = core.STORM
    lo, hi = pd.Timestamp(min(x_values)), pd.Timestamp(max(x_values))
    inside = (lo <= sm["end"] and hi >= sm["start"]) if daily else (lo <= sm["month"] <= hi)
    return " · ⚑ fictional storm: Palace closed 13–17 Sep 2025, cancellations spiked" if inside else ""


def period_label():
    return {"D": "daily", "W-SUN": "weekly", "MS": "monthly"}[FREQ]


def comparison_series(metric):
    """Series aligned to PT.index for LY or budget."""
    if compare == "Last year":
        if not core.covered(D, F.shifted()):
            return None, "Last year (n/a)"
        ly = core.period_table(D, F.shifted(), FREQ)
        if ly.empty:
            return None, "Last year"
        idx = ly.index + pd.DateOffset(years=1)
        if FREQ == "W-SUN":
            idx = idx.to_period("W").start_time
        s = pd.Series(ly[metric].values, index=idx)
        s = s[~s.index.duplicated()]
        return s.reindex(PT.index), "Last year"
    if F.has_dims:
        return None, "Budget (n/a with filters)"
    b = core.budget_period(D, F, FREQ)
    return (b[metric].reindex(PT.index) if metric in b else None), "Budget"


# ================================================================== pages
def page_overview():
    st.markdown(ui.page_title("Executive overview", f"{prop_opt} · {start:%d %b %Y} – {end:%d %b %Y} · "
                              f"comparisons {CMP_LABEL} shown first · revenue net of accommodation tax &amp; service charge"),
                unsafe_allow_html=True)
    cards = [card("Occupancy", "occ", f"{K['occ']:.1%}", "pts", spark=PT["occ"]),
             card("ADR", "adr", money(K["adr"]), spark=PT["adr"]),
             card("RevPAR", "revpar", money(K["revpar"]), spark=PT["revpar"]),
             card("Total revenue", "total", money(K["total"]), spark=PT["total"]),
             card("GOPPAR", "goppar", money(K["goppar"]), spark=PT["goppar"])]
    st.markdown(ui.kpi_cards(cards), unsafe_allow_html=True)
    note_dims()
    st.markdown(ui.insights_box(core.insights(D, F, K, LY, BUD), actions=core.recommendations(D, F, K, LY)),
                unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        cmp, cmp_name = comparison_series("total")
        pm = partial_mask(PT.index)
        fig = go.Figure()
        add_bars(fig, PT.index, PT["room_rev"], "Rooms", NAVY, pm)
        add_bars(fig, PT.index, PT["anc"], "Ancillary", GOLD, pm)
        add_partial_legend(fig, pm)
        if cmp is not None:
            fig.add_scatter(x=PT.index, y=cmp, name=cmp_name, mode="lines+markers",
                            line=dict(color=CORAL, width=2, dash="dot"), marker=dict(size=5))
        fig.update_layout(barmode="stack", yaxis=dict(tickprefix="$", tickformat="~s"))
        add_storm(fig, PT.index, daily=FREQ != "MS")
        chart(fig, "Total revenue", f"{period_label().capitalize()} rooms + ancillary, against {cmp_name.lower()}"
              + partial_note(pm) + storm_note(PT.index, FREQ != "MS"))
    with c2:
        mix = {"Rooms": K["room_rev"]}
        n = core.nights(D, F)
        for c in core.ANC_COLS:
            mix[core.ANC_LABELS[c]] = n[c].sum()
        fig = go.Figure(go.Pie(labels=list(mix), values=list(mix.values()), hole=0.62, sort=False,
                               marker=dict(colors=[NAVY, GOLD, TEAL, SEA, SLATE], line=dict(color="white", width=2)),
                               textinfo="percent", textposition="outside", texttemplate="%{label}<br>%{percent:.0%}"))
        fig.update_layout(showlegend=False, margin=dict(l=30, r=30, t=30, b=30),
                          annotations=[dict(text=f"<b>{money(K['total'])}</b><br><span style='font-size:11px;color:{MUTED}'>total revenue</span>",
                                            showarrow=False, font=dict(size=17, color=NAVY))])
        chart(fig, "Revenue mix", "Rooms vs ancillary streams")

    c3, c4 = st.columns([3, 2], gap="medium")
    with c3:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        pm = partial_mask(PT.index)
        add_bars(fig, PT.index, PT["occ"], "Occupancy", SEA, pm, secondary_y=False)
        add_partial_legend(fig, pm, secondary_y=False)
        add_storm(fig, PT.index, daily=FREQ != "MS")
        fig.add_scatter(x=PT.index, y=PT["adr"], name="ADR", mode="lines+markers", line=dict(color=NAVY, width=2.4),
                        marker=dict(size=5), secondary_y=True)
        pct_axis(fig, False, range=[0, 1.1], dtick=0.25)
        nice_money_axis(fig, PT["adr"].max())
        chart(fig, "Occupancy & ADR", "High season fills the hotel and lifts rate – the classic Caribbean curve"
              + partial_note(pm))
    with c4:
        n = core.nights(D, F)
        inv = D["inv"][D["inv"].property.isin(props)].groupby("room_type")["rooms"].sum()
        rp = (n.groupby("room_type")["room_revenue"].sum() / (inv * K["days"])).dropna()
        order = [r for r in core.ROOM_TYPES if r in rp.index]
        fig = go.Figure()
        fig.add_bar(y=order, x=rp[order], orientation="h", name="This period", marker_color=TEAL,
                    text=[money(v) for v in rp[order]], textposition="outside", cliponaxis=False)
        if LY:
            nl = core.nights(D, F.shifted())
            rpl = (nl.groupby("room_type")["room_revenue"].sum() / (inv * LY["days"])).reindex(order)
            fig.add_bar(y=order, x=rpl, orientation="h", name="Last year", marker_color=SAND)
        fig.update_layout(barmode="group", xaxis=dict(tickprefix="$", showgrid=True, gridcolor="#EFEAE1"),
                          yaxis=dict(autorange="reversed"), margin=dict(l=8, r=40, t=34, b=8))
        chart(fig, "RevPAR by room type", "Revenue per available room, this period vs last year")


def page_pricing():
    st.markdown(ui.page_title("Pricing & revenue", "Where rate is won or lost – by room, day, lead time and "
                              "against the competition"), unsafe_allow_html=True)
    n = core.nights(D, F)
    nl = core.nights(D, F.shifted()) if LY else None
    ci = core.compset_index(D, F)
    idx_now = ci["our_adr"].mean() / ci["comp_adr"].mean() * 100 if len(ci) else np.nan
    cil = core.compset_index(D, F.shifted()) if LY else pd.DataFrame()
    idx_ly = cil["our_adr"].mean() / cil["comp_adr"].mean() * 100 if len(cil) else None
    lead = n["lead_time_days"].mean()
    lead_ly = nl["lead_time_days"].mean() if nl is not None and len(nl) else None
    pc = core.pace(D, F, 4)
    otb, otb_ly = pc["otb"].sum(), pc["ly_otb"].sum()
    wk = n[n["dow"].isin(["Fri", "Sat"])]
    wd = n[~n["dow"].isin(["Fri", "Sat"])]
    prem = wk["room_revenue"].mean() / wd["room_revenue"].mean() - 1 if len(wk) and len(wd) else np.nan
    cards = [card("ADR", "adr", money(K["adr"]), spark=PT["adr"]),
             plain_card("Comp-set index", f"{idx_now:.1f}",
                        ui.delta_html(idx_now / 100, idx_ly / 100, "pts", "vs LY") if idx_ly else "100 = market rate",
                        spark=ci["index"] if len(ci) > 1 else None),
             plain_card("Avg lead time", f"{lead:.0f} days",
                        ui.delta_html(lead, lead_ly, "pct", "vs LY") if lead_ly else ""),
             plain_card("On the books · 4 mo", f"{otb:,.0f} RN",
                        ui.delta_html(otb, otb_ly, "pct", "vs same time LY") if otb_ly else ""),
             plain_card("Weekend premium", f"{prem:+.1%}" if not np.isnan(prem) else "–", "Fri–Sat vs Sun–Thu ADR")]
    st.markdown(ui.kpi_cards(cards), unsafe_allow_html=True)
    note_dims()

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        hm = n.pivot_table(index="room_type", columns="dow", values="room_revenue", aggfunc="mean")
        hm = hm.reindex(index=[r for r in core.ROOM_TYPES if r in hm.index], columns=core.DOWS)
        fig = go.Figure(go.Heatmap(z=hm.values, x=hm.columns, y=hm.index, colorscale=[[0, "#F6F1E7"], [0.5, SEA], [1, NAVY]],
                                   text=[[f"${v:,.0f}" if not np.isnan(v) else "" for v in row] for row in hm.values],
                                   texttemplate="%{text}", textfont=dict(size=11), showscale=False, xgap=3, ygap=3,
                                   hovertemplate="%{y} · %{x}<br>ADR %{text}<extra></extra>"))
        fig.update_layout(yaxis=dict(autorange="reversed"), xaxis=dict(side="top", ticks=""), margin=dict(t=30))
        chart(fig, "ADR by room type & day of week", "Average achieved rate; darker = higher")
    with c2:
        bins = [-1, 7, 30, 60, 90, 180, 400]
        labels = ["0–7", "8–30", "31–60", "61–90", "91–180", "180+"]
        nb = n.assign(b=pd.cut(n["lead_time_days"], bins, labels=labels))
        g = nb.groupby("b", observed=False).agg(rn=("room_revenue", "size"), rev=("room_revenue", "sum"))
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=labels, y=g["rn"] / g["rn"].sum(), name="Share of room nights", marker_color=SEA, secondary_y=False)
        fig.add_scatter(x=labels, y=g["rev"] / g["rn"], name="ADR", mode="lines+markers",
                        line=dict(color=NAVY, width=2.4), secondary_y=True)
        pct_axis(fig, False)
        nice_money_axis(fig, (g["rev"] / g["rn"]).max())
        fig.update_xaxes(title_text="Days booked before arrival")
        chart(fig, "Booking lead time", "How far ahead guests book, and what they pay")

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        fig = go.Figure()
        fig.add_bar(x=pc["month"], y=pc["otb"], name="On the books now", marker_color=TEAL,
                    text=[f"{v:,}" for v in pc["otb"]], textposition="inside", insidetextanchor="end", textangle=0,
                    insidetextfont=dict(color="white", size=10))
        fig.add_bar(x=pc["month"], y=pc["ly_otb"], name="Same time last year", marker_color=SAND,
                    text=[f"{v:,}" for v in pc["ly_otb"]], textposition="inside", insidetextanchor="end", textangle=0,
                    insidetextfont=dict(color=NAVY, size=10))
        fig.add_scatter(x=pc["month"], y=pc["ly_final"], name="Last year final", mode="markers",
                        marker=dict(symbol="diamond", size=10, color=CORAL, line=dict(color="white", width=1.5)))
        fig.update_layout(barmode="group", yaxis_title="Room nights")
        chart(fig, "Booking pace vs last year", f"Room nights on the books as of {AS_OF:%d %b %Y} for upcoming stays")
    with c4:
        dd = core.period_table(D, F, "D")
        dd = dd[dd["rn"] > 0].copy()
        dd["season"] = core.season_of(dd.index)
        fig = go.Figure()
        for s in core.SEASONS:
            x = dd[dd["season"] == s]
            fig.add_scatter(x=x["occ"], y=x["adr"], mode="markers", name=s,
                            marker=dict(color=ui.SEASON_COLORS[s], size=6, opacity=0.6, line=dict(width=0)),
                            hovertemplate="%{customdata}<br>Occ %{x:.0%} · ADR $%{y:,.0f}<extra></extra>",
                            customdata=x.index.strftime("%d %b %Y"))
        if len(dd) > 5:
            b1, b0 = np.polyfit(dd["occ"], dd["adr"], 1)
            xs = np.linspace(dd["occ"].min(), dd["occ"].max(), 20)
            fig.add_scatter(x=xs, y=b0 + b1 * xs, mode="lines", name="Trend", line=dict(color=NAVY, dash="dash", width=1.5))
        fig.update_xaxes(tickformat=".0%", title_text="Daily occupancy", showgrid=True, gridcolor="#EFEAE1")
        fig.update_yaxes(tickprefix="$", title_text="Daily ADR")
        chart(fig, "Rate vs occupancy", "Each dot is a day – are we pricing up when demand is high?")

    c5, c6 = st.columns([2, 3], gap="medium")
    with c5:
        fig = go.Figure()
        if len(ci):
            roll = ci["index"].rolling(3, min_periods=1).mean()
            fig.add_bar(x=ci.index, y=ci["index"] - 100, base=100, name="Monthly index",
                        marker_color=[TEAL if v >= 100 else CORAL for v in ci["index"]], opacity=0.35,
                        customdata=np.c_[ci["index"], ci["our_adr"], ci["comp_adr"]],
                        hovertemplate="%{x|%b %Y}<br>Index %{customdata[0]:.1f}<br>Ours $%{customdata[1]:,.0f} · "
                                      "comp set $%{customdata[2]:,.0f}<extra></extra>")
            fig.add_scatter(x=ci.index, y=roll, mode="lines+markers", name="3-month rolling average",
                            line=dict(color=NAVY, width=2.6, shape="spline"), marker=dict(size=5))
            fig.add_hline(y=100, line=dict(color=MUTED, dash="dot", width=1))
            lo_, hi_ = min(ci["index"].min(), 100), max(ci["index"].max(), 100)
            fig.update_yaxes(range=[lo_ - 1.5, hi_ + 1.5])
        fig.update_layout(yaxis_title="Index (100 = comp set)", bargap=0.35)
        chart(fig, "Comp-set ADR index", "Monthly vs simulated rate-shop of 5 similar boutiques (indicative); "
              "teal = above market, coral = below")
    with c6:
        with st.container(border=True):
            st.markdown(ui.chart_title("What-if pricing", "Move the rate and see the estimated RevPAR impact"),
                        unsafe_allow_html=True)
            s1, s2 = st.columns(2)
            chg = s1.slider("Rate change", -20, 30, 10, 1, format="%d%%", key="rate_chg") / 100
            el = s2.select_slider("Price elasticity (illustrative)", [-0.4, -0.6, -0.8, -1.0, -1.2, -1.5], value=-0.8, key="elasticity",
                                  help="% change in room nights for a 1% change in rate. Boutique leisure hotels in "
                                       "peak season are typically inelastic (-0.4 to -0.8); low season is more elastic.")
            w = core.whatif(K["occ"], K["adr"], chg, el)
            d_rev = (w["revpar"] - w["base_revpar"]) * K["avail"]
            cls = "up" if d_rev >= 0 else "down"
            st.markdown(f"""<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:4px 0 6px">
<div class="calc"><div class="kpi-label">ADR</div><div class="big" style="color:{NAVY}">{money(w['adr'])}</div><div class="note">from {money(K['adr'])}</div></div>
<div class="calc"><div class="kpi-label">Occupancy</div><div class="big" style="color:{NAVY}">{w['occ']:.1%}</div><div class="note">from {K['occ']:.1%}</div></div>
<div class="calc"><div class="kpi-label">RevPAR</div><div class="big {cls}">{money(w['revpar'])}</div><div class="note">from {money(w['base_revpar'])}</div></div>
<div class="calc"><div class="kpi-label">Δ Revenue</div><div class="big {cls}">{'+' if d_rev >= 0 else '−'}{money(abs(d_rev))}</div><div class="note">over this period</div></div>
</div>""", unsafe_allow_html=True)
            xs = np.arange(-20, 31, 1) / 100
            fig = go.Figure()
            for e, col, dash in ((-0.5, SEA, "dot"), (el, TEAL, "solid"), (-1.2, CORAL, "dot")):
                ys = [core.whatif(K["occ"], K["adr"], x, e)["revpar"] for x in xs]
                fig.add_scatter(x=xs, y=ys, mode="lines", name=f"elasticity {e}", line=dict(color=col, dash=dash, width=2.4 if e == el else 1.4))
            fig.add_scatter(x=[chg], y=[w["revpar"]], mode="markers", name="Your scenario",
                            marker=dict(color=NAVY, size=11, line=dict(color="white", width=2)))
            fig.update_xaxes(tickformat="+.0%", title_text="Rate change")
            fig.update_yaxes(tickprefix="$", title_text="RevPAR")
            fig.update_layout(height=240, margin=dict(l=8, r=8, t=30, b=8))
            st.plotly_chart(fig, width="stretch", config=ui.PLOTLY_CONFIG, theme=None)
            st.caption(f"Illustrative assumption: constant price elasticity of {el} – a {abs(chg):.0%} rate "
                       f"{'rise' if chg >= 0 else 'cut'} changes room nights by {el * chg:+.1%}; occupancy capped at 98%. "
                       "Directional only – a real engagement calibrates elasticity from the hotel's own booking history.")


def page_season():
    st.markdown(ui.page_title("Seasonality & forecast", "High season Dec–Apr · shoulder May–Jul & Nov · low / "
                              "hurricane season Aug–Oct"), unsafe_allow_html=True)
    fa = core.Filters(props, DATA_START, AS_OF, room_types, channels, segments, markets)
    mt = core.period_table(D, fa, "MS")
    mt["season"] = core.season_of(mt.index)
    by_s = core.nights(D, F).assign(s=lambda x: x["season"]).groupby("s").agg(rn=("room_revenue", "size"),
                                                                               rev=("room_revenue", "sum"))
    cal = core.calendar(F)
    sdays = pd.Series(core.season_of(cal["date"])).value_counts()
    rooms_n = core.rooms(D, F)
    sea = pd.DataFrame({"occ": by_s["rn"] / (sdays * rooms_n), "adr": by_s["rev"] / by_s["rn"]}).reindex(core.SEASONS)
    sea["revpar"] = sea["occ"] * sea["adr"]
    fc = core.forecast(D, F)
    nd = core.nights(D, F.with_dates(DATA_START, AS_OF), dims=False)
    festive = nd[((nd.stay_date.dt.month == 12) & (nd.stay_date.dt.day >= 20)) | ((nd.stay_date.dt.month == 1) & (nd.stay_date.dt.day <= 3))]
    fest = festive[festive.stay_date >= AS_OF - pd.DateOffset(years=1)]
    cards = [plain_card("High-season occ.", f"{sea.loc['High season', 'occ']:.0%}" if not np.isnan(sea.loc['High season', 'occ']) else "–",
                        f"ADR {money(sea.loc['High season', 'adr'])}"),
             plain_card("Low-season occ.", f"{sea.loc['Low / hurricane', 'occ']:.0%}" if not np.isnan(sea.loc['Low / hurricane', 'occ']) else "–",
                        f"ADR {money(sea.loc['Low / hurricane', 'adr'])}", color=CORAL),
             plain_card("Festive peak ADR", money(fest["room_revenue"].mean()) if len(fest) else "–", "20 Dec – 3 Jan, last season"),
             plain_card("Forecast · next 90d", f"{fc['forecast'].mean():.0%}",
                        ui.delta_html(fc["forecast"].mean(), fc["ly_actual"].mean(), "pts", "vs LY actual")),
             plain_card("On the books", f"{fc['otb'].mean():.0%}", "of next 90 days' rooms")]
    st.markdown(ui.kpi_cards(cards), unsafe_allow_html=True)
    st.caption("Heatmaps use the full 3-year history (property / room / guest filters apply; date filter does not)."
               + (" Coral outline = Sep 2025 fictional storm: Palace closed 13–17 Sep and cancellations spiked."
                  if "Alustrian Palace" in props else ""))

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def heat(metric, fmt, scale):
        p = mt.assign(y=mt.index.year, m=mt.index.month).pivot_table(index="y", columns="m", values=metric)
        p = p.reindex(columns=range(1, 13))
        text = [[("" if np.isnan(v) else fmt(v)) for v in row] for row in p.values]
        fig = go.Figure(go.Heatmap(z=p.values, x=months, y=[str(y) for y in p.index], colorscale=scale, showscale=False,
                                   text=text, texttemplate="%{text}", textfont=dict(size=10), xgap=2, ygap=2,
                                   hovertemplate="%{x} %{y}: %{text}<extra></extra>"))
        bands = [(0, 4, "High"), (4, 7, "Shoulder"), (7, 10, "Low / hurricane"), (10, 11, "Sh."), (11, 12, "High")]
        colors = {"High": TEAL, "Shoulder": GOLD, "Sh.": GOLD, "Low / hurricane": CORAL}
        for a, b, lab in bands:
            fig.add_shape(type="rect", xref="x", yref="paper", x0=a - 0.48, x1=b - 0.52, y0=1.03, y1=1.09,
                          fillcolor=colors[lab], line_width=0, opacity=0.85)
            fig.add_annotation(x=(a + b - 1) / 2, y=1.1, xref="x", yref="paper", text=lab, showarrow=False,
                               yanchor="bottom", font=dict(size=10, color=MUTED))
        rows = [str(y) for y in p.index]
        if "Alustrian Palace" in props and "2025" in rows:
            yi = rows.index("2025")
            fig.add_shape(type="rect", xref="x", yref="y", x0=7.5, x1=8.5, y0=yi - 0.5, y1=yi + 0.5,
                          line=dict(color=CORAL, width=2.5), fillcolor="rgba(0,0,0,0)")
        fig.update_layout(yaxis=dict(autorange="reversed", type="category"), margin=dict(t=48, l=8, r=8, b=8), height=260)
        return fig

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        chart(heat("occ", lambda v: f"{v:.0%}", [[0, "#FBEDE7"], [0.45, "#F3E3C3"], [1, TEAL]]),
              "Monthly occupancy", "Hurricane-season trough vs the Dec–Apr peak")
    with c2:
        chart(heat("adr", lambda v: f"{v:,.0f}", [[0, "#F6F1E7"], [0.5, GOLD], [1, NAVY]]),
              "Monthly ADR (USD)", "Rate follows the season – December's festive weeks lift the month")

    c3, c4 = st.columns([3, 2], gap="medium")
    with c3:
        hist = core.period_table(D, core.Filters(props, AS_OF - pd.Timedelta(days=89), AS_OF, room_types), "D")
        fig = go.Figure()
        fs = fc.copy()
        for col in ("forecast", "lo", "hi", "ly_actual"):
            fs[col] = fs[col].rolling(7, center=True, min_periods=1).mean()
        fig.add_scatter(x=fs["date"], y=fs["otb"], name="On the books", mode="lines", line=dict(width=0),
                        fill="tozeroy", fillcolor="rgba(200,164,100,0.35)")
        fig.add_scatter(x=list(fs["date"]) + list(fs["date"][::-1]), y=list(fs["hi"]) + list(fs["lo"][::-1]),
                        fill="toself", fillcolor="rgba(27,127,134,0.15)", line=dict(width=0), name="80% confidence band",
                        hoverinfo="skip")
        fig.add_scatter(x=hist.index, y=hist["occ"].rolling(7, min_periods=1).mean(), name="Actual (7-day avg)",
                        line=dict(color=NAVY, width=2))
        fig.add_scatter(x=fs["date"], y=fs["forecast"], name="Forecast", line=dict(color=TEAL, width=2.6))
        fig.add_scatter(x=fs["date"], y=fs["ly_actual"], name="Last year actual",
                        line=dict(color=CORAL, width=1.4, dash="dot"))
        fig.add_vline(x=AS_OF, line=dict(color=MUTED, dash="dot", width=1))
        fig.add_annotation(x=AS_OF, y=1.02, yref="y", text="today", showarrow=False, xanchor="left",
                           font=dict(size=10, color=MUTED))
        fig.update_yaxes(tickformat=".0%", range=[0, 1.06])
        fig.update_layout(height=360)
        chart(fig, "90-day occupancy forecast", ("Property & room-type filters only. " if (F.has_dims or seasons or dows) else "") + "Pick-up model (on-the-books + last year's pick-up) blended with a "
              "trend-adjusted seasonal baseline")
    with c4:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=sea.index, y=sea["occ"], name="Occupancy", marker_color=[ui.SEASON_COLORS[s] for s in sea.index],
                    text=[f"{v:.0%}" if not np.isnan(v) else "" for v in sea["occ"]], textposition="inside",
                    insidetextfont=dict(color="white"), secondary_y=False)
        fig.add_scatter(x=sea.index, y=sea["revpar"], name="RevPAR", mode="lines+markers",
                        marker=dict(size=10, color=NAVY, line=dict(color="white", width=2)),
                        hovertemplate="%{x}<br>RevPAR $%{y:,.0f}<extra></extra>",
                        line=dict(color=NAVY, width=2), secondary_y=True)
        pct_axis(fig, False, range=[0, 1.1], dtick=0.25)
        nice_money_axis(fig, sea["revpar"].max())
        fig.update_layout(height=360)
        chart(fig, "Season scorecard", "Occupancy and RevPAR by season, selected period")


def page_channels():
    st.markdown(ui.page_title("Channels & guests", "Who books, through which door, and what it costs"),
                unsafe_allow_html=True)
    n = core.nights(D, F)
    mix = core.channel_mix(n)
    nl = core.nights(D, F.shifted()) if LY else pd.DataFrame()
    mix_ly = core.channel_mix(nl) if len(nl) else None
    res = core.reservations(D, F, ("Checked out",))
    res_ly = core.reservations(D, F.shifted(), ("Checked out",)) if LY else pd.DataFrame()
    ds = mix["share_rn"].get("Direct website", 0)
    ds_ly = mix_ly["share_rn"].get("Direct website", 0) if mix_ly is not None else None
    net_adr = (n["room_revenue"].sum() - n["commission"].sum()) / len(n)
    net_ly = (nl["room_revenue"].sum() - nl["commission"].sum()) / len(nl) if len(nl) else None
    rep = res["repeat_guest"].mean() if len(res) else np.nan
    rep_ly = res_ly["repeat_guest"].mean() if len(res_ly) else None
    los = res["nights"].mean() if len(res) else np.nan
    pt_share = PT  # sparkline for commission
    cards = [plain_card("Direct share", f"{ds:.1%}", ui.delta_html(ds, ds_ly, "pts", "vs LY") if ds_ly is not None else ""),
             card("Commissions paid", "commission", money(K["commission"]), good_up=False, spark=pt_share["commission"]),
             plain_card("Net ADR", money(net_adr), ui.delta_html(net_adr, net_ly, "pct", "vs LY") if net_ly else ""),
             plain_card("Repeat guests", f"{rep:.1%}" if not np.isnan(rep) else "–",
                        ui.delta_html(rep, rep_ly, "pts", "vs LY") if rep_ly is not None and not np.isnan(rep) else ""),
             plain_card("Avg stay", f"{los:.1f} nights" if not np.isnan(los) else "–",
                        ui.delta_html(los, res_ly["nights"].mean(), "pct", "vs LY") if len(res_ly) else "")]
    st.markdown(ui.kpi_cards(cards), unsafe_allow_html=True)
    note_dims()

    st.markdown('<div class="section-title">Channels</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        m = mix.sort_values("revenue")
        fig = go.Figure(go.Bar(y=m.index, x=m["revenue"], orientation="h",
                               marker_color=[ui.CHANNEL_COLORS[c] for c in m.index],
                               text=[f"{money(r)} · {rn:,} RN" for r, rn in zip(m["revenue"], m["rn"])],
                               textposition="outside", cliponaxis=False, textfont=dict(size=11)))
        fig.update_layout(xaxis=dict(tickprefix="$", tickformat="~s", showgrid=True, gridcolor="#EFEAE1",
                                     range=[0, m["revenue"].max() * 1.75]), margin=dict(l=8, r=8, t=20, b=8))
        chart(fig, "Room revenue & room nights by channel", "")
    with c2:
        fig = go.Figure()
        fig.add_bar(x=mix.index, y=mix["adr"], name="Gross ADR", marker_color=SAND)
        fig.add_bar(x=mix.index, y=mix["net_adr"], name="Net ADR (after commission)", marker_color=TEAL,
                    text=[f"−{c:.0%}" for c in (1 - mix["net_adr"] / mix["adr"])], textposition="outside")
        fig.update_layout(barmode="group", yaxis=dict(tickprefix="$"), xaxis=dict(tickangle=0))
        fig.update_xaxes(ticktext=[c.replace("Travel agents/wholesalers", "Agents/<br>wholesale").replace("Direct website", "Direct")
                                   for c in mix.index], tickvals=list(mix.index))
        chart(fig, "Gross vs net ADR", "What each channel really pays per night once commission is deducted")

    c3, c4 = st.columns([3, 2], gap="medium")
    with c3:
        fa = F.with_dates(max(DATA_START, F.start - pd.DateOffset(years=1)), F.end)
        nn = core.nights(D, fa)
        g = nn.groupby([nn["stay_date"].dt.to_period("M").dt.start_time, "channel"]).size().unstack(fill_value=0)
        sh = g.div(g.sum(axis=1), axis=0)
        fig = go.Figure()
        if "Direct website" in sh:
            fig.add_scatter(x=sh.index, y=sh["Direct website"], name="Direct website", mode="lines+markers",
                            line=dict(color=TEAL, width=2.6), fill="tozeroy", fillcolor="rgba(27,127,134,0.08)")
        ota = sh[[c for c in core.OTA if c in sh]].sum(axis=1)
        fig.add_scatter(x=sh.index, y=ota, name="OTAs (Booking.com, Expedia, Airbnb)", mode="lines",
                        line=dict(color=CORAL, width=2, dash="dot"))
        fig.update_yaxes(tickformat=".0%", rangemode="tozero")
        add_storm(fig, sh.index)
        chart(fig, "Direct-booking share trend", "Monthly share of room nights, incl. the prior 12 months for context"
              + storm_note(sh.index))
    with c4:
        with st.container(border=True):
            st.markdown(ui.chart_title("Commission-savings calculator", "Shift OTA & wholesale nights to your own website"),
                        unsafe_allow_html=True)
            shift = st.slider("Share of OTA/wholesale nights moved to direct", 0, 40, 10, 1, format="%d%%", key="shift") / 100
            dcost = st.slider("Direct booking cost (engine, card fees, marketing)", 0, 12, int(core.DIRECT_COST * 100), 1, format="%d%%", key="dcost") / 100
            cs = core.commission_savings(n, shift, dcost)
            annual = cs["saving"] * 365 / max(K["days"], 1)
            st.markdown(f"""<div class="calc" style="margin-top:4px"><div class="kpi-label">Estimated saving this period</div>
<div class="big">{money(cs['saving'])}</div><div class="note">{cs['nights']:,.0f} room nights moved · avg OTA/wholesale commission
{cs['ota_rate']:.1%} → {dcost:.0%} direct · ≈ <b>{money(annual)}</b> a year</div></div>""", unsafe_allow_html=True)
            st.caption("Assumes the moved guests pay the same rate; savings flow straight to GOP.")

    st.markdown('<div class="section-title">Guests</div>', unsafe_allow_html=True)
    c5, c6, c7 = st.columns(3, gap="medium")
    with c5:
        sg = n.groupby("segment").agg(rn=("room_revenue", "size"), rev=("room_revenue", "sum")).reindex(
            [s for s in core.SEGMENTS if s in set(n["segment"])])
        fig = go.Figure(go.Pie(labels=sg.index, values=sg["rev"], hole=0.6, sort=False,
                               marker=dict(colors=[TEAL, GOLD, NAVY, SLATE], line=dict(color="white", width=2)),
                               texttemplate="%{percent:.0%}", textposition="inside",
                               customdata=sg["rev"] / sg["rn"],
                               hovertemplate="%{label}<br>Revenue %{value:$,.0f}<br>ADR %{customdata:$,.0f}<extra></extra>"))
        fig.update_layout(legend=dict(orientation="h", y=-0.05, yanchor="top", entrywidth=130, font=dict(size=10)),
                          margin=dict(t=10, b=10), height=380)
        chart(fig, "Room revenue by guest segment", "")
    with c6:
        sm = n.groupby(["season", "source_market"]).size().unstack(fill_value=0)
        sm = sm.reindex([s for s in core.SEASONS if s in sm.index])
        sm = sm.div(sm.sum(axis=1), axis=0)
        fig = go.Figure()
        for mk, col in zip(core.MARKETS, [NAVY, CORAL, TEAL, GOLD, SEA]):
            if mk in sm:
                fig.add_bar(x=sm.index, y=sm[mk], name=mk, marker_color=col,
                            text=[f"{v:.0%}" if v >= 0.06 else "" for v in sm[mk]], textposition="inside",
                            insidetextfont=dict(color="white", size=10))
        fig.update_layout(barmode="stack", yaxis=dict(tickformat=".0%"), height=380,
                          legend=dict(orientation="h", entrywidth=62, y=1.0, font=dict(size=10)), margin=dict(t=50))
        fig.update_xaxes(tickvals=list(sm.index), ticktext=[x.split(" ")[0] for x in sm.index], tickangle=0)
        chart(fig, "Source markets by season", {1: "US-led; Canadians rise in the winter months"}.get(
            0 if "Alustrian Villas" in props else 1, "Barbados draws the UK; Caribbean residents travel in summer"))
    with c7:
        if len(res):
            bins = [0, 2, 4, 7, 10, 30]
            labs = ["1–2", "3–4", "5–7", "8–10", "11+"]
            rr = res.assign(b=pd.cut(res["nights"], bins, labels=labs))
            g = rr.groupby(["b", "segment"], observed=False).size().unstack(fill_value=0)
            fig = go.Figure()
            for s, col in zip(core.SEGMENTS, [TEAL, GOLD, NAVY, SLATE]):
                if s in g:
                    fig.add_bar(x=labs, y=g[s], name=s, marker_color=col)
            fig.update_layout(barmode="stack", yaxis_title="Stays", height=380, margin=dict(t=50),
                              legend=dict(orientation="h", entrywidth=110, y=1.0, font=dict(size=10)))
            fig.update_xaxes(title_text="Nights")
            chart(fig, "Length of stay", "Families and villa guests stay longest")


def page_costs():
    st.markdown(ui.page_title("Costs & profitability", "Gross operating profit, cost lines and ancillary revenue · "
                              "property level"), unsafe_allow_html=True)
    c = core.costs(D, F)
    cl = core.costs(D, F.shifted()) if LY else None
    tot = c[core.COST_COLS].sum()
    util = (tot["electricity"] + tot["water_gas"]) / K["total_all"]
    util_ly = ((cl["electricity"].sum() + cl["water_gas"].sum()) / LY["total_all"]) if LY else None
    na = core.nights(D, F, dims=False)
    fb_rev = na["fb_revenue"].sum()
    fbp = tot["fb_cost"] / fb_rev if fb_rev else np.nan
    fbp_ly = None
    if LY:
        nal = core.nights(D, F.shifted(), dims=False)
        fbp_ly = cl["fb_cost"].sum() / nal["fb_revenue"].sum()
        anc_por_ly = nal["ancillary_revenue"].sum() / len(nal)
    anc_por = na["ancillary_revenue"].sum() / len(na)
    PT["util_pct"] = (PT["electricity"] + PT["water_gas"]) / PT["total_all"].replace(0, np.nan)
    cards = [card("GOP", "gop", money(K["gop"]), spark=PT["gop"]),
             card("GOP margin", "gop_margin", f"{K['gop_margin']:.1%}", "pts", spark=PT["gop_margin"]),
             card("CPOR", "cpor", money(K["cpor"]), good_up=False, spark=PT["cpor"]),
             plain_card("Utilities % rev.", f"{util:.1%}", ui.delta_html(util, util_ly, "pts", "vs LY", good_up=False)
                        if util_ly else "", spark=PT["util_pct"], color=CORAL),
             plain_card("F&B cost %", f"{fbp:.1%}", ui.delta_html(fbp, fbp_ly, "pts", "vs LY", good_up=False) if fbp_ly else "target 30%"),
             plain_card("Ancillary / room", money(anc_por), ui.delta_html(anc_por, anc_por_ly, "pct", "vs LY") if LY else "")]
    st.markdown(ui.kpi_cards(cards), unsafe_allow_html=True)
    if F.has_dims:
        st.caption("ⓘ Costs and GOP are property-level; room / channel / guest filters don't apply on this page "
                   "(except ancillary revenue per occupied room, which uses all stays).")

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        cols = [NAVY, CORAL, SEA, GOLD, MUTED, SLATE, SAND]
        pm = partial_mask(PT.index)
        for col, color in zip(core.COST_COLS, cols):
            add_bars(fig, PT.index, PT[col], core.COST_LABELS[col], color, pm, secondary_y=False)
        add_partial_legend(fig, pm, secondary_y=False)
        add_storm(fig, PT.index, daily=FREQ != "MS")
        fig.add_scatter(x=PT.index, y=PT["gop_margin"], name="GOP margin", mode="lines+markers",
                        line=dict(color=TEAL, width=2.6), secondary_y=True)
        fig.update_layout(barmode="stack", legend=dict(font=dict(size=10)), height=360)
        fig.update_yaxes(tickprefix="$", tickformat="~s", secondary_y=False)
        gm_lo = float(np.floor(min(-0.2, PT["gop_margin"].min() - 0.05) * 5) / 5)
        fig.update_yaxes(tickformat=".0%", secondary_y=True, showgrid=False, range=[gm_lo, 0.8], tick0=0, dtick=0.2)
        chart(fig, "Operating costs & GOP margin", f"{period_label().capitalize()} cost lines; margin swings with the season"
              + partial_note(pm))
    with c2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        e_por = PT["electricity"] / PT["orn_all"].replace(0, np.nan)
        add_bars(fig, PT.index, e_por, "Electricity per occupied room",
                 [CORAL if m.month in (6, 7, 8, 9, 10) else GOLD for m in PT.index], pm, secondary_y=False)
        add_partial_legend(fig, pm, secondary_y=False)
        fig.add_scatter(x=PT.index, y=PT["electricity_kwh"] / PT["days"], name="kWh per day", mode="lines",
                        line=dict(color=NAVY, width=1.8), secondary_y=True)
        fig.update_yaxes(tickprefix="$", secondary_y=False)
        nice_money_axis(fig, (PT["electricity_kwh"] / PT["days"]).max(), prefix="")
        fig.update_xaxes(nticks=6, tickangle=0)
        fig.update_layout(height=360)
        chart(fig, "Utilities spotlight: electricity",
              f"Electricity is {tot['electricity'] / K['total_all']:.1%} of revenue at ~$0.40/kWh – AC load peaks in summer (coral)")

    c3, c4 = st.columns([2, 3], gap="medium")
    with c3:
        a = pd.Series({core.ANC_LABELS[col]: na[col].sum() / len(na) for col in core.ANC_COLS})
        shares = pd.Series({core.ANC_LABELS[col]: na[col].sum() / K["total_all"] for col in core.ANC_COLS})
        fig = go.Figure(go.Bar(x=a.index, y=a.values, marker_color=[GOLD, TEAL, SEA, SLATE],
                               text=[f"<b>{money(v)}</b><br>{s:.0%} of rev."
                                     for v, s in zip(a.values, shares.values)], textposition="outside", cliponaxis=False,
                               textfont=dict(size=12)))
        fig.update_layout(yaxis=dict(tickprefix="$", range=[0, a.max() * 1.35]), margin=dict(t=20))
        chart(fig, "Ancillary revenue per occupied room", f"Ancillary = {shares.sum():.0%} of total revenue")
    with c4:
        fbm = core.period_table(D, F, "MS")
        nm = na.groupby(na["stay_date"].dt.to_period("M").dt.start_time)["fb_revenue"].sum()
        fbpct = (fbm["fb_cost"] / nm.reindex(fbm.index)).dropna()
        fig = go.Figure()
        fig.add_hline(y=0.30, line=dict(color=CORAL, dash="dash", width=1.2),
                      annotation_text="30% target", annotation_position="bottom right",
                      annotation_font=dict(size=10, color=CORAL))
        fig.add_scatter(x=fbpct.index, y=fbpct, mode="lines+markers", name="F&B cost %",
                        line=dict(color=NAVY, width=2.4),
                        marker=dict(color=[CORAL if v > 0.33 else NAVY for v in fbpct], size=8))
        fig.update_yaxes(tickformat=".0%", range=[0.25, max(0.4, fbpct.max() + 0.01)])
        fig.update_layout(showlegend=False)
        chart(fig, "F&B cost of sales %", "Monthly food & beverage cost as % of F&B revenue; coral = above 33%")

    with st.container(border=True):
        st.markdown(ui.chart_title("Mini P&L", "Selected period, property level"), unsafe_allow_html=True)
        rows = [("Room revenue", K["total_all"] - na["ancillary_revenue"].sum()), ("Ancillary revenue", na["ancillary_revenue"].sum()),
                ("Total revenue", K["total_all"])] + [("less " + core.COST_LABELS[col], tot[col]) for col in core.COST_COLS] + \
               [("Gross operating profit", K["gop"])]
        ly_vals = None
        if LY:
            ctl = cl[core.COST_COLS].sum()
            nal = core.nights(D, F.shifted(), dims=False)
            ly_vals = [LY["total_all"] - nal["ancillary_revenue"].sum(), nal["ancillary_revenue"].sum(), LY["total_all"]] + \
                      [ctl[col] for col in core.COST_COLS] + [LY["gop"]]
        df = pd.DataFrame(rows, columns=["Line", "Amount"])
        df["% of revenue"] = df["Amount"].abs() / K["total_all"]
        df["Per occupied room"] = df["Amount"] / K["orn_all"]
        if ly_vals:
            df["Last year"] = ly_vals
            df["Change vs LY"] = df["Amount"] / df["Last year"] - 1
        st.dataframe(df, hide_index=True, width="stretch", height=(len(df) + 1) * 35 + 3, column_config={
            "Amount": st.column_config.NumberColumn(format="$%,.0f"),
            "Last year": st.column_config.NumberColumn(format="$%,.0f"),
            "% of revenue": st.column_config.NumberColumn(format="percent"),
            "Per occupied room": st.column_config.NumberColumn(format="$%,.0f"),
            "Change vs LY": st.column_config.NumberColumn(format="percent")})


def page_reputation():
    st.markdown(ui.page_title("Reputation & operations", "Guest reviews across platforms and booking reliability"),
                unsafe_allow_html=True)
    rv = core._cal_filter(D["reviews"], F, "review_date")
    tp = core._cal_filter(D["topics"], F, "review_date")
    rvl = core._cal_filter(D["reviews"], F.shifted(), "review_date") if LY else pd.DataFrame()
    tpl = core._cal_filter(D["topics"], F.shifted(), "review_date") if LY else pd.DataFrame()
    r = core.reservations(D, F)
    rl = core.reservations(D, F.shifted()) if LY else pd.DataFrame()

    def rate(df, s):
        return (df["status"] == s).mean() if len(df) else np.nan

    sc, sc_ly = rv["score_5pt"].mean(), (rvl["score_5pt"].mean() if len(rvl) else None)
    pos, pos_ly = ((tp["sentiment"] == "Positive").mean() if len(tp) else np.nan,
                   (tpl["sentiment"] == "Positive").mean() if len(tpl) else None)
    cx, cx_ly = rate(r, "Cancelled"), (rate(rl, "Cancelled") if len(rl) else None)
    ns, ns_ly = rate(r, "No-show"), (rate(rl, "No-show") if len(rl) else None)
    cards = [plain_card("Review score", f"{sc:.2f} / 5" if not np.isnan(sc) else "–",
                        ui.delta_html(sc, sc_ly, "pct", "vs LY") if sc_ly else ""),
             plain_card("Reviews", f"{len(rv):,}", ui.delta_html(len(rv), len(rvl), "pct", "vs LY") if len(rvl) else ""),
             plain_card("Positive mentions", f"{pos:.0%}" if not np.isnan(pos) else "–",
                        ui.delta_html(pos, pos_ly, "pts", "vs LY") if pos_ly is not None else ""),
             plain_card("Cancellations", f"{cx:.1%}" if not np.isnan(cx) else "–",
                        ui.delta_html(cx, cx_ly, "pts", "vs LY", good_up=False) if cx_ly is not None else ""),
             plain_card("No-shows", f"{ns:.1%}" if not np.isnan(ns) else "–",
                        ui.delta_html(ns, ns_ly, "pts", "vs LY", good_up=False) if ns_ly is not None else "")]
    st.markdown(ui.kpi_cards(cards), unsafe_allow_html=True)
    st.caption("Review figures follow property & date filters; Booking.com scores (out of 10) are shown on a 5-point scale.")

    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        wide = core._cal_filter(D["reviews"], F.with_dates(max(DATA_START, F.start - pd.DateOffset(months=6)), F.end), "review_date")
        g = wide.groupby([wide["review_date"].dt.to_period("M").dt.start_time, "platform"])["score_5pt"].mean().unstack()
        g = g.rolling(3, min_periods=1).mean()
        fig = go.Figure()
        for p, col in (("TripAdvisor", TEAL), ("Google", GOLD), ("Booking.com", NAVY)):
            if p in g:
                fig.add_scatter(x=g.index, y=g[p], name=p, mode="lines", line=dict(color=col, width=2.4))
        fig.update_yaxes(range=[3.6, 5], title_text="Score (of 5)")
        add_storm(fig, g.index)
        chart(fig, "Review score by platform", "3-month rolling average; note the late-2025 dip (housekeeping staffing)")
    with c2:
        if len(tp):
            s = tp.groupby(["topic", "sentiment"]).size().unstack(fill_value=0)
            s = s.div(s.sum(axis=1), axis=0).reindex(columns=["Positive", "Neutral", "Negative"], fill_value=0)
            s = s.sort_values("Positive")
            fig = go.Figure()
            for sent, col in (("Positive", TEAL), ("Neutral", SAND), ("Negative", CORAL)):
                fig.add_bar(y=s.index, x=s[sent], name=sent, orientation="h", marker_color=col,
                            text=[f"{v:.0%}" if v >= 0.07 else "" for v in s[sent]], textposition="inside",
                            insidetextfont=dict(color="white" if sent != "Neutral" else NAVY, size=11))
            fig.update_layout(barmode="stack", xaxis=dict(tickformat=".0%", range=[0, 1]))
            chart(fig, "Sentiment by topic", "Share of review mentions")
        else:
            st.info("No reviews in this period.")

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        if len(r):
            g = r.groupby("channel")["status"].value_counts(normalize=True).unstack(fill_value=0)
            g = g.reindex(index=[ch for ch in core.CHANNELS if ch in g.index], columns=["Cancelled", "No-show"], fill_value=0)
            fig = go.Figure()
            fig.add_bar(x=g.index, y=g["Cancelled"], name="Cancelled", marker_color=CORAL)
            fig.add_bar(x=g.index, y=g["No-show"], name="No-show", marker_color=GOLD)
            fig.update_layout(barmode="group", yaxis=dict(tickformat=".0%"))
            fig.update_xaxes(ticktext=[c.replace("Travel agents/wholesalers", "Agents/<br>wholesale").replace("Direct website", "Direct")
                                       for c in g.index], tickvals=list(g.index))
            chart(fig, "Cancellations & no-shows by channel", "Share of bookings arriving in the period")
    with c4:
        fa = F.with_dates(max(DATA_START, F.start - pd.DateOffset(years=1)), F.end)
        ra = core.reservations(D, fa)
        if len(ra):
            g = ra.groupby(ra["arrival_date"].dt.to_period("M").dt.start_time)["status"].value_counts(normalize=True).unstack(fill_value=0)
            g = g.reindex(columns=["Cancelled", "No-show"], fill_value=0)
            fig = go.Figure()
            fig.add_scatter(x=g.index, y=g["Cancelled"], name="Cancellation rate", mode="lines+markers",
                            line=dict(color=CORAL, width=2.4))
            fig.add_scatter(x=g.index, y=g["No-show"], name="No-show rate", mode="lines+markers",
                            line=dict(color=GOLD, width=2))
            fig.update_yaxes(tickformat=".0%", rangemode="tozero")
            add_storm(fig, g.index)
            chart(fig, "Cancellation trend", "By arrival month, incl. prior 12 months" + (storm_note(g.index) or
                                                                                         "; OTA-heavy months cancel more"))


def page_built():
    st.markdown(ui.page_title("How it's built", "From scattered exports to one trusted, automatically refreshed "
                              "model – the data-automation service behind this dashboard"), unsafe_allow_html=True)
    st.markdown("""<div class="flow">
<div class="box messy"><h5>1 · Messy inputs</h5>PMS exports, OTA extranet CSVs (Booking.com, Expedia, Airbnb), budget spreadsheets,
accounting P&amp;L, review sites.<br><span class="pill">mixed date formats</span><span class="pill">room codes</span>
<span class="pill">duplicates</span><span class="pill">$ as text</span><span class="pill">wide budgets</span></div>
<div class="arrow">➜</div>
<div class="box clean"><h5>2 · Clean, modelled data</h5>Automated Python / Power Query pipeline standardises, de-duplicates and
reconciles every source into a star schema: one row per stay-night, plus costs, budget, comp set and reviews.
<br><span class="pill">refreshes daily</span><span class="pill">validation checks</span></div>
<div class="arrow">➜</div>
<div class="box dash"><h5>3 · Decisions</h5>This dashboard (or Power BI) with KPIs vs last year &amp; budget, plain-English
insights, pricing what-ifs, and a one-click monthly owner report.<br><span class="pill">phone-friendly</span>
<span class="pill">PDF / Excel export</span></div></div>""", unsafe_allow_html=True)

    st.markdown('<div class="note" style="font-size:.88rem;margin:-4px 0 12px"><b>Same model, your choice of front end:</b> '
                'the cleaned model and these visuals can be delivered in <b>Power BI</b> (for teams already on Microsoft 365) '
                'or as a hosted <b>web app</b> like this one.</div>', unsafe_allow_html=True)
    dq = core.data_quality(D["raw"])
    st.markdown('<div class="section-title">Data-quality scorecard</div>', unsafe_allow_html=True)
    tiles = [("Sources merged", f"{dq['sources']}", "PMS export, Booking.com CSV, budget sheet"),
             ("Duplicates removed", f"{dq['duplicates']}", f"+ {dq['blank_rows']} blank row(s) dropped"),
             ("Missing values fixed", f"{dq['missing']}", "rates / commissions back-filled from source"),
             ("Formats standardised", f"{dq['date_formats']} → 1", f"date formats; {dq['room_codes']} room codes → 4 types; "
                                                                   f"{dq['channel_codes']} source codes → 6 channels"),
             ("Text numbers converted", f"{dq['text_numbers']}", "\"$\", \"USD 1 234\", \"%\", \"k\", \"5 nts\" → numbers"),
             ("Manual reporting saved", f"~{dq['hours_saved']} hrs/mo", "illustrative estimate for a 40-room hotel")]
    st.markdown('<div class="dq-grid">' + "".join(
        f'<div class="kpi"><div class="kpi-label">{t}</div><div class="kpi-value">{v}</div>'
        f'<div class="kpi-deltas"><span class="flat">{d}</span></div></div>' for t, v, d in tiles) + "</div>",
        unsafe_allow_html=True)
    st.caption("Counts are computed from the sample raw files below; in a real engagement the same checks run on every "
               "refresh. Hours saved is an illustrative estimate, not a measured figure.")

    st.markdown('<div class="section-title">Before: what the raw files look like</div>',
                unsafe_allow_html=True)
    raw = D["raw"]
    t1, t2, t3 = st.tabs(["PMS export", "Booking.com extranet CSV", "Budget spreadsheet"])
    with t1:
        st.dataframe(raw["pms_export_sample"], hide_index=True, width="stretch", height=300)
        st.caption("Issues: three date formats, free-text nights (\"5 nts\"), inconsistent room codes (OVK / ocean vw / "
                   "OV-KING), source codes, a duplicated booking and a blank row, rates stored as text.")
    with t2:
        st.dataframe(raw["ota_bookingcom_sample"], hide_index=True, width="stretch")
        st.caption("Issues: long-form dates, \"USD 1 234.50\" prices with space separators, missing commission amounts, "
                   "status codes that differ from the PMS, and confirmation numbers that must be matched to PMS records.")
    with t3:
        st.dataframe(raw["budget_spreadsheet_sample"], hide_index=True, width="stretch")
        st.caption("Issues: months as columns, percentages and \"k\" suffixes stored as text, notes mixed into the data.")

    st.markdown('<div class="section-title">After: the clean model</div>',
                unsafe_allow_html=True)
    model = pd.DataFrame([
        ("fact_stay_nights", "1 row per occupied room per night", len(D["nights"]), "rate, ancillary spend, channel, segment, market, lead time, commission"),
        ("fact_reservations", "1 row per booking", len(D["res"]), "status (stayed / cancelled / no-show), dates, LOS, repeat guest"),
        ("fact_costs_daily", "1 row per property per day", len(D["costs"]), "payroll, electricity (kWh & $), water, F&B cost, maintenance"),
        ("fact_budget", "1 row per property per month", len(D["budget"]), "room nights, revenue, GOP targets"),
        ("fact_compset", "1 row per property per day", len(D["comp"]), "indicative competitor ADR"),
        ("fact_reviews (+ topics)", "1 row per review / topic", len(D["reviews"]), "platform, score, topic sentiment"),
        ("dim_rooms", "1 row per room type", len(D["inv"]), "inventory by property")],
        columns=["Table", "Grain", "Rows", "Key fields"])
    st.dataframe(model, hide_index=True, width="stretch", height=(len(model) + 1) * 35 + 3, column_config={"Key fields": st.column_config.TextColumn(width="large")})
    c1, c2 = st.columns([3, 2], gap="medium")
    with c2:
        st.markdown("""<div class="calc"><div class="kpi-label">What gets automated</div><ul style="margin:6px 0 0;padding-left:18px;font-size:.86rem;line-height:1.6">
<li>Nightly pull of PMS &amp; OTA exports (API or scheduled CSV drop)</li>
<li>Mapping tables for room types, channels &amp; markets</li>
<li>Duplicate &amp; cancellation reconciliation across sources</li>
<li>Budget unpivoted to a daily grain for any date range</li>
<li>Data-quality checks (e.g. room nights ≤ rooms available)</li>
<li>Monthly owner report generated automatically</li></ul></div>""", unsafe_allow_html=True)
        st.download_button("Download the full demo dataset (Excel)", (core.DATA_DIR / "alustrian_palace_demo_data.xlsx").read_bytes(),
                           file_name="alustrian_palace_demo_data.xlsx", width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c1:
        st.markdown('<div class="note" style="margin-top:8px">Sample of the cleaned stay-night table:</div>', unsafe_allow_html=True)
        sample = D["nights"][D["nights"].stay_date.between("2026-10-10", "2026-10-11")].head(8)
        st.dataframe(sample[["stay_date", "room_type", "channel", "segment", "source_market", "room_revenue",
                             "ancillary_revenue", "commission"]], hide_index=True, width="stretch",
                     column_config={"stay_date": st.column_config.DateColumn("stay_date", format="YYYY-MM-DD")})


# ------------------------------------------------------------------ owner report (sidebar, every page)
with st.sidebar:
    st.markdown("### Owner report")
    months = pd.date_range(DATA_START, AS_OF, freq="MS")[::-1]
    default_m = 1 if AS_OF.day < 28 else 0
    m_sel = st.selectbox("Month", months, index=default_m, format_func=lambda d: d.strftime("%B %Y") +
                         (" (to date)" if d.month == AS_OF.month and d.year == AS_OF.year else ""), key="report_month")

    @st.cache_data(show_spinner=False)
    def _pdf(p, m):
        return report.pdf_summary(D, list(p), m)

    @st.cache_data(show_spinner=False)
    def _xlsx(p, m):
        return report.excel_summary(D, list(p), m)

    st.download_button("⬇ Download monthly summary (PDF)", _pdf(tuple(props), m_sel), width="stretch",
                       file_name=f"alustrian_monthly_summary_{m_sel:%Y_%m}.pdf", mime="application/pdf")
    st.download_button("⬇ Monthly summary (Excel)", _xlsx(tuple(props), m_sel), width="stretch",
                       file_name=f"alustrian_monthly_summary_{m_sel:%Y_%m}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Demo data — fictional property. USD throughout.")

{"overview": page_overview, "pricing": page_pricing, "season": page_season, "channels": page_channels,
 "costs": page_costs, "reputation": page_reputation, "built": page_built}[page]()
st.markdown(ui.footer(), unsafe_allow_html=True)

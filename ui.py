"""Look & feel: CSS, wordmark, KPI cards, Plotly template."""
from __future__ import annotations

import html

import numpy as np
import plotly.graph_objects as go
import plotly.io as pio

NAVY, TEAL, GOLD, SAND, CORAL = "#12304A", "#1B7F86", "#C8A464", "#E9DCC4", "#E4735F"
SEA, SLATE, MAUVE, INK, MUTED = "#7FBFB8", "#8A9BAE", "#B5838D", "#1F2A37", "#6B7785"
PALETTE = [NAVY, TEAL, GOLD, CORAL, SEA, SLATE, MAUVE]
CHANNEL_COLORS = {"Direct website": TEAL, "Booking.com": NAVY, "Expedia": GOLD, "Airbnb": CORAL,
                  "Travel agents/wholesalers": SLATE, "Walk-in": SEA}
SEASON_COLORS = {"High season": TEAL, "Shoulder": GOLD, "Low / hurricane": CORAL}

pio.templates["alustrian"] = go.layout.Template(layout=dict(
    font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", size=12, color=INK),
    colorway=PALETTE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False, linecolor="#DCD5C8", tickcolor="#DCD5C8", ticks="outside", ticklen=4,
               title=dict(font=dict(size=11, color=MUTED))),
    yaxis=dict(gridcolor="#EFEAE1", zeroline=False, linecolor="rgba(0,0,0,0)",
               title=dict(font=dict(size=11, color=MUTED))),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, font=dict(size=11),
                bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=8, r=8, t=34, b=8), hoverlabel=dict(font=dict(family="Inter"), bgcolor="white"),
    bargap=0.28, height=330))
pio.templates.default = "plotly_white+alustrian"
PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap');
html, body, .stApp, .stMarkdown, [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"], button, input, select, textarea,
[data-baseweb="select"] *, [data-testid="stCaptionContainer"] { font-family: 'Inter', sans-serif; }
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }
h1, h2, h3, h4, .serif { font-family: 'Playfair Display', Georgia, serif !important; color: #12304A; letter-spacing: .2px; }
.block-container { padding-top: 4.5rem; padding-bottom: 2rem; max-width: 1400px; }
[data-testid="stHeader"] { background: rgba(251,249,245,0.85); backdrop-filter: blur(6px); }
[data-testid="stSidebar"] { background: #F3EEE5; border-right: 1px solid #E6DECF; }
[data-testid="stSidebar"] h3 { font-size: 1.05rem; margin-top: .4rem; }
.ap-header { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;
  padding: 10px 4px 14px; border-bottom: 1px solid #E6DECF; margin-bottom: 14px; }
.ap-brand { display:flex; align-items:center; gap:14px; }
.ap-word { font-family:'Playfair Display', serif; font-size: 1.75rem; font-weight: 600; letter-spacing: .32em;
  color:#12304A; line-height:1; }
.ap-sub { font-size:.74rem; color:#6B7785; letter-spacing:.08em; text-transform:uppercase; margin-top:6px; }
.ap-badge { background:#FFF4EF; color:#B4513F; border:1px solid #F2C9BC; border-radius:999px;
  padding:5px 12px; font-size:.72rem; font-weight:600; letter-spacing:.06em; text-transform:uppercase; white-space:nowrap; }
.ap-page-title { font-family:'Playfair Display', serif; font-size:1.55rem; color:#12304A; margin:2px 0 2px; }
.ap-page-sub { color:#6B7785; font-size:.86rem; margin-bottom: 12px; }
.kpi-grid { display:grid; grid-template-columns: repeat(var(--n, 5), minmax(0, 1fr)); gap:14px; margin: 4px 0 18px; }
.kpi { background:#FFFFFF; border:1px solid #ECE5D8; border-radius:14px; padding:14px 16px 10px;
  box-shadow: 0 1px 2px rgba(18,48,74,.04), 0 6px 18px rgba(18,48,74,.05); position:relative; overflow:hidden; }
.kpi { overflow:visible; } .kpi-label { overflow:visible !important; }
.tip { cursor:help; color:#A9B3BE; font-size:.8rem; position:relative; text-transform:none; letter-spacing:0; }
.tip:hover::after { content: attr(data-tip); position:absolute; left:-10px; top:20px; z-index:50; width:230px;
  white-space:normal; background:#12304A; color:#F4EFE6; font-size:.74rem; font-weight:400; line-height:1.35;
  padding:8px 10px; border-radius:8px; box-shadow:0 6px 18px rgba(0,0,0,.18); }
.partial-note { font-size:.72rem; color:#6B7785; }
.dq-grid { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:12px; margin:6px 0 14px; }
@media (max-width: 760px) { .dq-grid { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.kpi:before { content:""; position:absolute; left:0; top:0; bottom:0; width:4px; border-radius:14px 0 0 14px; background:linear-gradient(#1B7F86,#C8A464); }
.kpi-label { font-size:.68rem; color:#6B7785; letter-spacing:.1em; text-transform:uppercase; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.kpi-value { font-family:'Inter', sans-serif; font-size:1.55rem; white-space:nowrap; font-weight:600; color:#12304A; margin:4px 0 4px;
  font-variant-numeric: tabular-nums; letter-spacing:-.01em; }
.kpi-deltas { display:flex; gap:10px; flex-wrap:wrap; font-size:.74rem; color:#6B7785; }
.kpi-deltas b { font-weight:600; }
.up { color:#1B7F86; } .down { color:#D0563F; } .flat { color:#6B7785; }
.kpi svg { display:block; margin-top:6px; }
.chart-title { font-family:'Playfair Display', serif; font-size:1.08rem; color:#12304A; margin:0 0 0; font-weight:600; }
.chart-sub { font-size:.76rem; color:#6B7785; margin: 1px 0 0; }
div[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .chart-title) {
  background:#FFFFFF; border-radius:14px; border-color:#ECE5D8 !important;
  box-shadow: 0 1px 2px rgba(18,48,74,.03), 0 6px 18px rgba(18,48,74,.04); }
.section-title { font-family:'Playfair Display', serif; font-size:1.25rem; color:#12304A; font-weight:600; margin:10px 0 8px; }
.insights { background: linear-gradient(135deg, #12304A 0%, #1B5E6E 100%); color:#F4EFE6; border-radius:16px;
  padding:18px 22px; margin: 0 0 18px; box-shadow:0 8px 24px rgba(18,48,74,.18); }
.insights h4 { color:#E9DCC4 !important; margin:0 0 8px; font-size:1.15rem; }
.insights ul { margin:0; padding-left:18px; } .insights li { margin:5px 0; font-size:.9rem; line-height:1.45; }
.insights b { color:#FFFFFF; } .insights .gold { color:#E9C98B; }
.note { font-size:.75rem; color:#6B7785; }
.calc { background:#FFFFFF; border:1px solid #ECE5D8; border-radius:14px; padding:14px 16px; }
.calc .big { font-size:1.7rem; font-weight:600; color:#1B7F86; font-variant-numeric: tabular-nums; }
.pill { display:inline-block; background:#F3EEE5; color:#12304A; border-radius:999px; padding:3px 10px;
  font-size:.72rem; margin:2px 4px 2px 0; }
.flow { display:grid; grid-template-columns: 1fr auto 1fr auto 1fr; gap:10px; align-items:stretch; margin:8px 0 16px; }
.flow .box { background:#FFFFFF; border:1px solid #ECE5D8; border-radius:14px; padding:14px 16px; font-size:.84rem; }
.flow .box h5 { font-family:'Playfair Display', serif; color:#12304A; margin:0 0 6px; font-size:1.02rem; }
.flow .arrow { align-self:center; color:#C8A464; font-size:1.8rem; }
.flow .messy { border-left:4px solid #E4735F; } .flow .clean { border-left:4px solid #1B7F86; } .flow .dash { border-left:4px solid #C8A464; }
.ap-footer { margin-top:28px; padding:16px 4px 6px; border-top:1px solid #E6DECF; display:flex; justify-content:space-between;
  flex-wrap:wrap; gap:8px; color:#6B7785; font-size:.78rem; }
.ap-footer .who { font-family:'Playfair Display', serif; color:#12304A; font-size:.95rem; }
.ap-footer .placeholder { background:#FFF4EF; border:1px dashed #E4735F; color:#B4513F; border-radius:6px; padding:2px 8px; }
@media (max-width: 1100px) { .kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 760px) {
  .block-container { padding-top: 4.2rem; padding-left: .9rem; padding-right: .9rem; }
  .ap-word { font-size:1.2rem; letter-spacing:.16em; line-height:1.25; } .kpi-value { font-size:1.3rem; }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap:10px; }
  .flow { grid-template-columns: 1fr; } .flow .arrow { transform: rotate(90deg); justify-self:center; }
}
</style>
"""

LOGO_SVG = """<svg width="52" height="52" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-label="Alustrian Palace">
<circle cx="32" cy="32" r="30" fill="#12304A"/><circle cx="32" cy="32" r="26.5" fill="none" stroke="#C8A464" stroke-width="1.2"/>
<path d="M18 46 V30 a14 14 0 0 1 28 0 V46" fill="none" stroke="#C8A464" stroke-width="2.2"/>
<path d="M24 46 V31 a8 8 0 0 1 16 0 V46" fill="none" stroke="#E9DCC4" stroke-width="1.4"/>
<path d="M14 46 H50" stroke="#C8A464" stroke-width="2"/>
<path d="M32 15 l2.2 4.4 4.8.7-3.5 3.4.8 4.8-4.3-2.3-4.3 2.3.8-4.8-3.5-3.4 4.8-.7z" fill="#C8A464"/>
<path d="M19 50 q6.5 -3 13 0 t13 0" fill="none" stroke="#7FBFB8" stroke-width="1.6"/></svg>"""


def header(location: str, as_of) -> str:
    return (f'<div class="ap-header"><div class="ap-brand">{LOGO_SVG}<div><div class="ap-word">ALUSTRIAN PALACE</div>'
            f'<div class="ap-sub">{html.escape(location)} · data to {as_of:%d %b %Y}</div></div></div>'
            f'<div class="ap-badge">Demo data — fictional property</div></div>')


def footer() -> str:
    return ('<div class="ap-footer"><div><span class="who">Built by Tramal Whitehall · Data &amp; Revenue Analytics</span><br>'
            'Power BI &amp; web dashboards · data cleaning &amp; reporting automation · pricing &amp; revenue analysis</div>'
            '<div><span class="placeholder">[Contact placeholder — business name, email &amp; website TBC]</span><br>'
            'All figures are randomly generated demo data for a fictional property.</div></div>')


def page_title(title: str, sub: str) -> str:
    return f'<div class="ap-page-title">{html.escape(title)}</div><div class="ap-page-sub">{sub}</div>'


def chart_title(title: str, sub: str = "") -> str:
    s = f'<div class="chart-sub">{sub}</div>' if sub else ""
    return f'<div class="chart-title">{html.escape(title)}</div>{s}'


def sparkline(values, color=TEAL, w=150, h=30) -> str:
    v = np.asarray([x for x in values if x is not None and not np.isnan(x)], float)
    if len(v) < 2:
        return ""
    lo, hi = v.min(), v.max()
    rng = hi - lo or 1
    xs = np.linspace(2, w - 2, len(v))
    ys = h - 3 - (v - lo) / rng * (h - 6)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"2,{h} " + pts + f" {w - 2},{h}"
    return (f'<svg width="100%" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<polygon points="{area}" fill="{color}" opacity="0.10"/>'
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.6" stroke-linejoin="round"/>'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="2.4" fill="{color}"/></svg>')


def delta_html(cur, ref, kind="pct", label="vs LY", good_up=True) -> str:
    if ref is None or cur is None or (isinstance(ref, float) and np.isnan(ref)) or ref == 0:
        return f'<span class="flat">– {label}</span>'
    if kind == "pts":
        d = (cur - ref) * 100
        txt = f"{abs(d):.1f} pts"
    elif ref < 0 or abs(cur / ref - 1) > 5:          # % change meaningless on a tiny/negative base
        d = cur - ref
        txt = f"${abs(d):,.0f}"
    else:
        d = cur / ref - 1
        txt = f"{abs(d):.1%}"
    cls = "flat" if abs(d) < 1e-9 else ("up" if (d > 0) == good_up else "down")
    arrow = "▲" if d > 0 else ("▼" if d < 0 else "■")
    return f'<span class="{cls}"><b>{arrow} {txt}</b> {label}</span>'


DEFS = {
    "Occupancy": "Room nights sold ÷ rooms available in the period.",
    "ADR": "Average daily rate: room revenue ÷ room nights sold.",
    "RevPAR": "Revenue per available room: room revenue ÷ rooms available (= ADR × occupancy).",
    "GOPPAR": "Gross operating profit ÷ rooms available.",
    "GOP": "Gross operating profit: total revenue minus operating costs (before rent, fees, tax).",
    "GOP margin": "Gross operating profit as a share of total revenue.",
    "Net ADR": "ADR after channel commission / distribution cost is deducted.",
    "CPOR": "Cost per occupied room: total operating costs ÷ room nights sold.",
    "Total revenue": "Room revenue plus ancillary (F&B, spa, excursions, transfers).",
    "Comp-set index": "Our ADR ÷ comp-set ADR × 100; above 100 = priced above the market.",
}


def kpi_cards(cards: list[dict]) -> str:
    out = [f'<div class="kpi-grid" style="--n:{len(cards)}">']
    for c in cards:
        tip = DEFS.get(c["label"])
        tip_html = f' <span class="tip" data-tip="{html.escape(tip)}" title="{html.escape(tip)}">ⓘ</span>' if tip else ""
        out.append(f'<div class="kpi"><div class="kpi-label">{html.escape(c["label"])}{tip_html}</div>'
                   f'<div class="kpi-value">{c["value"]}</div><div class="kpi-deltas">{"".join(c.get("deltas", []))}</div>'
                   f'{c.get("spark", "")}</div>')
    out.append("</div>")
    return "".join(out)


def insights_box(items: list[str], title="Key insights", actions: list[str] | None = None) -> str:
    import re
    bold = re.compile(r"\*\*(.+?)\*\*")
    lis = "".join("<li>" + bold.sub(r"<b>\1</b>", html.escape(i)) + "</li>" for i in items)
    act = ""
    if actions:
        als = "".join("<li>" + bold.sub(r"<b>\1</b>", html.escape(a)) + "</li>" for a in actions)
        act = f'<h4 style="margin-top:14px">➜ Recommended actions</h4><ul>{als}</ul>'
    return f'<div class="insights"><h4>✦ {html.escape(title)}</h4><ul>{lis}</ul>{act}</div>'

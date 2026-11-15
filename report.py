"""Monthly owner summary exports: PDF (fpdf2) and Excel."""
from __future__ import annotations

import io
import re

import numpy as np
import pandas as pd
from fpdf import FPDF

import core

_REPL = {"—": "-", "–": "-", "·": "-", "’": "'", "“": '"', "”": '"', "▲": "+", "▼": "-", "✦": "*", "≈": "~", "×": "x"}


def _t(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", str(s))
    for a, b in _REPL.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def month_bundle(data, properties: list, month: pd.Timestamp) -> dict:
    ms = month.replace(day=1)
    me = min(ms + pd.offsets.MonthEnd(0), data["as_of"])
    f = core.Filters(properties, ms, me)
    k = core.kpis(data, f)
    ly = core.kpis(data, f.shifted()) if core.covered(data, f.shifted()) else None
    b = core.budget_kpis(data, f)
    n = core.nights(data, f)
    mix = core.channel_mix(n)
    daily = core.period_table(data, f, "D")
    return dict(f=f, k=k, ly=ly, b=b, mix=mix, daily=daily, ins=core.insights(data, f, k, ly, b),
                recs=core.recommendations(data, f, k, ly), ms=ms, me=me)


HEADLINE = [("Occupancy", "occ", "pct"), ("ADR", "adr", "usd"), ("RevPAR", "revpar", "usd"),
            ("Total revenue", "total", "usd"), ("GOP margin", "gop_margin", "pct")]


def _fmt(v, kind):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    if kind == "pct":
        return f"{v:.1%}"
    sign = "-" if v < 0 else ""
    if abs(v) >= 1e6:
        return f"{sign}${abs(v) / 1e6:.2f}M"
    return f"{sign}${abs(v):,.0f}"


def _delta(k, ref, key, kind):
    if not ref or ref.get(key) in (None, 0):
        return "-"
    if kind == "pct":
        return f"{(k[key] - ref[key]) * 100:+.1f} pts"
    if ref[key] <= 0:
        return f"{'+' if k[key] >= ref[key] else '-'}${abs(k[key] - ref[key]):,.0f}"
    return f"{k[key] / ref[key] - 1:+.1%}"


def headline_rows(B):
    return [[label, _fmt(B["k"][key], kind), _delta(B["k"], B["ly"], key, kind), _delta(B["k"], B["b"], key, kind)]
            for label, key, kind in HEADLINE]


def _rows(B):
    k, ly, b = B["k"], B["ly"], B["b"]
    spec = [("Occupancy", "occ", "pct"), ("ADR", "adr", "usd"), ("RevPAR", "revpar", "usd"),
            ("Room revenue", "room_rev", "usd"), ("Ancillary revenue", "anc", "usd"), ("Total revenue", "total", "usd"),
            ("GOP", "gop", "usd"), ("GOP margin", "gop_margin", "pct"), ("GOPPAR", "goppar", "usd")]
    out = []
    for label, key, kind in spec:
        def f(v):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return "-"
            if kind == "pct":
                return f"{v:.1%}"
            sign = "-" if v < 0 else ""
            return f"{sign}${abs(v):,.0f}" if abs(v) >= 1000 else f"{sign}${abs(v):,.2f}"

        def d(ref):
            if not ref or ref.get(key) in (None, 0):
                return "-"
            if kind == "pct":
                return f"{(k[key] - ref[key]) * 100:+.1f} pts"
            if ref[key] <= 0 or abs(k[key] / ref[key] - 1) > 5:   # % change meaningless on tiny/negative base
                diff = k[key] - ref[key]
                return ("+" if diff >= 0 else "-") + f"${abs(diff):,.0f}"
            return f"{k[key] / ref[key] - 1:+.1%}"
        out.append([label, f(k[key]), f(ly[key]) if ly else "-", d(ly), f(b[key]) if b else "-", d(b)])
    return out


def pdf_summary(data, properties: list, month: pd.Timestamp) -> bytes:
    B = month_bundle(data, properties, month)
    navy, teal, gold, sand, coral, ink, muted = ((18, 48, 74), (27, 127, 134), (200, 164, 100), (243, 238, 229),
                                                 (208, 86, 63), (31, 42, 55), (107, 119, 133))
    period = f"{B['ms']:%B %Y}" + (f" (to {B['me']:%d %b})" if B["me"] < B["ms"] + pd.offsets.MonthEnd(0) else "")
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(False)

    def header(subtitle):
        pdf.add_page()
        pdf.set_fill_color(*navy)
        pdf.rect(0, 0, 210, 32, "F")
        pdf.set_text_color(233, 220, 196)
        pdf.set_font("Times", "B", 21)
        pdf.set_xy(14, 7)
        pdf.cell(0, 10, "A L U S T R I A N   P A L A C E")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(14, 19)
        pdf.cell(0, 6, _t(f"{subtitle} - {period} - {' + '.join(properties)}"))
        pdf.set_xy(146, 7)
        pdf.set_fill_color(228, 115, 95)
        pdf.set_font("Helvetica", "B", 7.5)
        pdf.cell(50, 6, "DEMO DATA - FICTIONAL PROPERTY", align="C", fill=True)
        pdf.set_y(40)

    def footer(page):
        pdf.set_draw_color(230, 224, 212)
        pdf.line(14, 279, 196, 279)
        pdf.set_xy(14, 281)
        pdf.set_font("Helvetica", "I", 7.2)
        pdf.set_text_color(*muted)
        pdf.multi_cell(182, 3.6, _t("Revenue is net of government accommodation tax and hotel service charge. Demo data for a "
                                    "fictional property - not real results.\nBuilt by Tramal Whitehall - Data & Revenue "
                                    f"Analytics - [contact placeholder]          Page {page} of 2"), align="C")

    def h2(txt, y=None):
        if y is not None:
            pdf.set_y(y)
        pdf.set_x(14)
        pdf.set_font("Times", "B", 14)
        pdf.set_text_color(*navy)
        pdf.cell(0, 7, txt)
        pdf.ln(9)

    def bullets(items, color):
        pdf.set_font("Helvetica", "", 9.6)
        for i, s_ in enumerate(items, 1):
            y = pdf.get_y()
            pdf.set_fill_color(*color)
            pdf.ellipse(15, y + 1.2, 4.2, 4.2, "F")
            pdf.set_xy(15, y + 1.3)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(255, 255, 255)
            pdf.cell(4.2, 4, str(i), align="C")
            pdf.set_font("Helvetica", "", 9.6)
            pdf.set_text_color(*ink)
            pdf.set_xy(22, y)
            pdf.multi_cell(172, 5.4, _t(s_))
            pdf.ln(2.5)

    # ---------------- page 1: one-page plain-English summary
    header("Monthly owner summary")
    pdf.set_x(14)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*ink)
    k = B["k"]
    pdf.multi_cell(182, 5.2, _t(
        f"In {period} the {'portfolio' if len(properties) > 1 else 'hotel'} sold {k['rn']:,} room nights at an average rate "
        f"of ${k['adr']:,.0f}, earning {_fmt(k['total'], 'usd')} in total revenue with a gross operating profit margin of "
        f"{k['gop_margin']:.1%}."))
    pdf.ln(4)
    h2("The month at a glance")
    x0, y0, w, h, gap = 14, pdf.get_y(), 34.4, 30, 2.5
    for i, (label, val, dly, dbud) in enumerate(headline_rows(B)):
        x = x0 + i * (w + gap)
        pdf.set_fill_color(250, 248, 244)
        pdf.set_draw_color(230, 224, 212)
        pdf.rect(x, y0, w, h, "DF")
        pdf.set_fill_color(*teal)
        pdf.rect(x, y0, 1.2, h, "F")
        pdf.set_xy(x + 3, y0 + 3)
        pdf.set_font("Helvetica", "B", 6.8)
        pdf.set_text_color(*muted)
        pdf.cell(w - 4, 4, label.upper())
        pdf.set_xy(x + 3, y0 + 8.5)
        pdf.set_font("Helvetica", "B", 13.5)
        pdf.set_text_color(*navy)
        pdf.cell(w - 4, 7, _t(val))
        for j, (lab, d) in enumerate((("vs LY", dly), ("vs budget", dbud))):
            pdf.set_xy(x + 3, y0 + 17.5 + j * 5)
            pdf.set_font("Helvetica", "B", 7.6)
            pdf.set_text_color(*(teal if d.startswith("+") else coral if d.startswith("-") and d != "-" else muted))
            pdf.cell(w - 4, 4, _t(f"{d}  {lab}"))
    pdf.set_y(y0 + h + 8)
    h2("What happened")
    bullets(B["ins"][:3], teal)
    pdf.ln(2)
    h2("Recommended actions")
    bullets(B["recs"][:3], gold)
    footer(1)

    # ---------------- page 2: detail & charts
    header("Detail & charts")
    h2("All KPIs")
    widths = [44, 28, 28, 22, 28, 22]
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*sand)
    pdf.set_text_color(*ink)
    pdf.set_x(14)
    for w_, h_ in zip(widths, ["Metric", "Actual", "Last year", "vs LY", "Budget", "vs budget"]):
        pdf.cell(w_, 7, h_, fill=True, align="L" if h_ == "Metric" else "R")
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for i, row in enumerate(_rows(B)):
        pdf.set_x(14)
        pdf.set_fill_color(*(255, 255, 255) if i % 2 == 0 else (250, 248, 244))
        for j, (w_, v) in enumerate(zip(widths, row)):
            pdf.set_text_color(*(teal if j in (3, 5) and v.startswith("+") else coral if j in (3, 5) and v.startswith("-") and v != "-" else ink))
            pdf.cell(w_, 6.3, _t(v), fill=True, align="L" if j == 0 else "R")
        pdf.ln(6.3)
    pdf.ln(3)
    h2("Daily occupancy")
    d = B["daily"]
    x0, y0, cw, ch = 16, pdf.get_y(), 178, 32
    pdf.set_draw_color(220, 213, 200)
    pdf.line(x0, y0 + ch, x0 + cw, y0 + ch)
    if len(d):
        bw = cw / len(d)
        for i, (dt, r) in enumerate(d.iterrows()):
            hgt = ch * float(min(r["occ"], 1))
            pdf.set_fill_color(*(teal if r["occ"] >= 0.7 else gold))
            pdf.rect(x0 + i * bw + 0.3, y0 + ch - hgt, max(bw - 0.6, 0.3), hgt, "F")
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(*muted)
        for i, dt in enumerate(d.index):
            if i % 5 == 0:
                pdf.set_xy(x0 + i * bw - 2, y0 + ch + 0.5)
                pdf.cell(8, 3, f"{dt:%d}")
        pdf.set_xy(x0, y0 + ch + 4)
        pdf.cell(0, 3, "teal = 70%+ occupancy, gold = below 70%")
    pdf.set_y(y0 + ch + 10)
    h2("Channel mix")
    cw2 = [56, 26, 32, 26, 26, 26]
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_fill_color(*sand)
    pdf.set_text_color(*ink)
    pdf.set_x(14)
    for w_, h_ in zip(cw2, ["Channel", "Room nights", "Room revenue", "Share", "ADR", "Net ADR"]):
        pdf.cell(w_, 7, h_, fill=True, align="L" if h_ == "Channel" else "R")
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    for ch_name, r in B["mix"].iterrows():
        pdf.set_x(14)
        for j, (w_, v) in enumerate(zip(cw2, [ch_name, f"{r.rn:,.0f}", f"${r.revenue:,.0f}", f"{r.share_rn:.0%}",
                                              f"${r.adr:,.0f}", f"${r.net_adr:,.0f}"])):
            pdf.cell(w_, 6, _t(v), align="L" if j == 0 else "R")
        pdf.ln(6)
    if len(B["ins"]) > 3:
        pdf.ln(3)
        h2("More insights")
        bullets(B["ins"][3:], teal)
    footer(2)
    return bytes(pdf.output())


def excel_summary(data, properties: list, month: pd.Timestamp) -> bytes:
    B = month_bundle(data, properties, month)
    buf = io.BytesIO()
    kp = pd.DataFrame(_rows(B), columns=["Metric", "Actual", "Last year", "vs LY", "Budget", "vs budget"])
    daily = B["daily"][["rn", "avail", "occ", "adr", "revpar", "room_rev", "anc", "total_all", "cost", "gop"]].copy()
    daily.columns = ["Room nights", "Rooms available", "Occupancy", "ADR", "RevPAR", "Room revenue",
                     "Ancillary revenue", "Total revenue", "Costs", "GOP"]
    daily.index.name = "Date"
    mix = B["mix"].rename(columns={"rn": "Room nights", "revenue": "Room revenue", "commission": "Commission",
                                   "adr": "ADR", "net_adr": "Net ADR", "share_rn": "Share of nights",
                                   "share_rev": "Share of revenue"})
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        wb_rows = [["Alustrian Palace - monthly owner summary", "", "", ""],
                   [f"{B['ms']:%B %Y} - {' + '.join(properties)}", "", "", ""],
                   ["DEMO DATA - FICTIONAL PROPERTY. Revenue net of government accommodation tax and hotel service charge.", "", "", ""],
                   ["", "", "", ""], ["KPI", "Actual", "vs last year", "vs budget"]] + headline_rows(B) + \
                  [["", "", "", ""], ["What happened", "", "", ""]] + [[f"{i}. {_t(x)}", "", "", ""] for i, x in enumerate(B["ins"][:3], 1)] + \
                  [["", "", "", ""], ["Recommended actions", "", "", ""]] + [[f"{i}. {_t(x)}", "", "", ""] for i, x in enumerate(B["recs"][:3], 1)]
        pd.DataFrame(wb_rows).to_excel(xw, sheet_name="Summary", index=False, header=False)
        kp.to_excel(xw, sheet_name="KPI detail", index=False)
        daily.round(2).to_excel(xw, sheet_name="Daily")
        mix.round(3).to_excel(xw, sheet_name="Channels")
        from openpyxl.styles import Alignment, Font, PatternFill
        for ws in xw.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = 18
            ws.column_dimensions["A"].width = 26
        ws = xw.book["Summary"]
        ws.column_dimensions["A"].width = 110
        ws["A1"].font = Font(name="Georgia", size=16, bold=True, color="12304A")
        ws["A3"].font = Font(italic=True, color="B4513F")
        for row in ws.iter_rows():
            for c in row:
                if c.value in ("KPI", "What happened", "Recommended actions") or (c.row == 5 and c.value):
                    c.font = Font(bold=True, color="12304A")
                    c.fill = PatternFill("solid", fgColor="F3EEE5")
                if c.column == 1 and isinstance(c.value, str) and c.value[:2] in ("1.", "2.", "3."):
                    c.alignment = Alignment(wrap_text=True, vertical="top")
    return buf.getvalue()

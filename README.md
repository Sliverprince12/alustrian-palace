# Alustrian Palace — Boutique Hotel Performance Dashboard (demo)

A showcase dashboard for **independent boutique hotels, villa managers and short-term-rental operators**
(Turks & Caicos, Barbados and the wider Caribbean). Built with **Python · Streamlit · Plotly · pandas**.

> **Demo data — fictional property.** *Alustrian Palace* (40 rooms, Grace Bay, Turks & Caicos) and its sister
> property *Alustrian Villas* (10 units, Barbados) do not exist. Every number is randomly generated
> (fixed seed) by `generate_data.py`. All amounts are in USD.

Built by **Tramal Whitehall · Data & Revenue Analytics** — *[contact placeholder: business name, email & website TBC]*

**Same model, your choice of front end:** the cleaned data model and these visuals can be delivered in **Power BI**
or as a hosted **web app** like this one.

Revenue is shown **net of government accommodation tax and hotel service charge**.

## Pages
| Page | What's on it |
|---|---|
| Executive overview | Occupancy, ADR, RevPAR, total revenue, GOPPAR vs last year **and** budget with sparklines and hover definitions; auto-generated *Key insights* + *Recommended actions*; revenue vs LY/budget; revenue mix; occupancy & ADR; RevPAR by room type |
| Pricing & revenue | ADR by room type × day of week, booking lead time, on-the-books pace vs last year, rate-vs-occupancy scatter, comp-set ADR index, **what-if pricing** (rate change → occupancy via price elasticity → RevPAR) |
| Seasonality & forecast | Monthly occupancy & ADR heatmaps with season bands, 90-day occupancy forecast with 80% band, season scorecard |
| Channels & guests | Revenue / room nights by channel, gross vs net ADR, direct-share trend, **commission-savings calculator**, guest segments, source markets by season, length of stay, repeat rate |
| Costs & profitability | GOP, margin, CPOR, utilities (electricity spotlight), F&B cost %, ancillary revenue per occupied room, mini P&L |
| Reputation & operations | Review score by platform, topic sentiment, cancellation & no-show rates |
| How it's built | Data-quality scorecard (computed from the raw samples; hours saved is illustrative), messy raw inputs (PMS export, Booking.com CSV, budget sheet) → clean star-schema model → dashboard |

Sidebar: property selector (incl. portfolio roll-up), date presets (Last 12 months, YTD, MTD, Custom), compare vs last
year / budget, room type, channel, segment, source market, season, day-of-week filters, and a **monthly owner summary**
download: PDF page 1 is a one-page plain-English summary (5 KPIs, 3 insights, 3 recommended actions), page 2 has
the full KPI table and charts; the Excel file has a matching Summary sheet. Part-months are shown faded/hatched in
monthly bar charts, and the fictional Sep 2025 storm closure is annotated where it falls in range. Pages can be linked directly with `?page=pricing` (overview, pricing, season, channels, costs,
reputation, built).

## Run it locally
```bash
cd alustrian-palace-dashboard
pip install -r requirements.txt     # Windows: py -m pip install -r requirements.txt
streamlit run app.py                # Windows: py -m streamlit run app.py
```
The app opens at http://localhost:8501. Optional:
```bash
python generate_data.py             # regenerate the demo data (same seed = same numbers)
python tests_consistency.py         # KPI maths & data consistency checks
```

## Deploy free on Streamlit Community Cloud
1. Create a GitHub repository (private is fine) and upload **everything in this folder**, keeping the `data/` and
   `.streamlit/` folders (`app.py` must sit at the top level of the repo).
   Tip: `.streamlit` starts with a dot, so it can be hidden; in the GitHub web uploader drag the folder in, or use
   *Add file → Create new file* and type `.streamlit/config.toml`, then paste its contents.
2. Go to https://share.streamlit.io → **Create app** → pick the repo, branch `main`, main file `app.py` → **Deploy**.
3. A few minutes later you'll get a `*.streamlit.app` link. Since this is demo data it is safe to make public.

## Files
```
app.py                 Streamlit app (layout, pages, charts)
core.py                Data loading, filters, KPI maths, forecast, insights
ui.py                  Styling: CSS, wordmark SVG, KPI cards, Plotly theme
report.py              Monthly owner summary (PDF via fpdf2, Excel via openpyxl)
generate_data.py       Fictional data generator (seed 20261115)
tests_consistency.py   Consistency checks
data/                  CSVs, alustrian_palace_demo_data.xlsx (all tables), raw_samples/ (messy inputs), meta.json
.streamlit/config.toml Theme
```

## Key assumptions (demo)
* Actuals run 1 Nov 2023 – 14 Nov 2026; later stay nights are bookings already on the books at 14 Nov 2026.
* Seasons: high Dec–Apr, shoulder May–Jul & Nov, low/hurricane Aug–Oct; festive peak 20 Dec – 3 Jan. Fictional
  storm in Sep 2025: Alustrian Palace closed 13–17 Sep, demand dipped and September cancellations spiked (~33%).
* Source markets: Palace (Grace Bay) ~80% US, ~10% Canada, ~7% UK+Europe, small Caribbean; Villas (Barbados) UK-led
  (~39% UK, ~29% US, ~8–10% Canada, rest Caribbean & Europe).
* Commissions: Booking.com 17%, Expedia 18%, Airbnb 15.5%, travel agents/wholesalers 25%, direct website ~7% (booking
  engine, card fees & direct marketing), walk-in 0%.
* Electricity ~$0.42/kWh (TCI) / ~$0.37 (Barbados) with summer AC load; F&B cost of sales ~31% (supplier spike Jul–Aug 2025).
* Palace GOP margin ~33% over the last 12 months (payroll ~28% of revenue).
* Budget = prior-year actual + ~1.5 pts occupancy and +5% ADR (first year: planning estimate). Budget and costs are
  property-level, so budget comparisons hide when room/channel/guest filters are on.
* Comp set is a simulated rate shop (indicative only), shown monthly with a 3-month rolling average. What-if pricing uses an illustrative constant price elasticity (default −0.8).
* Forecast = 50/50 blend of a pick-up model (on-the-books + last year's pick-up at the same lead time) and a
  trend-adjusted seasonal baseline; 80% band from historical residuals.

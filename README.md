# NSE Relative Rotation Graph Dashboard

A Python + Streamlit dashboard for Indian market rotation analysis using Relative Rotation Graphs (RRG).

## What it does

- Fetches NSE benchmark, sector indices, and stocks using `yfinance`
- Builds a sector-level RRG against `^NSEI`
- Lets you rotate a selected sector set against either `^NSEI` or an equal-weight sector basket
- Builds stock-level RRG inside each selected sector
- Adds a NIFTY stock search panel for single-stock RRG lookup
- Detects leading sectors and ranks top stock candidates
- Applies:
  - 200 DMA trend filter
  - breakout detection
  - quadrant-aware ranking
- Includes a Zerodha Kite Connect adapter layer with mock fallback
- Imports Zerodha holdings into a dashboard portfolio/watchlist context
- Saves Matplotlib RRG charts as PNG files
- Exports the buy list as PNG and PDF

## Supported sector indices

- `^NSEBANK`
- `^NSEIT`
- `^NSEAUTO`
- `^NSEFMCG`
- `^NSEPHARMA`

## Project layout

```text
nse_rrg_dashboard/
  app.py
  requirements.txt
  README.md
  rrg_dashboard/
    __init__.py
    config.py
    data_sources.py
    rrg.py
    charts.py
    screening.py
    kite_adapter.py
    exports.py
```

## Run locally

```powershell
Set-Location "C:\Users\BARIYAONE\OneDrive\Documents\Playground\nse_rrg_dashboard"
pip install -r requirements.txt
streamlit run app.py
```

## Zerodha integration

The dashboard can use Kite Connect metadata for operator context and future portfolio-linked rotation workflows.

Environment variables:

```powershell
$env:KITE_API_KEY="your_api_key"
$env:KITE_ACCESS_TOKEN="your_access_token"
```

If the SDK or credentials are unavailable, the app falls back to mock mode automatically.

### Holdings import

- Use the sidebar `Import Zerodha holdings` button
- Imported holdings are shown in the dashboard
- Those holdings also seed the watchlist selector automatically

## How stock selection works

### NIFTY stock search

- Use `NIFTY stock search in RRG` to inspect one stock directly against `^NSEI`
- This is useful when you want a quick quadrant view without changing the selected sector panel
- The card also shows:
  - current quadrant
  - 200 DMA filter
  - breakout flag

### Sector rotation comparison

- Use `Sector rotation comparison set` to limit the sector graph to chosen sectors
- Use `Sector rotation benchmark` to switch between:
  - `NIFTY 50`
  - `Equal-weight sector basket`

Top stock candidates are chosen from leading sectors using:

1. Sector must be in `Leading`
2. Stock quadrant preferred: `Leading` or `Improving`
3. Close must be above 200 DMA
4. Breakout flag boosts rank
5. RRG score favors stronger RS ratio and momentum

## Outputs

Saved under:

- [outputs](C:\Users\BARIYAONE\OneDrive\Documents\Playground\nse_rrg_dashboard\outputs)

Includes:

- `sector_rrg.png`
- sector stock RRG PNGs
- `exports/top_stocks_to_buy.png`
- `exports/top_stocks_to_buy.pdf`

## Easy universe editing

To add or change sector stocks, edit:

- [rrg_dashboard/config.py](C:\Users\BARIYAONE\OneDrive\Documents\Playground\nse_rrg_dashboard\rrg_dashboard\config.py)

The `SECTOR_STOCK_UNIVERSE` mapping is the main place to maintain stock lists.

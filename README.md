# Relative Rotation Graph Dashboard

A Streamlit dashboard rebuilt around a SharpeLy-style Relative Rotation Graph layout for Indian sector indices.

## Current focus

This version is intentionally narrow and screenshot-driven:

- one main RRG chart area
- benchmark selector
- tail-length control
- candle timeframe selector
- right-side watchlist rail
- sector/index-only workflow first

The earlier multi-panel candidate, export, and stock-ranking layout has been removed from the main experience.

## Covered indices

- `Nifty 50` benchmark: `^NSEI`
- `Nifty 500` benchmark: `^CRSLDX`
- tracked sector indices:
  - `^NSEBANK`
  - `^NSEIT`
  - `^NSEAUTO`
  - `^NSEFMCG`
  - `^NSEPHARMA`

## Run locally

```powershell
Set-Location "C:\Users\BARIYAONE\OneDrive\Documents\Playground\nse_rrg_dashboard"
.\.tools\python\python.exe -m streamlit run app.py
```

## Notes

- the chart uses the existing RRG engine and rescales the display to a 100-centered visual style to match the reference layout more closely
- the `Animate` control is kept in the UI shell, but real tail playback is not implemented yet
- the right rail currently prioritizes `Index` watchlists; `Stock` and `ETF` are intentionally deferred until the sector view is settled

# ARMO: do field-scale radars blink through the rain?

ES4304 (NTU) remote-sensing final project: a NASA ROSES-style proposal for **ARMO**, the Agricultural Rapid Moisture
Observatory, a two-satellite L-band radar mission with about 1.4-day revisit over the US.

Hourly ground truth from 120 NOAA U.S. Climate Reference Network stations (3,340 soil-moisture wetting events,
2025–2026) shows that wetting events last about 1.8 days, while the real 2026 Sentinel-1 + NISAR fleet captured only
about half of them. ARMO alone would capture 76 % of events (NISAR 38 %). The proposal is in two stages: a 2-year
retrieval study (US$ 217,882), then the mission (≈ US$ 150 M, inside the NASA Earth Venture cap).

- `report/ARMO_Proposal_ES4304.pdf`: the proposal
- `slides/ARMO_Slides_ES4304.pdf`: the presentation
- `market.pdf`: market and niche review
- `code/`: every analysis, figure, the report and the slides; run order and data sources in `code/README.md`
- `data/processed/`: result tables used by the report (raw downloads are re-created by scripts 01–07, 14, 23)
- `figures/`: all figures

All data are public. NISAR downloads need a free NASA Earthdata login and the Earth Engine scripts a free
non-commercial Earth Engine project; no credentials are stored in this repository.

The analysis code, documents and figures were produced with the help of an AI assistant (Claude, Anthropic) under the
team's direction.

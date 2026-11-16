# TEMU PLAYOFF PREDICTOR

An independent NFL playoff prediction model and mobile-friendly scenario explorer. Pick any remaining regular-season game, leave games open to simulate, and see playoff, division, bye and seed probabilities.

## Features

- All 32 teams and remaining 2026 games; ties supported.
- 10,000 seeded Monte Carlo seasons in a Web Worker.
- Opponent-adjusted point-margin ratings, prior-season regression, home field and rest.
- Baseline comparison, undo/redo, win/lose out, filters, impact sorting and rooting guide.
- Seed distributions, named local scenarios and shareable scenario links.
- Transparent model assumptions and a downloadable validation report.

## Historical evidence

Coefficients were fitted on 2010–2021. One chronological evaluation on 816 regular-season games from 2023–2025 produced:

| Metric | Original record-only model | Opponent-adjusted model |
|---|---:|---:|
| Brier score (lower is better) | 0.23060 | 0.22391 |
| Log loss (lower is better) | 0.65348 | 0.63878 |
| Winner accuracy | 62.7% | 63.1% |

The paired game-bootstrap Brier-difference interval includes zero. Games are correlated, so this interval can be optimistic. This is a modest observed improvement, not proof of a reliable edge. Playoff-event probabilities have not been calibrated through historical playoff backtesting.

The rating formula uses a fixed six-game ridge penalty toward 60% of the previous season's final rating, capped point margins of 28, and 0.97 weekly decay. Home adjustment in the rating fit is two points. Logistic coefficients are fitted to rating difference, home/neutral indicator and capped rest-day difference. Test years were not used to retune parameters.

## Limits

No injuries, quarterback availability, market odds or latent future rating uncertainty. Games are sampled independently with fixed current ratings. Future ties use a fixed 0.4% assumption. Synthetic future scores support deep point-based tiebreakers; their distribution is not calibrated. Net-touchdown criteria are unavailable; unresolved deep ties use seeded draws. This is not an official clinching engine. Sample 0% / 100% values do not prove elimination or clinching.

## Run and test

Serve `dist/` with any static HTTP server. No frontend dependencies or build step.

```sh
npm run check
pip install -r requirements.txt
OPENBLAS_NUM_THREADS=1 python scripts/build_data.py
```

The data builder downloads [nflverse/nfldata history](https://github.com/nflverse/nfldata), cross-checks the 2026 matchups against ESPN and uses ESPN’s current results and kickoff times, reconstructs pre-week ratings chronologically, repeats the fixed evaluation, validates all 272 scheduled games and writes `dist/data.json` and `dist/validation.json`. The builder records the source SHA-256. Teams that relocated are normalized across history.

## GitHub Pages

Settings → Pages → Source: **GitHub Actions**. `.github/workflows/pages.yml` validates and deploys `dist/` on pushes to main. `.github/workflows/refresh.yml` refreshes the bundled data and deploys at 11:23 UTC daily (06:23 EST / 07:23 EDT), with manual dispatch available. Scheduled workflow timing and source refresh timing are best-effort. The browser update button reloads the latest published snapshot and shows its timestamp.

Only static assets in `dist/` are published. Named scenarios stay in browser local storage; shared links contain picks and the selected team, without account data.

Independent project, not affiliated with the NFL or The New York Times. Team names identify matchups; visual design is original.

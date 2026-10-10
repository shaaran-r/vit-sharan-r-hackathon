# Signal & Stress demo dataset

This package contains the complete **synthetic dataset** used for the local
Signal & Stress demonstration. It is self-generated, seeded, reproducible demo
data. It is not supplied by S&P Global or Crisil and contains no real bank,
client, transaction, market-price, social-media, or publisher article records.

## Files

- `simulation/events.jsonl` — 12,000 fictional news/social-style records:
  6,000 `synthetic_news` and 6,000 `synthetic_social`. These are generated
  templates, not genuine publisher articles or posts.
- `simulation/portfolio.csv` — 2,400 fictional GBP holdings across loans,
  bonds, equities, derivatives and cash, linked to 240 fictional entities.
- `simulation/manifest.json` — dataset origin, random seed, record counts,
  generation timestamp, replay settings, baseline value and methodology.

## Synthetic event record

Each JSONL line is one JSON object. Common fields include:

| Field | Meaning |
| --- | --- |
| `event_id` | Stable synthetic record ID |
| `source` | `synthetic_news` or `synthetic_social` |
| `timestamp` | Synthetic event timestamp; not a publisher publication time |
| `text`, `body` | Generated fictional text |
| `entities` | Fictional entity IDs |
| `data_origin` | Always `synthetic` |
| `expected_event` | Generator-assigned event category, not an independently verified label |
| `topic`, `sector`, `region`, `language` | Synthetic metadata |
| `publisher` | Fictional publisher/channel name |
| `url` | Null; no article or social-post URL is represented |

## Synthetic portfolio record

`portfolio.csv` contains current-value notionals and simplified scenario
sensitivities. Important fields:

| Field | Meaning |
| --- | --- |
| `asset_id`, `asset_type` | Synthetic holding ID and asset class |
| `notional` | Fictional current GBP holding value; not a derivative contract notional |
| `duration`, `credit_duration` | Assumed rate and credit sensitivities, in years |
| `equity_beta` | Assumed equity sensitivity |
| `currency_exposure` | Signed FX-sensitive GBP exposure |
| `entity_id`, `sector`, `region` | Fictional exposure metadata |
| `base_currency`, `valuation_date` | Synthetic reporting metadata |
| `rating`, `maturity_date` | Illustrative metadata |
| `data_origin` | Always `synthetic` |
| `notional_basis` | States that notional is a synthetic current GBP value |

Values and sensitivities are bounded assumptions for demonstrating stress
mechanics. They are not historical estimates, actual positions, risk advice,
or calibrated valuation inputs. Derivatives are modeled with simplified
linear sensitivities.

## Reproducibility

The generator is `src/simulation.py`, using seed `20261008`. Regenerate the
three simulation data files from the repository root with:

```powershell
python -m src.simulation
```

The random seed reproduces generated content and values; generation timestamps
and date-relative fields depend on when regeneration is run.

## Separate live source disclosure

The application separately polls public BBC Business and CNBC RSS feeds. Those
external feeds are not included in this synthetic data archive: their contents
change over time and are subject to their publishers' terms. Source URLs,
polling behavior and limitations are documented in the root README and
implemented in `src/risk_engine/ingestion.py`.

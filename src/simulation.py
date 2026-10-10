"""Reproducible fictional datasets and clock-driven replay, never market data."""

import json
import random
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.stress_testing.engine import validate_portfolio


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "simulation"
SEED = 20261008
TICK_SECONDS = 10
EVENTS_PER_TICK = 6
WINDOW_SIZE = 120
SECTORS = ("Technology", "Energy", "Industrials", "Healthcare", "Consumer", "Financials")
REGIONS = ("UK", "Europe", "North America", "Asia Pacific")
TEMPLATES = (
    ("Geopolitical", "trade sanctions",
     "{name} faces severe loss and risk as trade sanctions threaten {region} supply routes. "
     "Simulated shipping costs rise {change}% and delayed contracts total GBP {amount} million."),
    ("Macroeconomic", "inflation",
     "{name} warns of severe margin pressure as inflation raises operating costs in {region}. "
     "A simulated interest rate increase of {bps} basis points affects refinancing of GBP {amount} million."),
    ("Credit Event", "default",
     "{name} reports severe credit loss and default risk in its {region} lending book. "
     "Simulated overdue payments reach GBP {amount} million; debt restructuring discussions begin."),
    ("Merger/Acquisition", "acquisition",
     "{name} announces an acquisition to boost growth and improve its {sector} network in {region}. "
     "The fictional transaction is valued at GBP {amount} million with expected savings of {change}%."),
    ("Product Launch", "product launch",
     "{name} reports a promising product launch with strong growth and record demand in {region}. "
     "The simulated {sector} offering targets GBP {amount} million in revenue and {change}% adoption."),
    ("General Market", "routine update",
     "{name} publishes a scheduled {sector} operating update for {region}. "
     "The fictional quarterly revenue estimate is GBP {amount} million; guidance remains unchanged."),
)


def generate_datasets() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    anchor = datetime.now(timezone.utc).replace(microsecond=0)
    entities = [
        {"entity_id": f"SIMCO{i:03d}", "name": f"Fictional {SECTORS[i % 6]} Group {i:03d}",
         "sector": SECTORS[i % 6], "region": REGIONS[(i // 6) % 4]}
        for i in range(240)
    ]
    records = []
    for i in range(12000):
        entity = rng.choice(entities)
        event, topic, template = TEMPLATES[i % len(TEMPLATES)]
        text = template.format(**entity, change=rng.randint(3, 28), bps=rng.choice((25, 50, 75, 100)),
                               amount=rng.randint(5, 800))
        social = (i // len(TEMPLATES)) % 2 == 1
        if social:
            text = f"Simulated analyst post: {text} #{entity['entity_id']} #{entity['sector']}"
        records.append({
            "event_id": f"sim-{i:05d}", "source": "synthetic_social" if social else "synthetic_news",
            "timestamp": (anchor - timedelta(minutes=12000 - i)).isoformat(),
            "text": text, "entities": [entity["entity_id"]], "url": None,
            "data_origin": "synthetic", "sector": entity["sector"], "region": entity["region"],
            "expected_event": event, "topic": topic, "language": "en",
            "publisher": "Fictional Analyst Network" if social else "Fictional Finance Wire",
            "body": text + " All organizations, figures and events in this record are generated for demo use.",
        })
    with (DATA_DIR / "events.jsonl").open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")

    holdings = []
    kinds = ("loan", "bond", "equity", "derivative", "cash")
    for i in range(2400):
        entity = entities[(i // 5) % len(entities)]
        kind = kinds[i % len(kinds)]
        value = round(rng.uniform(250_000, 12_000_000), 2)
        duration = round(rng.uniform(0.2, 7), 3) if kind in {"loan", "bond", "derivative"} else 0
        credit = round(duration * rng.uniform(0.7, 1.05), 3) if kind in {"loan", "bond"} else 0
        holdings.append({
            "asset_id": f"SIM-{i:05d}", "asset_type": kind,
            "description": f"Fictional {kind} exposure to {entity['name']}",
            "notional": value, "duration": duration,
            "equity_beta": round(rng.uniform(0.6, 1.6), 3) if kind == "equity" else 0,
            "credit_duration": credit,
            "currency_exposure": round(value * rng.uniform(-0.35, 0.5), 2) if kind != "cash" else 0,
            "entity_id": entity["entity_id"], "sector": entity["sector"], "region": entity["region"],
            "base_currency": "GBP", "rating": rng.choice(("AAA", "AA", "A", "BBB", "BB")) if credit else "N/A",
            "maturity_date": (anchor + timedelta(days=rng.randint(180, 3650))).date().isoformat()
                if kind in {"loan", "bond", "derivative"} else "",
            "data_origin": "synthetic", "valuation_date": anchor.date().isoformat(),
            "notional_basis": "Synthetic current GBP value; not contractual notional",
        })
    frame = validate_portfolio(pd.DataFrame(holdings))
    frame.to_csv(DATA_DIR / "portfolio.csv", index=False)
    manifest = {
        "data_origin": "synthetic", "seed": SEED, "generated_at": anchor.isoformat(),
        "event_count": len(records), "holdings_count": len(holdings), "entities_count": len(entities),
        "currency": "GBP", "baseline_value": round(float(frame["notional"].sum()), 2),
        "tick_seconds": TICK_SECONDS, "events_per_tick": EVENTS_PER_TICK, "window_size": WINDOW_SIZE,
        "methodology": "Seeded template generation with fictional companies and bounded sensitivities. "
                       "Clock-driven replay cycles through the corpus; not observed prices, posts or transactions.",
    }
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(records):,} fictional events and {len(holdings):,} holdings in {DATA_DIR}")


@lru_cache(maxsize=1)
def catalogue() -> tuple[dict, list[dict], str]:
    try:
        manifest = json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))
        records = [json.loads(line) for line in (DATA_DIR / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        csv_text = (DATA_DIR / "portfolio.csv").read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValueError("Simulation dataset missing. Run python -m src.simulation before starting the API.") from None
    if len(records) < WINDOW_SIZE:
        raise ValueError("Simulation corpus must contain at least 120 events")
    return manifest, records, csv_text


def simulation_status() -> dict:
    manifest, _, _ = catalogue()
    return {**manifest, "tick": int(time.time()) // TICK_SECONDS}


def simulation_portfolio() -> dict:
    manifest, _, csv_text = catalogue()
    return {
        "csv_text": csv_text, "source_reference": f"Synthetic seeded demo v1 (seed {SEED})",
        "valuation_date": manifest["generated_at"][:10], "currency": "GBP",
        "data_origin": "synthetic",
    }


def simulation_records(tick: int | None = None) -> list[dict]:
    _, records, _ = catalogue()
    tick = int(time.time()) // TICK_SECONDS if tick is None else tick
    end = tick * EVENTS_PER_TICK
    result = []
    for sequence in range(end - WINDOW_SIZE, end):
        original = records[sequence % len(records)]
        result.append({
            **original, "event_id": f"{original['event_id']}-replay-{sequence}",
            "dataset_timestamp": original["timestamp"],
            "timestamp": datetime.fromtimestamp(
                (sequence // EVENTS_PER_TICK + 1) * TICK_SECONDS, timezone.utc
            ).isoformat(),
            "simulation_tick": tick,
        })
    return result


if __name__ == "__main__":
    generate_datasets()

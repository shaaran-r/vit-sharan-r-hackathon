from io import StringIO
import numpy as np
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {
    "asset_id", "asset_type", "description", "notional", "duration",
    "equity_beta", "credit_duration", "currency_exposure",
}

SCENARIOS: dict[str, dict[str, float]] = {
    "Geopolitical": {"equity_return": -0.10, "rate_change": 0.02, "spread_change": 0.015, "fx_return": -0.05},
    "Macroeconomic": {"equity_return": -0.08, "rate_change": 0.02, "spread_change": 0.01, "fx_return": -0.02},
    "Credit Event": {"equity_return": -0.05, "rate_change": 0.01, "spread_change": 0.04, "fx_return": -0.01},
    "Merger/Acquisition": {"equity_return": 0.03, "rate_change": 0.0, "spread_change": 0.005, "fx_return": 0.0},
    "Product Launch": {"equity_return": 0.04, "rate_change": 0.0, "spread_change": 0.0, "fx_return": 0.0},
}


def validate_portfolio(portfolio: pd.DataFrame) -> pd.DataFrame:
    portfolio = portfolio.copy()
    missing = REQUIRED_COLUMNS.difference(portfolio.columns)
    if missing:
        raise ValueError(f"Portfolio is missing required columns: {', '.join(sorted(missing))}")
    if portfolio.empty:
        raise ValueError("Portfolio must contain at least one holding")
    for column in ("asset_id", "asset_type", "description"):
        if portfolio[column].isna().any() or portfolio[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"{column} must contain non-empty values")
    if portfolio["asset_id"].duplicated().any():
        raise ValueError("asset_id values must be unique")
    if not portfolio["asset_type"].isin({"loan", "bond", "equity", "derivative", "cash"}).all():
        raise ValueError("asset_type must be loan, bond, equity, derivative or cash")
    for column in ("notional", "duration", "equity_beta", "credit_duration", "currency_exposure"):
        try:
            portfolio[column] = pd.to_numeric(portfolio[column], errors="raise")
        except (TypeError, ValueError) as error:
            raise ValueError(f"{column} must contain numeric values") from error
        if not np.isfinite(portfolio[column]).all():
            raise ValueError(f"{column} must contain finite values")
    if (portfolio[["notional", "duration", "credit_duration"]] < 0).any().any():
        raise ValueError("Values, durations and credit durations must be non-negative")
    if portfolio["notional"].sum() <= 0:
        raise ValueError("Total portfolio value must be positive")
    return portfolio


def parse_portfolio_csv(csv_text: str) -> pd.DataFrame:
    try:
        portfolio = pd.read_csv(StringIO(csv_text))
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as error:
        raise ValueError(f"Invalid portfolio CSV: {error}") from error
    return validate_portfolio(portfolio)


def run_stress_test(
    signal: dict[str, Any],
    portfolio: pd.DataFrame | None = None,
) -> dict[str, Any]:
    event = signal["event_classification"]
    if event not in SCENARIOS:
        raise ValueError(f"No stress scenario is defined for event type: {event}")

    if portfolio is None:
        raise ValueError("Upload a real portfolio before running a stress test")
    holdings = validate_portfolio(portfolio)

    shock = SCENARIOS[event]
    holdings["baseline_value"] = holdings["notional"]
    holdings["equity_pnl"] = holdings["notional"] * holdings["equity_beta"] * shock["equity_return"]
    holdings["rates_pnl"] = -holdings["notional"] * holdings["duration"] * shock["rate_change"]
    holdings["credit_pnl"] = -holdings["notional"] * holdings["credit_duration"] * shock["spread_change"]
    holdings["fx_pnl"] = holdings["currency_exposure"] * shock["fx_return"]
    holdings["stressed_value"] = (
        holdings["baseline_value"]
        + holdings["equity_pnl"]
        + holdings["rates_pnl"]
        + holdings["credit_pnl"]
        + holdings["fx_pnl"]
    ).clip(lower=0)

    before = float(holdings["baseline_value"].sum())
    after = float(holdings["stressed_value"].sum())
    holding_columns = ["asset_id", "asset_type", "baseline_value", "stressed_value"]
    for column in ("description", "reference_apr_pct", "source_url", "source_license", "notional_basis",
                   "sector", "region", "rating", "data_origin",
                   "equity_pnl", "rates_pnl", "credit_pnl", "fx_pnl"):
        if column in holdings.columns:
            holding_columns.append(column)
    holding_data = holdings[holding_columns].copy()
    for column in ("baseline_value", "stressed_value", "reference_apr_pct"):
        if column in holding_data.columns:
            holding_data[column] = pd.to_numeric(holding_data[column], errors="coerce").round(2)
    holding_data = holding_data.astype(object).where(pd.notna(holding_data), None)
    return {
        "event_id": signal["event_id"],
        "event_classification": event,
        "impact_score": signal["impact_score"],
        "scenario": shock,
        "result_type": "Hypothetical scenario estimate, not an observed value or forecast",
        "portfolio_before": round(before, 2),
        "portfolio_after": round(after, 2),
        "change": round(after - before, 2),
        "change_percent": round((after - before) / before * 100, 2) if before else 0.0,
        "holdings": holding_data.to_dict(orient="records"),
    }

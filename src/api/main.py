from datetime import date
from typing import Any, Literal
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.risk_engine.ingestion import LiveSourceError, live_collector
from src.risk_engine.alpha_vantage import alpha_status
from src.risk_engine.pipeline import analyze_record, get_signals
from src.risk_engine.sentiment import SentimentModelError, sentiment_status
from src.stress_testing.engine import SCENARIOS, parse_portfolio_csv, run_stress_test
from src.simulation import DATA_DIR, simulation_portfolio, simulation_status


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    source: str = "user_supplied"
    entities: list[str] = Field(default_factory=list)
    data_origin: Literal["user_supplied", "synthetic"] = "user_supplied"


class PortfolioRequest(BaseModel):
    data_origin: Literal["user_declared_real"] = "user_declared_real"
    csv_text: str = Field(min_length=1, max_length=2_000_000)
    source_reference: str = Field(min_length=3, max_length=1000)
    valuation_date: date
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    authorized_real_data: Literal[True]


class SyntheticPortfolioRequest(BaseModel):
    data_origin: Literal["synthetic"]
    csv_text: str = Field(min_length=1, max_length=2_000_000)
    source_reference: str = Field(min_length=3, max_length=1000)
    valuation_date: date
    currency: str = Field(pattern=r"^[A-Z]{3}$")


PortfolioInput = PortfolioRequest | SyntheticPortfolioRequest


class StressTestRequest(BaseModel):
    event_id: str = "interactive"
    event_classification: str
    impact_score: int = Field(ge=1, le=10)
    portfolio: PortfolioInput
    min_impact: int = Field(default=7, ge=1, le=10)


class BatchStressRequest(BaseModel):
    portfolio: PortfolioInput
    min_impact: int = Field(default=7, ge=1, le=10)
    mode: Literal["live", "hybrid"] = "live"
    representative_only: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    live_collector.start()
    try:
        yield
    finally:
        live_collector.stop()


app = FastAPI(title="Signal & Stress Risk Engine", version="2.1.0", lifespan=lifespan)


def portfolio_data(request: PortfolioInput):
    if not request.source_reference.strip():
        raise ValueError("Portfolio source reference is required")
    if request.valuation_date > date.today():
        raise ValueError("Portfolio valuation date cannot be in the future")
    return parse_portfolio_csv(request.csv_text)


def attach_provenance(result: dict[str, Any], portfolio: PortfolioInput) -> dict[str, Any]:
    return {
        **result,
        "currency": portfolio.currency,
        "source_reference": portfolio.source_reference,
        "valuation_date": portfolio.valuation_date.isoformat(),
        "data_origin": "synthetic" if isinstance(portfolio, SyntheticPortfolioRequest) else "user_declared_real",
        "provenance_status": (
            "Synthetic fictional holdings; not actual exposures"
            if isinstance(portfolio, SyntheticPortfolioRequest)
            else "User-declared real holdings; not independently verified"
        ),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/news-status")
def news_status() -> dict[str, Any]:
    return {
        "alpha_vantage": alpha_status(), "live_news": live_collector.status(),
        "sentiment": sentiment_status(),
    }


@app.get("/simulation/status")
def demo_status() -> dict[str, Any]:
    try:
        return simulation_status()
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/simulation/portfolio")
def demo_portfolio() -> dict[str, Any]:
    try:
        return {"portfolio": simulation_portfolio(), "summary": simulation_status()}
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/simulation/download/{dataset}")
def download_demo(dataset: Literal["portfolio.csv", "events.jsonl", "manifest.json"]):
    demo_status()
    return FileResponse(DATA_DIR / dataset, filename=f"synthetic-{dataset}")


@app.get("/signals")
def signals(mode: str = "live", query: str = "finance") -> list[dict[str, Any]]:
    try:
        return get_signals(mode=mode, query=query)
    except LiveSourceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SentimentModelError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    try:
        return analyze_record(request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SentimentModelError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.post("/portfolio/validate")
def validate_uploaded_portfolio(request: PortfolioInput) -> dict[str, Any]:
    try:
        holdings = portfolio_data(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return attach_provenance({
        "holdings_count": len(holdings),
        "baseline_value": float(holdings["notional"].sum()),
    }, request)


@app.post("/stress-test")
def stress_test(request: StressTestRequest) -> dict[str, Any]:
    try:
        holdings = portfolio_data(request.portfolio)
        if request.event_classification not in SCENARIOS:
            raise ValueError(f"No stress scenario is defined for event type: {request.event_classification}")
        if request.impact_score < request.min_impact:
            return {"triggered": False, "reason": "Impact is below the selected threshold", "result": None}
        result = run_stress_test(request.model_dump(), portfolio=holdings)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"triggered": True, "reason": None, "result": attach_provenance(result, request.portfolio)}


@app.post("/stress-tests")
def stress_tests(request: BatchStressRequest) -> list[dict[str, Any]]:
    try:
        holdings = portfolio_data(request.portfolio)
        candidates = [
            signal for signal in get_signals(mode=request.mode)
            if signal["impact_score"] >= request.min_impact
            and signal["event_classification"] in SCENARIOS
        ]
        if request.representative_only:
            representatives = {}
            for signal in sorted(candidates, key=lambda item: item["impact_score"], reverse=True):
                representatives.setdefault(signal["event_classification"], signal)
            candidates = list(representatives.values())
        results = []
        for signal in candidates:
            result = attach_provenance(run_stress_test(signal, portfolio=holdings), request.portfolio)
            if request.representative_only:
                result.pop("holdings")
            results.append(result)
        return results
    except LiveSourceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SentimentModelError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/stress-tests")
def missing_portfolio() -> None:
    raise HTTPException(status_code=409, detail="A real portfolio is required. Use POST /stress-tests with portfolio data.")

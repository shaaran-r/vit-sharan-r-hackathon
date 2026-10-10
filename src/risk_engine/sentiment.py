import os
import re
from functools import lru_cache
from typing import Any, Callable
from pathlib import Path
from threading import Lock

from src import settings


POSITIVE_WORDS = {
    "beat", "boost", "growth", "improve", "positive", "promising", "raises",
    "record", "strong", "success", "surge", "upgrade",
}
NEGATIVE_WORDS = {
    "bankruptcy", "crash", "default", "decline", "drop", "escalate", "loss",
    "negative", "pressure", "risk", "severe", "threaten", "warns", "worried",
}
DEFAULT_FINBERT_MODEL = "ProsusAI/finbert"
LOCAL_FINBERT_MODEL = Path(__file__).resolve().parents[2] / "models" / "finbert"
_inference_lock = Lock()
_model_status = "not_loaded"


class SentimentModelError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_finbert(model_name: str) -> Callable[..., Any]:
    global _model_status
    try:
        from transformers import pipeline
    except ImportError as error:
        raise SentimentModelError(
            "FinBERT dependencies are missing; install requirements.txt or set "
            "SENTIMENT_BACKEND=lexicon for offline demo scoring"
        ) from error

    try:
        import torch
        torch.set_num_threads(2)
        classifier = pipeline(
            "text-classification",
            model=model_name,
            tokenizer=model_name,
            device=-1,
        )
        _model_status = "ready"
        return classifier
    except Exception as error:
        _model_status = "unavailable"
        raise SentimentModelError(
            f"Could not load FinBERT model {model_name!r}; check network access and model availability"
        ) from error


def _score_lexicon(text: str) -> tuple[float, float]:
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if not tokens:
        return 0.0, 0.0
    score = sum(token in POSITIVE_WORDS for token in tokens) - sum(
        token in NEGATIVE_WORDS for token in tokens
    )
    scaled = max(-1.0, min(1.0, score / max(3, len(tokens) * 0.2)))
    return round(scaled, 2), min(1.0, abs(scaled))


def model_name() -> str:
    return os.environ.get("FINBERT_MODEL") or (
        str(LOCAL_FINBERT_MODEL) if (LOCAL_FINBERT_MODEL / "model.safetensors").exists()
        else DEFAULT_FINBERT_MODEL
    )


def sentiment_status() -> dict[str, Any]:
    backend = os.environ.get("SENTIMENT_BACKEND", "finbert").lower()
    return {
        "backend": backend, "model": model_name() if backend == "finbert" else None,
        "status": _model_status if backend == "finbert" else "heuristic",
        "trained_model": backend == "finbert" and _model_status == "ready",
    }


def analyze_sentiment(text: str) -> tuple[float, float]:
    return _analyze_cached(text, os.environ.get("SENTIMENT_BACKEND", "finbert").lower(), model_name())


@lru_cache(maxsize=16000)
def _analyze_cached(text: str, backend: str, selected_model: str) -> tuple[float, float]:
    if backend == "lexicon":
        return _score_lexicon(text)
    if backend != "finbert":
        raise ValueError("SENTIMENT_BACKEND must be 'finbert' or 'lexicon'")

    try:
        with _inference_lock:
            prediction = _load_finbert(selected_model)(text, truncation=True, max_length=512)
    except SentimentModelError:
        raise
    except Exception as error:
        raise SentimentModelError(f"FinBERT inference failed: {error}") from error

    if isinstance(prediction, list) and prediction and isinstance(prediction[0], dict):
        prediction = prediction[0]
    if not isinstance(prediction, dict):
        raise SentimentModelError("FinBERT returned an unexpected prediction format")

    label = str(prediction.get("label", "")).lower()
    try:
        confidence = float(prediction["score"])
    except (KeyError, TypeError, ValueError) as error:
        raise SentimentModelError("FinBERT prediction is missing a numeric score") from error
    if label not in {"positive", "negative", "neutral"} or not 0 <= confidence <= 1:
        raise SentimentModelError("FinBERT returned an unsupported label or confidence")

    sentiment = confidence if label == "positive" else -confidence if label == "negative" else 0.0
    return round(sentiment, 2), round(confidence, 2)


def score_sentiment(text: str) -> float:
    return analyze_sentiment(text)[0]

"""Install the official ProsusAI checkpoint locally when the Hub is unavailable."""

import json
from pathlib import Path

import requests
import torch
from transformers import BertConfig, BertForSequenceClassification, BertTokenizer


MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "finbert"
WEIGHTS_URL = "https://prosus-public.s3-eu-west-1.amazonaws.com/finbert/finbert-sentiment/pytorch_model.bin"
VOCAB_URL = "https://s3.amazonaws.com/models.huggingface.co/bert/bert-base-uncased-vocab.txt"


def download(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".partial")
    try:
        with requests.get(url, stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()
            expected = int(response.headers.get("Content-Length", 0))
            size = 0
            with temporary.open("wb") as stream:
                for chunk in response.iter_content(1024 * 1024):
                    stream.write(chunk)
                    size += len(chunk)
            if expected and size != expected:
                raise RuntimeError(f"Incomplete model download: {size} of {expected} bytes")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    weights = MODEL_DIR / "official-pytorch_model.bin"
    vocab = MODEL_DIR / "vocab.txt"
    for url, path in ((WEIGHTS_URL, weights), (VOCAB_URL, vocab)):
        if not path.exists():
            print(f"Downloading official model asset: {path.name}", flush=True)
            download(url, path)
    labels = {0: "positive", 1: "negative", 2: "neutral"}
    config = BertConfig(id2label=labels, label2id={label: index for index, label in labels.items()})
    model = BertForSequenceClassification(config)
    state = torch.load(weights, map_location="cpu", weights_only=True)
    model.load_state_dict(state, strict=True)
    model.save_pretrained(MODEL_DIR, safe_serialization=True)
    BertTokenizer(vocab_file=str(vocab), do_lower_case=True, model_max_length=512).save_pretrained(MODEL_DIR)
    (MODEL_DIR / "provenance.json").write_text(json.dumps({
        "publisher": "ProsusAI", "repository": "https://github.com/ProsusAI/finBERT",
        "weights_url": WEIGHTS_URL, "vocab_url": VOCAB_URL,
        "label_mapping": labels, "conversion": "Strict state-dict load, serialized as safetensors",
    }, indent=2), encoding="utf-8")
    print(f"Local FinBERT prepared at {MODEL_DIR}", flush=True)


if __name__ == "__main__":
    main()

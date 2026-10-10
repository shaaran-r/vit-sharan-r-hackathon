import re
from html import escape

from src.risk_engine.classification import event_keyword_matches
from src.risk_engine.sentiment import NEGATIVE_WORDS, POSITIVE_WORDS


def highlight_headline(text: str) -> tuple[str, dict[str, list[str]]]:
    cues: dict[str, list[str]] = {"Event triggers": [], "Negative cues": [], "Positive cues": []}
    spans: list[tuple[int, int, str]] = []
    for start, end, category, keyword in event_keyword_matches(text):
        description = f"{keyword} ({category})"
        if description not in cues["Event triggers"]:
            cues["Event triggers"].append(description)
        spans.append((start, end, "trigger"))
    for token in re.finditer(r"[a-zA-Z']+", text):
        word = token.group().lower()
        if word in NEGATIVE_WORDS:
            group, style = "Negative cues", "negative"
        elif word in POSITIVE_WORDS:
            group, style = "Positive cues", "positive"
        else:
            continue
        if word not in cues[group]:
            cues[group].append(word)
        spans.append((token.start(), token.end(), style))

    # Combine overlapping matches so phrases such as "credit loss" remain one highlight.
    merged: list[tuple[int, int, set[str]]] = []
    for start, end, style in sorted(spans):
        if merged and start < merged[-1][1]:
            previous_start, previous_end, styles = merged[-1]
            merged[-1] = (previous_start, max(previous_end, end), styles | {style})
        else:
            merged.append((start, end, {style}))
    parts = []
    cursor = 0
    labels = {"negative": "Negative lexicon cue", "positive": "Positive lexicon cue", "trigger": "Event classification trigger"}
    for start, end, styles in merged:
        style = next(kind for kind in ("negative", "positive", "trigger") if kind in styles)
        title = "; ".join(labels[kind] for kind in sorted(styles))
        parts.append(escape(text[cursor:start]))
        parts.append(f'<mark class="cue-{style}" title="{escape(title, quote=True)}">{escape(text[start:end])}</mark>')
        cursor = end
    parts.append(escape(text[cursor:]))
    return '<div class="headline-cues">' + "".join(parts) + "</div>", cues

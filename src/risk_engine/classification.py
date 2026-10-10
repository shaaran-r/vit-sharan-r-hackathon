import re


EVENT_KEYWORDS = {
    "Geopolitical": ("war", "conflict", "sanction", "sanctions", "tariff", "tariffs", "trade tension", "geopolitical"),
    "Macroeconomic": ("inflation", "interest rate", "recession", "gdp", "unemployment", "central bank"),
    "Credit Event": ("default", "credit loss", "downgrade", "bankruptcy", "debt restructuring"),
    "Merger/Acquisition": ("merger", "acquisition", "acquire", "takeover", "buyout"),
    "Product Launch": ("product launch", "launches", "new product", "product release"),
}


def event_keyword_matches(text: str) -> list[tuple[int, int, str, str]]:
    normalized = re.sub(r"[^a-z0-9 ]", " ", text, flags=re.IGNORECASE)
    matches = []
    for category, keywords in EVENT_KEYWORDS.items():
        for keyword in keywords:
            keyword_pattern = re.escape(keyword).replace(r"\ ", r"\s+")
            for match in re.finditer(rf"(?<!\w){keyword_pattern}(?!\w)", normalized, flags=re.IGNORECASE):
                matches.append((match.start(), match.end(), category, keyword))
    return matches


def classify_event(text: str) -> str:
    matches = event_keyword_matches(text)
    return matches[0][2] if matches else "General Market"

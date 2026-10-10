"""Generate the submission architecture PNG and six-slide PDF using Pillow."""

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
WIDTH, HEIGHT = 2560, 1440
BG, CARD, WHITE, MUTED, ACCENT = "#08111f", "#102137", "#eef5ff", "#b6c7da", "#63d6c4"


def font(size: int, bold: bool = False):
    windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    names = [windows / ("arialbd.ttf" if bold else "arial.ttf"),
             Path("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")]
    for name in names:
        try:
            return ImageFont.truetype(str(name), size)
        except OSError:
            continue
    raise RuntimeError("Install Arial or DejaVu Sans to generate submission assets")


def wrap(draw, text, width, face):
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=face) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + [current]


def paragraph(draw, text, xy, width, size=38, color=MUTED):
    x, y = xy
    for line in wrap(draw, text, width, font(size)):
        draw.text((x, y), line, font=font(size), fill=color)
        y += int(size * 1.45)
    return y


def page(title, subtitle, number):
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 18), fill=ACCENT)
    draw.text((100, 70), "SIGNAL & STRESS  |  S&P GLOBAL & CRISIL CAMPUS HACKATHON",
              font=font(27, True), fill=ACCENT)
    draw.text((100, 140), title, font=font(76, True), fill=WHITE)
    paragraph(draw, subtitle, (104, 250), WIDTH - 210, 34)
    draw.line((100, 1320, WIDTH - 100, 1320), fill="#34506d", width=2)
    draw.text((100, 1350), "SHARAN R  |  VELLORE INSTITUTE OF TECHNOLOGY (VIT)",
              font=font(26), fill=MUTED)
    draw.text((WIDTH - 160, 1350), f"{number}/6", font=font(26), fill=ACCENT)
    return image


def bullets(image, items):
    draw = ImageDraw.Draw(image)
    y = 380
    for heading, body in items:
        draw.rounded_rectangle((100, y, WIDTH - 100, y + 188), radius=20, fill=CARD)
        draw.text((140, y + 24), heading, font=font(40, True), fill=ACCENT)
        end = paragraph(draw, body, (140, y + 83), WIDTH - 300, 34)
        if end > y + 187:
            raise ValueError(f"Slide content overflows: {heading}")
        y += 215
    if y > 1310:
        raise ValueError("Too many slide cards")


def vtext(base, text, xy, face, fill):
    """Draw text rotated 90 degrees (bottom-to-top) for swim-lane labels."""
    bbox = face.getbbox(text)
    w, h = bbox[2] - bbox[0] + 6, bbox[3] - bbox[1] + 6
    chip = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(chip).text((3, 3), text, font=face, fill=fill)
    base.paste(chip.rotate(90, expand=True), xy, chip.rotate(90, expand=True))


def chip(draw, xy, text, color):
    x, y = xy
    w = draw.textlength(text, font=font(19, True)) + 28
    draw.rounded_rectangle((x, y, x + w, y + 34), radius=17, outline=color, width=2)
    draw.text((x + 14, y + 7), text, font=font(19, True), fill=color)
    return w


def numbered_circle(draw, center, number, color):
    x, y = center
    draw.ellipse((x - 22, y - 22, x + 22, y + 22), fill=color)
    text = str(number)
    tw = draw.textlength(text, font=font(24, True))
    draw.text((x - tw / 2, y - 15), text, font=font(24, True), fill="#06101d")


def architecture():
    AW, AH = 3000, 1700
    LANE_BG = ["#0b1829", "#0c1b2e", "#0b1829", "#0c1b2e"]
    image = Image.new("RGB", (AW, AH), BG)
    draw = ImageDraw.Draw(image)

    margin_x = 90
    top_band = 10
    title_y = 40
    header_divider_y = 160
    lane_top = 190
    lane_gap = 18
    lane_h = 275
    lane_x0 = margin_x
    lane_x1 = AW - margin_x
    header_w = 230
    content_gap = 26
    box_gap = 28
    card_shadow = (4, 6)
    inner_pad_y = 24
    inner_pad_x = 16

    content_x0 = lane_x0 + header_w + content_gap
    content_w = lane_x1 - content_x0
    box_w = int((content_w - (3 * box_gap)) / 4)

    draw.rectangle((0, 0, AW, top_band), fill=ACCENT)
    draw.text((margin_x, title_y), "SIGNAL & STRESS  |  SYSTEM ARCHITECTURE", font=font(34, True), fill=WHITE)
    draw.text(
        (margin_x, title_y + 52),
        "End-to-end data flow: real and labeled-synthetic ingestion, local FinBERT scoring, structured API delivery, and event-driven portfolio stress testing",
        font=font(26),
        fill=MUTED,
    )
    draw.line((margin_x, header_divider_y, AW - margin_x, header_divider_y), fill="#223a54", width=2)

    lanes = [
        ("01", "Data sources", "Published and synthetic inputs", "#2ec4b6", [
            ("BBC BUSINESS RSS", "LIVE", "#2ec4b6", ["Public RSS publisher feed", "Polled every 60 seconds"], []),
            ("CNBC RSS", "LIVE", "#2ec4b6", ["Public RSS publisher feed", "Fetched concurrently with BBC"], []),
            ("SYNTHETIC REPLAY DATASET", "SYNTHETIC", "#ffb020", ["12,000 fictional news/social rows", "Seeded and clearly labeled"], []),
            ("PORTFOLIO CSV INPUT", "INPUT", "#57a6f7", ["2,400 synthetic GBP holdings", "Optional authorized real CSV"], []),
        ]),
        ("02", "Ingestion & NLP engine", "Collection, normalization, signal creation", "#ffb020", [
            ("LIVE NEWS COLLECTOR", "ENGINE", "#ffb020", ["Concurrent dual-publisher poll", "Deduplication and per-source status"], ["ThreadPoolExecutor", "daemon thread"]),
            ("TEXT NORMALIZER", "ENGINE", "#ffb020", ["Markup cleanup and provenance tags", "live_publisher vs synthetic"], ["pandas"]),
            ("FINBERT SENTIMENT MODEL", "MODEL", "#ffb020", ["Local pretrained financial BERT", "3-class softmax mapped to [-1, 1]"], ["PyTorch", "Transformers"]),
            ("EVENT & IMPACT SCORER", "ENGINE", "#ffb020", ["Rule-based event classification", "5 categories with impact scaled 1-10"], ["rule-based"]),
        ]),
        ("03", "Serving layer", "Structured delivery and live monitoring", "#57a6f7", [
            ("FASTAPI SERVICE", "API", "#57a6f7", ["Versioned REST JSON endpoints", "Lifespan starts and stops collector"], ["FastAPI", "uvicorn"]),
            ("STRUCTURED SIGNAL STORE", "DATA", "#57a6f7", ["In-memory signal cache", "sentiment, event, impact, metadata"], []),
            ("STREAMLIT DASHBOARD", "UI", "#57a6f7", ["Refreshes from API every 10 seconds", "Signal Explorer and Analyze Text"], ["Streamlit"]),
            ("/docs & /news-status", "API", "#57a6f7", ["OpenAPI reference", "Live source and model health"], []),
        ]),
        ("04", "Module B: stress testing", "Scenario trigger, shock engine, outputs", "#f16474", [
            ("THRESHOLD TRIGGER", "LOGIC", "#f16474", ["Category match plus impact > 7", "Threshold remains configurable"], []),
            ("SHOCK VECTOR LIBRARY", "CONFIG", "#f16474", ["Equity, rate, credit, FX shocks", "Preset scenarios by event type"], []),
            ("STRESS ENGINE", "ENGINE", "#f16474", ["Per-holding recomputation", "Beta, duration, FX exposure"], ["pandas", "numpy"]),
            ("SCENARIO VISUALIZATION", "UI", "#f16474", ["Baseline vs stressed chart", "Holding-level P&L drilldown"], ["Streamlit"]),
        ]),
    ]

    lane_positions = []

    def draw_header_block(x0, y0, x1, y1, number, title, subtitle, color):
        draw.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=color)
        draw.text((x0 + 24, y0 + 26), number, font=font(34, True), fill="#07111d")
        title_face = font(24, True)
        title_lines = wrap(draw, title, x1 - x0 - 48, title_face)
        for i, line in enumerate(title_lines):
            draw.text((x0 + 24, y0 + 82 + i * 28), line, font=title_face, fill="#07111d")
        subtitle_y = y0 + 94 + len(title_lines) * 28
        for i, line in enumerate(wrap(draw, subtitle, x1 - x0 - 48, font(20))):
            draw.text((x0 + 24, subtitle_y + i * 27), line, font=font(20), fill="#102137")

    def draw_card(x0, y0, x1, y1, title, tag, color, lines, chips_):
        draw.rounded_rectangle((x0 + card_shadow[0], y0 + card_shadow[1], x1 + card_shadow[0], y1 + card_shadow[1]),
                               radius=16, fill="#03070d")
        draw.rounded_rectangle((x0, y0, x1, y1), radius=16, fill=CARD, outline=color, width=2)
        draw.text((x0 + 20, y0 + 18), title, font=font(22, True), fill=WHITE)
        tag_w = int(draw.textlength(tag, font=font(15, True)) + 26)
        tag_x0 = x1 - tag_w - 16
        draw.rounded_rectangle((tag_x0, y0 + 16, x1 - 16, y0 + 42), radius=13, fill=color)
        draw.text((tag_x0 + 13, y0 + 20), tag, font=font(15, True), fill="#07111d")
        ty = y0 + 68
        for line in lines:
            draw.text((x0 + 20, ty), line, font=font(19), fill=MUTED)
            ty += 31
        if chips_:
            cx = x0 + 20
            cy = y1 - 46
            for item in chips_:
                cx += chip(draw, (cx, cy), item, color) + 10

    for i, (number, title, subtitle, color, boxes) in enumerate(lanes):
        y0 = lane_top + i * (lane_h + lane_gap)
        y1 = y0 + lane_h
        lane_positions.append((y0, y1))
        draw.rounded_rectangle((lane_x0, y0, lane_x1, y1), radius=20, fill=LANE_BG[i], outline="#193148", width=1)
        draw_header_block(lane_x0, y0, lane_x0 + header_w, y1, number, title, subtitle, color)

        card_y0 = y0 + inner_pad_y
        card_y1 = y1 - inner_pad_y
        for j, (card_title, tag, tcolor, lines, chips_) in enumerate(boxes):
            bx0 = content_x0 + j * (box_w + box_gap)
            bx1 = bx0 + box_w
            draw_card(bx0, card_y0, bx1, card_y1, card_title, tag, tcolor, lines, chips_)

    def draw_vertical_flow(x, start_y, end_y, color, number):
        draw.line((x, start_y, x, end_y), fill=color, width=5)
        draw.polygon([(x, end_y), (x - 12, end_y - 18), (x + 12, end_y - 18)], fill=color)
        numbered_circle(draw, (x, int((start_y + end_y) / 2)), number, color)

    flow_x = lane_x1 - 58
    flow_colors = ["#2ec4b6", "#ffb020", "#57a6f7"]
    for i, color in enumerate(flow_colors):
        start_y = lane_positions[i][1] - 18
        end_y = lane_positions[i + 1][0] + 18
        draw_vertical_flow(flow_x, start_y, end_y, color, i + 1)

    col_centers = [content_x0 + (box_w / 2) + idx * (box_w + box_gap) for idx in range(4)]
    portfolio_x = int(col_centers[3])
    stress_x = int(col_centers[2])
    route_x = int(content_x0 + 3 * (box_w + box_gap) - (box_gap / 2))
    top_y = lane_positions[0][1] - 12
    bottom_y = lane_positions[3][0] + 58

    draw.line((portfolio_x, top_y, portfolio_x, top_y + 28), fill="#57a6f7", width=4)
    draw.line((portfolio_x, top_y + 28, route_x, top_y + 28), fill="#57a6f7", width=4)
    draw.line((route_x, top_y + 28, route_x, bottom_y), fill="#57a6f7", width=4)
    draw.line((route_x, bottom_y, stress_x, bottom_y), fill="#57a6f7", width=4)
    draw.line((stress_x, bottom_y, stress_x, lane_positions[3][0] + 24), fill="#57a6f7", width=4)
    draw.polygon(
        [(stress_x, lane_positions[3][0] + 24), (stress_x - 12, lane_positions[3][0] + 6), (stress_x + 12, lane_positions[3][0] + 6)],
        fill="#57a6f7",
    )
    label = "Direct portfolio feed"
    label_w = int(draw.textlength(label, font=font(17, True)) + 24)
    label_x0 = route_x - int(label_w / 2)
    label_y0 = int((top_y + bottom_y) / 2) - 18
    draw.rounded_rectangle((label_x0, label_y0, label_x0 + label_w, label_y0 + 30), radius=15, fill=BG, outline="#57a6f7", width=2)
    draw.text((label_x0 + 12, label_y0 + 7), label, font=font(17, True), fill="#57a6f7")

    footer_top = lane_positions[-1][1] + 34
    flow_title_y = footer_top
    flow_body_y = flow_title_y + 38
    draw.text((margin_x, flow_title_y), "FLOW", font=font(22, True), fill=ACCENT)
    flow_steps = [
        (1, "Ingestion normalizes real and synthetic text and preserves provenance.", flow_colors[0]),
        (2, "FinBERT and rules convert text into sentiment, event, and impact signals.", flow_colors[1]),
        (3, "Signals are exposed via JSON and can trigger stress testing when severity is high.", flow_colors[2]),
    ]
    fy = flow_body_y
    for number, text, color in flow_steps:
        numbered_circle(draw, (margin_x + 18, fy + 14), number, color)
        draw.text((margin_x + 52, fy), text, font=font(20), fill=WHITE)
        fy += 36

    legend_x = AW - 700
    draw.text((legend_x, flow_title_y), "LEGEND", font=font(22, True), fill=ACCENT)
    legend_items = [
        ("#2ec4b6", "Real published data"),
        ("#ffb020", "Synthetic or rule-based processing"),
        ("#57a6f7", "Computed or served signal"),
        ("#f16474", "Stress-testing application output"),
    ]
    ly = flow_body_y
    for color, label in legend_items:
        draw.ellipse((legend_x, ly + 3, legend_x + 18, ly + 21), fill=color)
        draw.text((legend_x + 30, ly - 1), label, font=font(20), fill=MUTED)
        ly += 32

    footer_rule_y = AH - 74
    draw.line((margin_x, footer_rule_y, AW - margin_x, footer_rule_y), fill="#223a54", width=2)
    draw.text(
        (margin_x, footer_rule_y + 16),
        "RSS polling is not publisher push streaming. Synthetic data remains labeled at schema level. Scenario losses are illustrative, not forecasts.",
        font=font(22),
        fill=MUTED,
    )
    return image


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    diagram = architecture()
    diagram.save(OUT / "architecture.png", dpi=(200, 200))
    slides = []
    first = page("From headlines to portfolio risk",
                 "A unified AI/NLP risk engine with Module B: strategic event-driven stress testing.", 1)
    bullets(first, [
        ("CANDIDATE", "SHARAN R | VELLORE INSTITUTE OF TECHNOLOGY (VIT) | sharan.r2022@vitstudent.ac.in"),
        ("PROBLEM", "Risk analysts must connect unstructured financial news to portfolio exposures quickly and traceably."),
        ("APPROACH", "Real publisher news -> structured risk signals -> hypothetical shocks -> before/after portfolio estimates."),
        ("DEMO SCOPE", "A locally runnable Python prototype. No investment advice, production valuation or guaranteed predictions."),
    ])
    slides.append(first)
    second = page("One engine, modular applications",
                  "FastAPI | Streamlit | PyTorch + Transformers | pandas | RSS background worker", 2)
    resized = diagram.resize((2240, 1000))
    second.paste(resized, (160, 310))
    slides.append(second)
    third = page("Dataset used: real + clearly fictional",
                 "Self-generated synthetic data is permitted by the supplied dataset clarification.", 3)
    bullets(third, [
        ("REAL INPUTS", "BBC and CNBC RSS: up to 25 headlines each, collected every 60 seconds. URLs and publication times retained."),
        ("DETAILED SYNTHETIC DATA", "12,000 fictional news/social records; 2,400 holdings; 240 issuers; 5 asset types, 6 sectors and 4 regions."),
        ("REPRODUCIBLE DEMO", "Seed 20261008; CSV/JSONL datasets and generation manifest. Optional replay emits 6 events every 10 seconds."),
        ("ASSUMPTIONS", "GBP values and bounded sensitivities are fictional. No actual bank transactions, calibrated distributions or live social posts."),
    ])
    slides.append(third)
    fourth = page("Explainable workflow, honest model scope",
                  "Pretrained sentiment is active; event and severity rules remain illustrative.", 4)
    bullets(fourth, [
        ("SIGNAL CONTRACT", "Sentiment [-1, 1], event category, impact [1, 10], source, timestamp and provenance available through JSON APIs."),
        ("NLP VERIFICATION", "Official local FinBERT: positive +0.84, negative -0.82, neutral 0.00 on three smoke-test sentences, not a benchmark."),
        ("FAST INSPECTION", "Six editable cases, source/category filters, downloads, cue highlights and explicit stress-threshold explanations."),
        ("BOUNDARIES", "Keyword cues are not FinBERT attributions. Impact is not a calibrated prediction; negation and factual accuracy are not resolved."),
    ])
    slides.append(fourth)
    fifth = page("Module B: quantify hypothetical stress",
                 "A geopolitical scenario illustrates the baseline-to-stressed portfolio workflow.", 5)
    bullets(fifth, [
        ("EVENT-DRIVEN TRIGGER", "Risk category and impact drive the scenario. Default threshold >=7; select 8 for the example impact >7."),
        ("ILLUSTRATIVE SHOCKS", "Geopolitical: equity -10%, rates +2 percentage points, spreads +1.5 points, FX -5%."),
        ("BUNDLED DATASET RESULT", "GBP 14,685,727,454.43 baseline -> GBP 13,392,991,408.98 stressed value: approximately -8.80%."),
        ("INTERPRETATION", "Holding P&L and asset-class charts support risk review. Linear sensitivities and zero-clipping are simplified; scenarios are independent."),
    ])
    slides.append(fifth)
    sixth = page("Validated prototype, reviewer-ready demo",
                 "Business value: traceability from a published headline to an estimated portfolio exposure change.", 6)
    bullets(sixth, [
        ("VERIFICATION", "37 tests passed at last validation. Both real publishers, trained inference and unattended collection were verified."),
        ("REVIEWER WALKTHROUGH", "Confirm model/source status -> load Debt default -> analyze cues -> inspect stress impact -> open Dataset studio and API docs."),
        ("RUN LOCALLY", "Install requirements; generate datasets; prepare official FinBERT; run python run_demo.py. Dashboard: localhost:8501."),
        ("NEXT STEPS & SUBMISSION", "Evaluate unseen headlines and calibrate impact. Public repo: vit-sharan-r-hackathon (pending). Demo video URL: pending."),
    ])
    slides.append(sixth)
    slides[0].save(OUT / "presentation.pdf", save_all=True, append_images=slides[1:], resolution=160)
    print(f"Saved {len(slides)} slides and a detailed architecture diagram in {OUT}")


if __name__ == "__main__":
    main()

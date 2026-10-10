"""Generate the submission architecture and seven-slide presentation assets."""

import base64
import html
import os
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs"
WIDTH, HEIGHT = 2560, 1440
BG, CARD, WHITE, MUTED, ACCENT = "#08111f", "#102137", "#eef5ff", "#b6c7da", "#63d6c4"
BLUE, AMBER, ROSE = "#57a6f7", "#ffb020", "#f16474"


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


def slide_frame(title: str, subtitle: str, number: int, section: str) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 14), fill=ACCENT)
    draw.text((92, 50), section.upper(), font=font(24, True), fill=ACCENT)
    title_size = 66
    title_face = font(title_size, True)
    while draw.textlength(title, font=title_face) > WIDTH - 192 and title_size > 42:
        title_size -= 2
        title_face = font(title_size, True)
    draw.text((92, 92), title, font=title_face, fill=WHITE)
    paragraph(draw, subtitle, (96, 178), WIDTH - 192, 29, MUTED)
    draw.line((92, 1320, WIDTH - 92, 1320), fill="#2b4058", width=2)
    draw.text((94, 1345), "SHARAN R  |  VELLORE INSTITUTE OF TECHNOLOGY", font=font(20, True), fill=MUTED)
    draw.text((WIDTH - 148, 1345), f"{number:02d} / 07", font=font(20, True), fill=ACCENT)
    return image


def panel(draw, bounds, heading: str, color: str = ACCENT, fill: str = CARD) -> None:
    x0, y0, x1, y1 = bounds
    draw.rounded_rectangle((x0 + 4, y0 + 7, x1 + 4, y1 + 7), radius=18, fill="#03070d")
    draw.rounded_rectangle(bounds, radius=18, fill=fill, outline="#25405c", width=2)
    draw.rectangle((x0 + 2, y0 + 22, x0 + 8, y1 - 22), fill=color)
    draw.text((x0 + 28, y0 + 24), heading, font=font(25, True), fill=color)


def wrapped_text(draw, text: str, xy: tuple[int, int], width: int, size: int = 24,
                 color: str = MUTED, gap: float = 1.45) -> int:
    x, y = xy
    face = font(size)
    for line in wrap(draw, text, width, face):
        draw.text((x, y), line, font=face, fill=color)
        y += int(size * gap)
    return y


def tag(draw, xy: tuple[int, int], text: str, color: str) -> int:
    x, y = xy
    face = font(17, True)
    width = int(draw.textlength(text, font=face) + 28)
    draw.rounded_rectangle((x, y, x + width, y + 34), radius=17, fill=color)
    draw.text((x + 14, y + 7), text, font=face, fill="#06101d")
    return width


def draw_cover() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 16), fill=ACCENT)
    draw.text((100, 78), "S&P GLOBAL & CRISIL  |  CAMPUS HACKATHON 2026", font=font(23, True), fill=ACCENT)
    draw.text((100, 190), "SIGNAL", font=font(132, True), fill=WHITE)
    draw.text((100, 326), "& STRESS", font=font(132, True), fill=ACCENT)
    wrapped_text(
        draw,
        "From unstructured financial news to transparent portfolio stress scenarios.",
        (108, 520), 1190, 37, WHITE,
    )
    draw.text((108, 730), "AI / NLP RISK ENGINE", font=font(22, True), fill=MUTED)
    draw.text((108, 770), "+ MODULE B: STRATEGIC PORTFOLIO STRESS TESTING", font=font(22, True), fill=MUTED)

    # A restrained three-stage visual establishes the narrative without implying
    # that this illustrative decoration is a live-data status indicator.
    nodes = [(1585, "HEADLINE", "#2ec4b6"), (1980, "RISK SIGNAL", BLUE), (2350, "SCENARIO", ROSE)]
    for idx in range(len(nodes) - 1):
        x0, _label, _color = nodes[idx]
        x1, _label2, _color2 = nodes[idx + 1]
        draw.line((x0, 420, x1, 420), fill="#35536c", width=5)
        draw.polygon([(x1 - 15, 420), (x1 - 32, 409), (x1 - 32, 431)], fill="#35536c")
    for x, label, color in nodes:
        draw.ellipse((x - 58, 362, x + 58, 478), fill=CARD, outline=color, width=5)
        draw.ellipse((x - 14, 406, x + 14, 434), fill=color)
        label_w = draw.textlength(label, font=font(18, True))
        draw.text((x - label_w / 2, 510), label, font=font(18, True), fill=WHITE)

    draw.line((100, 1115, WIDTH - 100, 1115), fill="#2b4058", width=2)
    draw.text((104, 1156), "SHARAN R", font=font(30, True), fill=WHITE)
    draw.text((104, 1202), "Vellore Institute of Technology (VIT)", font=font(23), fill=MUTED)
    draw.text((WIDTH - 910, 1160), "12,000", font=font(33, True), fill=ACCENT)
    draw.text((WIDTH - 910, 1206), "synthetic text records", font=font(18), fill=MUTED)
    draw.text((WIDTH - 610, 1160), "2,400", font=font(33, True), fill=BLUE)
    draw.text((WIDTH - 610, 1206), "fictional holdings", font=font(18), fill=MUTED)
    draw.text((WIDTH - 310, 1160), "2", font=font(33, True), fill=ROSE)
    draw.text((WIDTH - 310, 1206), "live RSS publishers", font=font(18), fill=MUTED)
    draw.text((WIDTH - 170, 1346), "01 / 07", font=font(20, True), fill=ACCENT)
    return image


def draw_problem() -> Image.Image:
    image = slide_frame(
        "The decision gap",
        "The hard part is not finding a headline. It is translating it into an exposure decision.",
        2, "01  |  Problem & approach",
    )
    draw = ImageDraw.Draw(image)
    panel(draw, (96, 330, 1180, 1015), "ILLUSTRATIVE SCENARIO  ·  FICTIONAL COMPANY", AMBER)
    draw.text((142, 408), "“Trade sanctions threaten", font=font(42, True), fill=WHITE)
    draw.text((142, 465), "critical supply routes.”", font=font(42, True), fill=WHITE)
    draw.text((142, 570), "One headline. Three analyst questions.", font=font(26, True), fill=AMBER)
    prompts = [
        ("01", "What kind of event is this?"),
        ("02", "How adverse and how material?"),
        ("03", "Which exposures should I inspect?"),
    ]
    y = 635
    for n, text in prompts:
        draw.ellipse((144, y, 185, y + 41), fill="#24364b")
        draw.text((154, y + 9), n, font=font(17, True), fill=AMBER)
        draw.text((210, y + 5), text, font=font(23), fill=WHITE)
        y += 76
    draw.text((142, 900), "SOURCE  ·  SYNTHETIC DEMO EXAMPLE", font=font(17, True), fill=MUTED)

    panel(draw, (1230, 330, 2463, 1015), "FROM READING TO REVIEW", BLUE)
    flow = [
        ("01", "STRUCTURE", "Classify as Geopolitical"),
        ("02", "PRIORITIZE", "Estimate sentiment + impact"),
        ("03", "INVESTIGATE", "Apply a defined portfolio scenario"),
    ]
    y = 420
    for n, title, body in flow:
        draw.rounded_rectangle((1280, y, 1400, y + 92), radius=16, fill="#18314a")
        draw.text((1310, y + 26), n, font=font(31, True), fill=BLUE)
        draw.text((1440, y + 4), title, font=font(18, True), fill=BLUE)
        draw.text((1440, y + 36), body, font=font(26, True), fill=WHITE)
        y += 145
    draw.text((1282, 890), "Decision support — not automated investment advice.", font=font(21), fill=MUTED)

    draw.rounded_rectangle((98, 1070, 2463, 1234), radius=16, fill="#10283a", outline="#214b5c", width=2)
    draw.text((130, 1095), "DESIGN PRINCIPLE", font=font(18, True), fill=ACCENT)
    draw.text((130, 1140), "Keep source provenance, model output and scenario assumptions visible at every step.",
              font=font(28, True), fill=WHITE)
    return image


def draw_architecture_slide(diagram: Image.Image) -> Image.Image:
    # The standalone architecture image already has a title, legend and caveats.
    # Preserve its native aspect ratio to prevent distortion on the slide.
    return diagram.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def draw_engine() -> Image.Image:
    image = slide_frame(
        "How a headline becomes a signal",
        "Four explicit stages produce an auditable signal contract — with model and rule responsibilities separated.",
        4, "03  |  Implementation",
    )
    draw = ImageDraw.Draw(image)
    cards = [
        ("01", "INGEST & NORMALIZE", "#2ec4b6",
         ["BBC + CNBC RSS", "Parallel 60-second polling", "Dedup + provenance tags"]),
        ("02", "FINBERT SENTIMENT", BLUE,
         ["Local ProsusAI FinBERT", "Positive / negative / neutral", "Signed confidence in [-1, 1]"]),
        ("03", "EVENT CLASSIFICATION", AMBER,
         ["Keyword-based event rules", "Five named event classes", "General Market fallback"]),
        ("04", "IMPACT ESTIMATE", ROSE,
         ["Category base score", "+ round(2 x |sentiment|)", "Clamped to [1, 10]"]),
    ]
    x0, y0, card_w, card_h, gap = 96, 360, 565, 410, 26
    for idx, (number, title, color, lines) in enumerate(cards):
        x = x0 + idx * (card_w + gap)
        panel(draw, (x, y0, x + card_w, y0 + card_h), title, color)
        draw.ellipse((x + 30, y0 + 82, x + 92, y0 + 144), fill="#1a2d43")
        draw.text((x + 47, y0 + 96), number, font=font(21, True), fill=color)
        yy = y0 + 178
        for line in lines:
            wrapped_text(draw, line, (x + 32, yy), card_w - 64, 22, WHITE, 1.35)
            yy += 62
        if idx < len(cards) - 1:
            mid_y = y0 + card_h / 2
            draw.line((x + card_w + 3, mid_y, x + card_w + gap - 6, mid_y), fill="#49677e", width=4)
            draw.polygon(
                [(x + card_w + gap - 6, mid_y), (x + card_w + gap - 20, mid_y - 10),
                 (x + card_w + gap - 20, mid_y + 10)],
                fill="#49677e",
            )

    panel(draw, (96, 820, 2464, 1198), "API SIGNAL CONTRACT", ACCENT)
    fields = [
        ("SENTIMENT", "-1.0 to +1.0"),
        ("EVENT", "category label"),
        ("IMPACT", "1 to 10"),
        ("TRACEABILITY", "source · time · provenance"),
    ]
    field_w = 545
    for idx, (label, detail) in enumerate(fields):
        x = 134 + idx * 575
        draw.text((x, 910), label, font=font(18, True), fill=ACCENT)
        wrapped_text(draw, detail, (x, 950), field_w, 26, WHITE)
    draw.text(
        (132, 1085),
        "Honest boundary: event classification and impact are heuristic rules; UI highlights are keyword cues, not FinBERT explanations.",
        font=font(20), fill=MUTED,
    )
    return image


def draw_stress() -> Image.Image:
    image = slide_frame(
        "Module B  |  From event to portfolio scenario",
        "A geopolitical example using a fictional wholesale-style portfolio and a predefined shock vector.",
        5, "04  |  Strategic stress testing",
    )
    draw = ImageDraw.Draw(image)
    panel(draw, (96, 330, 1180, 820), "GEOPOLITICAL SHOCK ASSUMPTIONS", ROSE)
    shock_rows = [
        ("Equities", "-10.0%"),
        ("Interest rates", "+2.0 pp"),
        ("Credit spreads", "+1.5 pp"),
        ("FX factor", "-5.0%"),
    ]
    y = 410
    for label, value in shock_rows:
        draw.text((145, y), label, font=font(24), fill=WHITE)
        draw.text((880, y), value, font=font(24, True), fill=ROSE)
        draw.line((145, y + 47, 1115, y + 47), fill="#253b53", width=2)
        y += 82
    draw.text((145, 755), "Trigger example: impact > 7  |  dashboard threshold = 8", font=font(19, True), fill=MUTED)

    panel(draw, (1230, 330, 2463, 820), "BUNDLED SYNTHETIC DATASET RESULT", BLUE)
    draw.text((1280, 415), "BASELINE", font=font(18, True), fill=MUTED)
    draw.text((1280, 456), "GBP 14.69bn", font=font(49, True), fill=WHITE)
    draw.text((1280, 545), "STRESSED VALUE", font=font(18, True), fill=MUTED)
    draw.text((1280, 586), "GBP 13.39bn", font=font(49, True), fill=BLUE)
    draw.rounded_rectangle((2075, 448, 2388, 682), radius=22, fill="#342231", outline=ROSE, width=2)
    draw.text((2115, 480), "-8.80%", font=font(46, True), fill=ROSE)
    draw.text((2120, 555), "-GBP 1.29bn", font=font(25, True), fill=WHITE)
    draw.text((1280, 700), "2,400 holdings  ·  240 fictional issuers  ·  GBP", font=font(20), fill=MUTED)

    panel(draw, (96, 875, 2463, 1198), "TRANSPARENT FIRST-ORDER SENSITIVITIES", ACCENT)
    formulas = [
        ("EQUITY", "value x beta x equity return"),
        ("RATES", "-value x duration x rate change"),
        ("CREDIT", "-value x credit duration x spread change"),
        ("FX", "currency exposure x FX return"),
    ]
    col_w = 560
    for idx, (label, formula) in enumerate(formulas):
        x = 132 + idx * 575
        draw.text((x, 960), label, font=font(18, True), fill=ACCENT)
        wrapped_text(draw, formula, (x, 1002), col_w - 20, 20, WHITE, 1.38)
    draw.text((132, 1138), "Estimate only: linear sensitivities, zero floor and simplified derivatives; not a calibrated forecast or valuation.",
              font=font(19), fill=MUTED)
    return image


def draw_evidence() -> Image.Image:
    image = slide_frame(
        "Evidence, data and boundaries",
        "A reproducible demo with public publisher inputs and explicitly fictional exposure data.",
        6, "05  |  Results & validation",
    )
    draw = ImageDraw.Draw(image)
    stats = [
        ("2", "publisher RSS feeds", "#2ec4b6"),
        ("12,000", "synthetic text records", AMBER),
        ("2,400", "synthetic holdings", BLUE),
        ("37", "tests passed at last run", ROSE),
    ]
    stat_w, stat_gap = 555, 32
    for idx, (value, label, color) in enumerate(stats):
        x = 96 + idx * (stat_w + stat_gap)
        draw.rounded_rectangle((x, 340, x + stat_w, 505), radius=18, fill=CARD, outline="#243d57", width=2)
        draw.text((x + 26, 362), value, font=font(48, True), fill=color)
        draw.text((x + 28, 438), label, font=font(19, True), fill=MUTED)

    panel(draw, (96, 555, 1230, 1055), "DATA PROVENANCE", "#2ec4b6")
    draw.text((140, 635), "REAL", font=font(18, True), fill="#2ec4b6")
    wrapped_text(draw, "BBC Business + CNBC public RSS; collection metadata retained; polled every 60 seconds.",
                 (140, 675), 1010, 22, WHITE)
    draw.text((140, 790), "SYNTHETIC", font=font(18, True), fill=AMBER)
    wrapped_text(draw, "Seed 20261008. Fictional entities, news/social text, GBP holdings, and bounded sensitivities. No confidential client data.",
                 (140, 830), 1010, 22, WHITE)
    draw.text((140, 970), "No live Twitter/X integration or market-price stream.", font=font(19, True), fill=MUTED)

    panel(draw, (1270, 555, 2463, 1055), "WHAT VERIFICATION MEANS", BLUE)
    checks = [
        ("VERIFIED", "Publisher collection, local inference path, API behavior, scenario math and tests."),
        ("NOT CLAIMED", "Held-out FinBERT accuracy, calibrated impact prediction or measured analyst time saved."),
        ("REPRODUCIBILITY", "Bundled CSV/JSONL, manifest, fixed seed and documented local run command."),
    ]
    y = 635
    for label, body in checks:
        draw.text((1315, y), label, font=font(17, True), fill=BLUE)
        wrapped_text(draw, body, (1515, y - 1), 875, 19, WHITE, 1.35)
        y += 120
    draw.rounded_rectangle((96, 1100, 2463, 1215), radius=14, fill="#251d27", outline="#5b3c4a", width=2)
    draw.text((128, 1125), "DOMAIN CAVEAT", font=font(17, True), fill=ROSE)
    draw.text((340, 1125), "RSS polling is not push streaming. Synthetic scenario P&L is illustrative, not a forecast.",
              font=font(22), fill=WHITE)
    return image


def draw_close() -> Image.Image:
    image = slide_frame(
        "A traceable path from news to risk review",
        "Designed to support analyst triage and consistent what-if exploration — not replace expert judgment.",
        7, "06  |  Domain impact & next steps",
    )
    draw = ImageDraw.Draw(image)
    panel(draw, (96, 340, 1530, 925), "THE REVIEWER WALKTHROUGH", ACCENT)
    demo_steps = [
        ("01", "Confirm live source + FinBERT status"),
        ("02", "Analyze the fictional Debt default case"),
        ("03", "Set threshold 8; test Trade sanctions"),
        ("04", "Inspect portfolio change + holding drivers"),
        ("05", "Open API docs and synthetic-data manifest"),
    ]
    y = 432
    for number, text in demo_steps:
        draw.ellipse((138, y, 190, y + 52), fill="#203449")
        draw.text((151, y + 13), number, font=font(16, True), fill=ACCENT)
        draw.text((220, y + 10), text, font=font(24, True), fill=WHITE)
        y += 91

    panel(draw, (1580, 340, 2463, 925), "NEXT ITERATIONS", BLUE)
    next_steps = [
        "Evaluate on unseen headlines",
        "Calibrate severity with expert labels",
        "Improve entity-to-exposure mapping",
        "Extend derivative valuation",
    ]
    y = 440
    for text in next_steps:
        draw.ellipse((1630, y + 5, 1648, y + 23), fill=BLUE)
        wrapped_text(draw, text, (1674, y), 710, 21, WHITE)
        y += 93
    draw.text((1630, 825), "AI assistance used with review and disclosure.", font=font(16), fill=MUTED)

    draw.rounded_rectangle((96, 1000, 2463, 1214), radius=20, fill="#10283a", outline="#285264", width=2)
    draw.text((136, 1032), "TRACEABILITY", font=font(17, True), fill=ACCENT)
    draw.text((136, 1072), "HEADLINE", font=font(30, True), fill=WHITE)
    draw.text((393, 1072), "→", font=font(31, True), fill=ACCENT)
    draw.text((455, 1072), "SIGNAL", font=font(30, True), fill=WHITE)
    draw.text((655, 1072), "→", font=font(31, True), fill=ACCENT)
    draw.text((718, 1072), "SCENARIO", font=font(30, True), fill=WHITE)
    draw.text((953, 1072), "→", font=font(31, True), fill=ACCENT)
    draw.text((1017, 1072), "PORTFOLIO IMPACT", font=font(30, True), fill=WHITE)
    draw.text((136, 1145), "Public repo: github.com/shaaran-r/vit-sharan-r-hackathon",
              font=font(18), fill=MUTED)
    draw.text((WIDTH - 525, 1145), "Demo video: pending", font=font(18, True), fill=AMBER)
    return image


def interactive_html(slides: list[Image.Image], notes: list[str]) -> str:
    encoded_slides = []
    for slide in slides:
        output = BytesIO()
        slide.save(output, format="PNG", optimize=True)
        encoded_slides.append(base64.b64encode(output.getvalue()).decode("ascii"))
    images = "\n".join(
        f'<img class="deck-slide{" active" if idx == 0 else ""}" src="data:image/png;base64,{data}" alt="Slide {idx + 1} of 7" />'
        for idx, data in enumerate(encoded_slides)
    )
    nav = "".join(
        f'<button type="button" class="dot{" active" if idx == 0 else ""}" aria-label="Go to slide {idx + 1}" aria-current="{"true" if idx == 0 else "false"}" data-slide="{idx}">{idx + 1:02d}</button>'
        for idx in range(len(slides))
    )
    notes_html = "".join(
        f'<section class="note{" active" if idx == 0 else ""}" data-note="{idx}"><strong>Slide {idx + 1} presenter note</strong><p>{html.escape(note)}</p></section>'
        for idx, note in enumerate(notes)
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#08111f"><title>Signal &amp; Stress | Interactive Jury Deck</title>
<style>
:root{{--bg:#08111f;--panel:#102137;--ink:#eef5ff;--muted:#b6c7da;--accent:#63d6c4}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Segoe UI,Arial,sans-serif}}
.top{{height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 22px;border-bottom:1px solid #294056}}
.brand{{font-weight:700;letter-spacing:.04em}}.actions{{display:flex;gap:8px}}
button,a{{font:inherit}}.actions button,.actions a,.controls button,.dot{{color:var(--ink);background:var(--panel);border:1px solid #36516b;border-radius:8px;padding:9px 12px;text-decoration:none;cursor:pointer}}
button:hover,.actions a:hover,.dot:hover{{border-color:var(--accent)}}button:focus-visible,a:focus-visible{{outline:3px solid var(--accent);outline-offset:2px}}
main{{min-height:calc(100vh - 125px);display:grid;place-items:center;padding:22px}}
.stage{{width:min(94vw,calc((100vh - 205px)*1.7778));position:relative;box-shadow:0 24px 70px #0009;border:1px solid #294056;border-radius:10px;overflow:hidden;background:#08111f}}
.deck-slide{{display:none;width:100%;height:auto;aspect-ratio:16/9}}.deck-slide.active{{display:block;animation:enter .24s ease-out}}
@keyframes enter{{from{{opacity:.5;transform:translateY(4px)}}to{{opacity:1;transform:none}}}}
.controls{{display:flex;align-items:center;justify-content:center;gap:10px;padding:10px}}
.dots{{display:flex;gap:5px}}.dot{{padding:6px 9px;font-size:.8rem}}.dot.active{{border-color:var(--accent);color:var(--accent);background:#12313a}}
.counter{{min-width:66px;text-align:center;color:var(--muted);font-variant-numeric:tabular-nums}}
.notes{{max-width:960px;margin:0 auto 24px;padding:0 18px}}.note{{display:none;color:var(--muted);line-height:1.5}}.note.active{{display:block}}
.note strong{{color:var(--accent)}}.note p{{margin:6px 0}}
@media(max-width:650px){{.top{{padding:0 10px}}.brand{{font-size:.85rem}}.actions button,.actions a{{padding:7px;font-size:.78rem}}main{{padding:10px}}.dots{{gap:2px}}.dot{{padding:5px 6px;font-size:.7rem}}}}
@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation:none!important;scroll-behavior:auto!important}}}}
</style></head>
<body><header class="top"><div class="brand">SIGNAL &amp; STRESS <span style="color:var(--muted);font-weight:400">| JURY PRESENTATION</span></div>
<div class="actions"><a href="https://github.com/shaaran-r/vit-sharan-r-hackathon" target="_blank" rel="noopener">Repository ↗</a><a href="presentation.pdf" download>Download PDF ↓</a><button id="full" type="button">Fullscreen</button></div></header>
<main><div class="stage" aria-live="polite" aria-label="Presentation slides">{images}</div></main>
<nav class="controls" aria-label="Slide controls"><button id="prev" type="button" aria-label="Previous slide">← Prev</button><div class="dots">{nav}</div><span class="counter" id="counter">01 / 07</span><button id="next" type="button" aria-label="Next slide">Next →</button></nav>
<aside class="notes" aria-live="polite">{notes_html}</aside>
<script>
const slides=[...document.querySelectorAll('.deck-slide')],dots=[...document.querySelectorAll('.dot')],notes=[...document.querySelectorAll('.note')],counter=document.getElementById('counter');let current=0;
function go(i){{current=(i+slides.length)%slides.length;slides.forEach((x,n)=>x.classList.toggle('active',n===current));dots.forEach((x,n)=>{{x.classList.toggle('active',n===current);x.setAttribute('aria-current',n===current?'true':'false')}});notes.forEach((x,n)=>x.classList.toggle('active',n===current));counter.textContent=String(current+1).padStart(2,'0')+' / '+String(slides.length).padStart(2,'0')}}
document.getElementById('prev').onclick=()=>go(current-1);document.getElementById('next').onclick=()=>go(current+1);dots.forEach(x=>x.onclick=()=>go(Number(x.dataset.slide)));
document.getElementById('full').onclick=()=>document.fullscreenElement?document.exitFullscreen():document.querySelector('.stage').requestFullscreen();
document.addEventListener('keydown',e=>{{if(['ArrowRight','PageDown',' '].includes(e.key)){{e.preventDefault();go(current+1)}}else if(['ArrowLeft','PageUp'].includes(e.key)){{e.preventDefault();go(current-1)}}else if(e.key==='Home')go(0);else if(e.key==='End')go(slides.length-1)}});
</script></body></html>"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    diagram = architecture()
    diagram.save(OUT / "architecture.png", dpi=(200, 200))

    slides = [
        draw_cover(),
        draw_problem(),
        draw_architecture_slide(diagram),
        draw_engine(),
        draw_stress(),
        draw_evidence(),
        draw_close(),
    ]
    slides[0].save(OUT / "presentation.pdf", save_all=True, append_images=slides[1:], resolution=160)

    presenter_notes = [
        "Introduce the project, candidate and scope. State that this is the AI/NLP Risk Engine plus Module B.",
        "Frame the illustrative headline as fictional. Explain that the aim is a traceable review workflow, not automatic trading.",
        "Walk from source through processing and serving to stress testing. Mention RSS polling is not publisher push streaming.",
        "Explain FinBERT sentiment separately from rule-based event classification and impact. The impact formula is a heuristic, not a trained severity model.",
        "Read the displayed portfolio values. The bundled reference is GBP 14.69bn to GBP 13.39bn, about -8.80%; do not present it as a forecast.",
        "Distinguish implementation tests and smoke checks from held-out accuracy, calibration, or measured business savings.",
        "Finish with the analyst workflow and next steps. Demo video is pending; only claim AI-use statements that are true for your work.",
    ]
    (OUT / "presentation.html").write_text(
        interactive_html(slides, presenter_notes), encoding="utf-8"
    )
    print(f"Saved architecture PNG and {len(slides)}-slide PDF + interactive HTML deck in {OUT}")


if __name__ == "__main__":
    main()

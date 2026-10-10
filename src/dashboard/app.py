import os
import time
from io import StringIO
from typing import Any

import pandas as pd
import requests
import streamlit as st
from src.dashboard.examples import HEADLINE_EXAMPLES
from src.dashboard.highlights import highlight_headline


API_URL = os.environ.get("RISK_API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Signal & Stress | Risk Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --ink: #eef5ff; --muted: #9aabc2; --line: rgba(170, 199, 233, .16); }
    .stApp {
        background:
          radial-gradient(ellipse at 80% -10%, rgba(11, 121, 129, .23), transparent 34%),
          radial-gradient(ellipse at 10% 0%, rgba(39, 82, 150, .22), transparent 35%),
          #08111f;
        color: var(--ink);
    }
    [data-testid="stHeader"] { background: rgba(8, 17, 31, .65); }
    [data-testid="stSidebar"] { background: #0b1626; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    .stMarkdown p, [data-testid="stWidgetLabel"] { color: #d2deed; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #9aabc2; }
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label { color: #d2deed; }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(21, 39, 61, .92), rgba(12, 25, 42, .92));
        border: 1px solid var(--line); border-radius: 16px; padding: 16px 18px;
    }
    [data-testid="stMetricLabel"] { color: #9aabc2; }
    [data-testid="stMetricValue"] { color: #f2f7ff; }
    [data-testid="stMetricDelta"] { color: #65d6ba; }
    div[data-testid="stForm"], div[data-testid="stExpander"] {
        border: 1px solid var(--line); border-radius: 16px; background: rgba(13, 27, 45, .76);
    }
    div.stButton > button, div.stFormSubmitButton > button {
        border-radius: 10px; border: 1px solid rgba(68, 204, 188, .48);
        background: linear-gradient(100deg, #087f8c, #176a9b); color: white;
        font-weight: 650; transition: all .18s ease;
    }
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        border-color: #73ead6; color: white; transform: translateY(-1px);
    }
    button[role="tab"] { font-weight: 650; }
    .hero {
        padding: 26px 30px 24px; border: 1px solid rgba(133, 183, 221, .19);
        border-radius: 20px; margin: 4px 0 22px;
        background: linear-gradient(110deg, rgba(18, 42, 64, .96), rgba(10, 30, 47, .89) 62%, rgba(9, 61, 70, .74));
        box-shadow: 0 18px 48px rgba(0, 0, 0, .19);
    }
    .hero-kicker { color: #63d6c4; text-transform: uppercase; letter-spacing: .16em; font-size: .72rem; font-weight: 750; }
    .hero h1 { color: #f4f8ff; margin: 8px 0 7px; font-size: 2.25rem; letter-spacing: -.04em; }
    .hero p { color: #b6c7da; margin: 0; max-width: 760px; }
    .section-note { color: #9aabc2; font-size: .91rem; }
    .signal-up { color: #5fe0b5; font-weight: 700; }
    .signal-down { color: #ff8291; font-weight: 700; }
    .signal-neutral { color: #a6b6ca; font-weight: 700; }
    .headline-cues {
        background: #102137; border: 1px solid var(--line); border-radius: 12px;
        padding: 18px; line-height: 2; white-space: pre-wrap; overflow-wrap: anywhere;
    }
    .headline-cues mark { padding: 3px 5px; border-radius: 5px; font-weight: 750; }
    .cue-negative { background: #632638; color: #ffe5e9; }
    .cue-positive { background: #155444; color: #d7fff0; }
    .cue-trigger { background: #665016; color: #fff1bf; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_json(path: str, params: tuple[tuple[str, str], ...] = (), refresh_bucket: int = 0) -> Any:
    # The bucket changes the dashboard cache key without changing the API request.
    response = requests.get(f"{API_URL}{path}", params=dict(params), timeout=45)
    response.raise_for_status()
    return response.json()


def api_error(error: requests.RequestException) -> str:
    response = getattr(error, "response", None)
    if response is not None:
        try:
            detail = response.json().get("detail")
            if detail:
                return str(detail)
        except (ValueError, AttributeError):
            pass
    return str(error)


def render_stress_result(result: dict[str, Any]) -> None:
    currency = result["currency"]
    st.caption(
        f"Hypothetical scenario estimate | {result['source_reference']} | "
        f"Valuation date: {result['valuation_date']} | {result['provenance_status']}"
    )
    before, after, change = st.columns(3)
    before.metric(
        "Synthetic baseline" if result.get("data_origin") == "synthetic" else "Reported baseline",
        f"{currency} {result['portfolio_before']:,.0f}",
    )
    after.metric("Estimated scenario value", f"{currency} {result['portfolio_after']:,.0f}")
    change.metric(
        "Scenario impact",
        f"{result['change_percent']:+.2f}%",
        f"{currency} {result['change']:+,.0f}",
        delta_color="normal",
    )
    scenario = result["scenario"]
    st.caption(
        "Scenario shocks · "
        f"Equities {scenario['equity_return']:+.1%} · "
        f"Rates +{scenario['rate_change']:.1%} · "
        f"Credit spreads +{scenario['spread_change']:.1%} · "
        f"FX {scenario['fx_return']:+.1%}"
    )
    holdings = pd.DataFrame(result["holdings"])
    grouped = holdings.groupby("asset_type")[["baseline_value", "stressed_value"]].sum()
    st.bar_chart(
        grouped,
        color=["#31b7c8", "#ef788c"],
    )
    st.dataframe(holdings, width="stretch", hide_index=True)


def simulate_signal(signal: dict[str, Any], portfolio: dict[str, Any] | None, threshold: int) -> None:
    if portfolio is None:
        st.info("Choose the synthetic demo portfolio or validate a real portfolio upload.")
        return
    if signal["event_classification"] == "General Market":
        st.info("No scenario is defined for this event category.")
        return
    try:
        response = requests.post(
            f"{API_URL}/stress-test",
            json={
                "event_id": signal["event_id"],
                "event_classification": signal["event_classification"],
                "impact_score": signal["impact_score"],
                "portfolio": portfolio,
                "min_impact": threshold,
            },
            timeout=45,
        )
        response.raise_for_status()
        outcome = response.json()
        if outcome["triggered"]:
            render_stress_result(outcome["result"])
        else:
            st.info(f"Scenario not triggered: {outcome['reason']}")
    except requests.RequestException as error:
        st.error(f"Stress simulation failed: {api_error(error)}")


st.markdown(
    """
    <div class="hero">
      <div class="hero-kicker">Financial risk intelligence · Live workbench</div>
      <h1>Signal &amp; Stress</h1>
      <p>Real publisher news meets a clearly labeled, continuously replayed simulation. Explore thousands of fictional exposures and hypothetical risk scenarios.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### ◈ Control room")
    st.caption("Choose sources, set the trigger and refresh your workspace.")
    st.caption("Real news: BBC and CNBC RSS, collected continuously by the API every 60 seconds.")
    st.caption("Use Signal explorer to search the fetched headlines.")
    news_choice = st.radio("Signal input", ["Hybrid live + simulation", "Live publishers only"], index=1)
    news_mode = "hybrid" if news_choice == "Hybrid live + simulation" else "live"
    portfolio_choice = st.radio("Portfolio input", ["Large synthetic demo", "Upload real holdings"])
    auto_update = st.toggle("Auto-update dashboard every 10 seconds", value=True)
    upload = None
    authorized = False
    if portfolio_choice == "Upload real holdings":
        upload = st.file_uploader("Real portfolio CSV", type=["csv"], max_upload_size=2)
        source_reference = st.text_input("Portfolio source/reference", placeholder="Public report URL or authorized dataset reference")
        valuation_date = st.date_input("Portfolio valuation date")
        currency = st.text_input("Portfolio base currency", value="", placeholder="GBP, USD, EUR", max_chars=3)
        authorized = st.checkbox("I confirm these are real, authorized, non-confidential holdings.")
        st.caption("All values must be in one base currency. No missing exposures are invented.")
    else:
        st.caption("2,400 fictional holdings, 240 fictional issuers, five asset types. All values in GBP.")
    impact_threshold = st.slider("Stress trigger threshold", 1, 10, 7)
    refresh = st.button("Refresh workspace", width="stretch")
    if refresh:
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption(f"API: {API_URL}")
    st.caption("Signals are demonstration outputs, not investment advice.")


st.session_state["simulation_clock_tick"] = int(time.time()) // 10


@st.fragment(run_every="10s" if auto_update else None)
def simulation_clock() -> None:
    tick = int(time.time()) // 10
    previous = st.session_state.get("simulation_clock_tick", tick)
    st.session_state["simulation_clock_tick"] = tick
    st.caption(
        f"Dashboard clock: {time.strftime('%H:%M:%S', time.gmtime())} UTC | "
        + ("real publisher polling" if news_mode == "live" else "real publisher polling + fictional replay")
    )
    if previous != tick:
        st.rerun()


simulation_clock()

try:
    health = fetch_json("/health")
    if health.get("status") != "ok":
        st.error("Risk API health check returned an unexpected status.")
        st.stop()
except requests.RequestException as error:
    st.error(f"Risk API is unavailable: {api_error(error)}")
    st.info("Start the application with `python run_demo.py`, then refresh this page.")
    st.stop()

try:
    params = (("mode", news_mode),)
    signals = fetch_json("/signals", params, int(time.time()) // 10 if auto_update else 0)
except requests.RequestException as error:
    st.error(f"Selected signal input is unavailable: {api_error(error)}.")
    signals = []

portfolio_payload = None
portfolio_summary = None
stress_results = []
demo = None
if portfolio_choice == "Large synthetic demo":
    try:
        demo = fetch_json("/simulation/portfolio")
        portfolio_payload = demo["portfolio"]
        portfolio_summary = {**demo["summary"], "provenance_status": "Synthetic fictional holdings"}
        st.warning("DEMO SIMULATION: all synthetic holdings, news and social posts are fictional. Only publisher-labeled headlines are real.")
    except requests.RequestException as error:
        st.error(f"Could not load synthetic portfolio: {api_error(error)}")
if upload is not None and authorized:
    try:
        candidate = {
            "csv_text": upload.getvalue().decode("utf-8-sig"),
            "source_reference": source_reference.strip(),
            "valuation_date": valuation_date.isoformat(),
            "currency": currency.strip().upper(),
            "authorized_real_data": authorized,
        }
        response = requests.post(f"{API_URL}/portfolio/validate", json=candidate, timeout=10)
        response.raise_for_status()
        portfolio_summary = response.json()
        portfolio_payload = candidate
    except UnicodeDecodeError:
        st.error("Portfolio CSV must be UTF-8 encoded.")
    except requests.RequestException as error:
        st.error(f"Portfolio validation failed: {api_error(error)}")
if portfolio_payload is None:
    st.info("Choose the synthetic demo portfolio or upload and validate real holdings to enable stress testing.")
elif signals:
    try:
        response = requests.post(
            f"{API_URL}/stress-tests",
            json={"portfolio": portfolio_payload, "min_impact": impact_threshold,
                  "mode": news_mode, "representative_only": True},
            timeout=45,
        )
        response.raise_for_status()
        stress_results = response.json()
    except requests.RequestException as error:
        st.error(f"Could not load portfolio stress results: {api_error(error)}")

if signals:
    live_sources = sorted({
        signal.get("source", "unknown")
        for signal in signals if signal.get("data_origin") == "live_publisher"
    })
    source_labels = {
        "bbc_business_rss": "BBC Business RSS",
        "cnbc_business_rss": "CNBC Business RSS",
        "alpha_vantage_news": "Alpha Vantage financial news",
    }
    st.info(
        "Live news source: "
        + (", ".join(source_labels.get(source, source) for source in live_sources) or "none currently available")
        + ". Synthetic sources are separate and explicitly labeled."
    )
    if news_mode == "hybrid" and not live_sources:
        st.warning("Live publishers are unavailable. Only the explicitly selected simulation is currently updating.")

try:
    news_status = fetch_json("/news-status", refresh_bucket=int(time.time()) // 10 if auto_update else 0)
    provider_status = news_status["alpha_vantage"]
    if provider_status["status"] == "unavailable":
        st.warning(provider_status["message"])
    elif provider_status["status"] == "ok":
        st.caption(provider_status["message"])
    model_status = news_status["sentiment"]
    if model_status["trained_model"]:
        st.success("Trained FinBERT sentiment model active. Event and impact scores remain heuristic.")
    elif model_status["backend"] == "finbert":
        st.warning(f"FinBERT status: {model_status['status']}. Model inference must succeed before it is marked active.")
    else:
        st.warning("Lexicon sentiment active; a trained model is not running.")
    collection = news_status["live_news"]
    st.caption(
        f"Real publisher collection: {collection['article_count']} records | "
        f"Last collection: {collection['last_collection'] or 'starting'} | "
        f"Poll interval: {collection['poll_seconds']} seconds. No publisher latency guarantee."
    )
    for publisher, status in collection["providers"].items():
        if status["status"] != "ok":
            st.warning(f"{publisher}: {status['message']}")
except requests.RequestException as error:
    st.warning(f"Could not check news provider status: {api_error(error)}")

signals_frame = pd.DataFrame(signals)
if not signals_frame.empty:
    if "entities" in signals_frame:
        signals_frame["entity_text"] = signals_frame["entities"].apply(
            lambda entities: ", ".join(entities) if isinstance(entities, list) else str(entities)
        )
    else:
        signals_frame["entity_text"] = ""
    signals_frame["source"] = signals_frame["source"].astype(str)

negative_count = int((signals_frame["sentiment_score"] < -0.15).sum()) if not signals_frame.empty else 0
high_count = int((signals_frame["impact_score"] >= impact_threshold).sum()) if not signals_frame.empty else 0
portfolio_value = portfolio_summary["baseline_value"] if portfolio_summary else None

metric_row_one = st.columns(2)
metric_row_one[0].metric("Signals", len(signals))
metric_row_one[1].metric("Negative", negative_count)
metric_row_two = st.columns(2)
metric_row_two[0].metric(f"Impact ≥ {impact_threshold}", high_count)
metric_row_two[1].metric(
    "Portfolio baseline",
    f"{portfolio_summary['currency']} {portfolio_value:,.0f}" if portfolio_summary else "Awaiting upload",
)

overview, analyzer, explorer, stress_lab, datasets = st.tabs(
    ["◈ Overview", "✦ Analyze text", "⌕ Signal explorer", "▥ Stress-test lab", "Dataset studio"]
)

with overview:
    st.subheader("Risk pulse")
    st.markdown(
        '<div class="section-note">Sentiment and severity across the current feed.</div>',
        unsafe_allow_html=True,
    )
    if not signals_frame.empty:
        pulse = signals_frame[
            ["event_id", "sentiment_score", "impact_score", "event_classification"]
        ].copy()
        pulse = pulse.rename(
            columns={
                "event_id": "Signal",
                "sentiment_score": "Sentiment",
                "impact_score": "Impact",
                "event_classification": "Event",
            }
        )
        pulse["Impact"] = pulse["Impact"].astype(float)
        st.scatter_chart(
            pulse,
            x="Sentiment",
            y="Impact",
            color="Event",
            size="Impact",
            height=340,
        )
        st.caption("Further left means more negative sentiment; higher points indicate greater estimated impact.")
    else:
        st.info("No signal records are available.")

    st.subheader("Stress snapshot")
    if stress_results:
        snapshot = pd.DataFrame(
            [
                {
                    "Event": result["event_classification"],
                    "Impact": result["impact_score"],
                    "Change": result["change"],
                    "Change (%)": result["change_percent"],
                }
                for result in stress_results
            ]
        )
        st.dataframe(snapshot, width="stretch", hide_index=True)
        selected = st.selectbox(
            "Preview a triggered event",
            options=range(len(stress_results)),
            format_func=lambda index: (
                f"{stress_results[index]['event_classification']} · "
                f"impact {stress_results[index]['impact_score']}"
            ),
            key="overview_stress_select",
        )
        preview = stress_results[selected]
        st.metric("Estimated scenario move", f"{preview['change_percent']:+.2f}%", f"{preview['currency']} {preview['change']:+,.0f}", delta_color="normal")
    else:
        st.info("No scenario results available. A validated portfolio and a supported high-impact event are required.")

    with st.expander("About the data and assumptions"):
        st.write(
            "Publisher news is real; synthetic_news and synthetic_social are fictional replay records. "
            "Portfolio inputs can be a labeled synthetic demo or user-declared real holdings. "
            "Simulation timestamps show replay emission time, not real-world publication time."
        )
        st.write(
            "FinBERT sentiment is used when model weights are available. A local lexicon fallback can be "
            "selected with `SENTIMENT_BACKEND=lexicon`. Event categories and portfolio shocks are simplified demo rules."
        )

def render_headline_cues(text: str) -> None:
    markup, cues = highlight_headline(text)
    st.markdown(markup, unsafe_allow_html=True)
    st.caption("Red: negative cues | Green: positive cues | Amber: event triggers. Hover a highlighted phrase for its role.")
    for label, words in cues.items():
        if words:
            st.text(f"{label}: {', '.join(words)}")
    if not any(cues.values()):
        st.caption("No event or sentiment keywords matched. Model sentiment may still detect context.")
    st.caption(
        "Keyword cues are not a FinBERT explanation or a trading recommendation. "
        "They do not resolve negation, rumors or factual accuracy."
    )


def load_headline_example(index: int) -> None:
    example = HEADLINE_EXAMPLES[index]
    st.session_state["analysis_text"] = example["text"]
    st.session_state["analysis_entities"] = example["entities"]
    st.session_state.pop("latest_manual_signal", None)


with analyzer:
    st.subheader("Analyze a headline or event")
    st.markdown(
        '<div class="section-note">Paste text to generate a risk signal and immediately test its portfolio scenario.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("#### Quick-start cases")
    st.caption("Fictional examples, not published news. Click a case to fill the form, then analyze or edit it.")
    for start in (0, 3):
        columns = st.columns(3)
        for offset, column in enumerate(columns):
            index = start + offset
            example = HEADLINE_EXAMPLES[index]
            column.button(
                example["label"], key=f"headline_example_{index}",
                help=f"Load a fictional {example['category']} example",
                on_click=load_headline_example, args=(index,), width="stretch",
            )
    with st.form("text_analysis_form", clear_on_submit=False):
        analysis_text = st.text_area(
            "Text to analyze",
            placeholder="Paste a published headline or sourced event description...",
            height=130,
            max_chars=10_000,
            key="analysis_text",
        )
        entities_text = st.text_input("Entities (optional, comma-separated)", key="analysis_entities")
        submitted = st.form_submit_button("Analyze & run stress test", width="stretch")

    if submitted:
        if not analysis_text.strip():
            st.warning("Enter a headline or event description first.")
        else:
            is_example = any(analysis_text.strip() == example["text"] for example in HEADLINE_EXAMPLES)
            try:
                response = requests.post(
                    f"{API_URL}/analyze",
                    json={
                        "text": analysis_text,
                        "source": "synthetic_example" if is_example else "dashboard_input",
                        "data_origin": "synthetic" if is_example else "user_supplied",
                        "entities": [item.strip() for item in entities_text.split(",") if item.strip()],
                    },
                    timeout=45,
                )
                response.raise_for_status()
                analyzed = response.json()
                st.session_state["latest_manual_signal"] = analyzed
            except requests.RequestException as error:
                st.error(f"Analysis failed: {api_error(error)}")

    analyzed = st.session_state.get("latest_manual_signal")
    if analyzed:
        st.divider()
        st.markdown("#### Generated risk signal")
        st.caption(
            "Fictional quick-start example; not real news."
            if analyzed.get("data_origin") == "synthetic"
            else "User-supplied text; not independently verified."
        )
        sentiment = analyzed["sentiment_score"]
        sentiment_label = "Positive" if sentiment > 0.15 else "Negative" if sentiment < -0.15 else "Neutral"
        sentiment_color = "signal-up" if sentiment > 0.15 else "signal-down" if sentiment < -0.15 else "signal-neutral"
        st.markdown(f'<span class="{sentiment_color}">{sentiment_label}</span>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sentiment", f"{sentiment:+.2f}")
        c2.metric("Sentiment confidence", f"{analyzed.get('sentiment_confidence', 0):.0%}")
        st.caption(analyzed["analysis_method"])
        c3.metric("Event type", analyzed["event_classification"])
        c4.metric("Impact", f"{analyzed['impact_score']} / 10")
        st.markdown("#### Important words in the analyzed text")
        render_headline_cues(analyzed["text"])
        if analyzed["event_classification"] == "General Market":
            st.caption("No event trigger matched; no stress scenario is defined for General Market.")
        elif analyzed["impact_score"] >= impact_threshold:
            st.caption(f"Scenario threshold met: impact {analyzed['impact_score']} ≥ {impact_threshold}.")
        else:
            st.caption(f"Below scenario threshold: impact {analyzed['impact_score']} < {impact_threshold}.")

        simulate_signal(analyzed, portfolio_payload, impact_threshold)
    elif analysis_text.strip():
        st.markdown("#### Important words preview")
        render_headline_cues(analysis_text)

with explorer:
    st.subheader("Signal explorer")
    if signals_frame.empty:
        st.info("There are no records to explore.")
    else:
        filter_cols = st.columns([1, 1, 1.35])
        categories = sorted(signals_frame["event_classification"].dropna().unique().tolist())
        sources = sorted(signals_frame["source"].dropna().unique().tolist())
        chosen_categories = filter_cols[0].multiselect("Event category", categories, default=categories)
        chosen_sources = filter_cols[1].multiselect("Source", sources, default=sources)
        search_text = filter_cols[2].text_input("Search headline/entity", placeholder="Search text...")
        min_sentiment, max_sentiment = st.slider(
            "Sentiment range",
            min_value=-1.0,
            max_value=1.0,
            value=(-1.0, 1.0),
            step=0.05,
        )
        filtered = signals_frame[
            signals_frame["event_classification"].isin(chosen_categories)
            & signals_frame["source"].isin(chosen_sources)
            & signals_frame["sentiment_score"].between(min_sentiment, max_sentiment)
        ]
        if search_text.strip():
            text_match = (
                filtered["text"].str.contains(search_text, case=False, na=False, regex=False)
                | filtered["entity_text"].str.contains(search_text, case=False, na=False, regex=False)
            )
            filtered = filtered[text_match]
        st.caption(f"Showing {len(filtered)} of {len(signals_frame)} signals")
        show_columns = [
            column
            for column in (
                "timestamp", "source", "data_origin", "sector", "region", "entity_text",
                "sentiment_score", "sentiment_confidence",
                "event_classification", "impact_score", "text", "body", "dataset_timestamp", "url",
            )
            if column in filtered.columns
        ]
        st.dataframe(
            filtered[show_columns],
            width="stretch",
            hide_index=True,
            column_config={
                "sentiment_score": st.column_config.ProgressColumn(
                    "Sentiment",
                    min_value=-1.0,
                    max_value=1.0,
                    format="%.2f",
                ),
                "impact_score": st.column_config.ProgressColumn(
                    "Impact",
                    min_value=1,
                    max_value=10,
                    format="%d / 10",
                ),
                "url": st.column_config.LinkColumn("Article", display_text="Open source"),
            },
        )
        if not filtered.empty:
            st.download_button(
                "Download filtered signals as CSV",
                filtered[show_columns].to_csv(index=False).encode("utf-8"),
                file_name="risk-signals.csv",
                mime="text/csv",
            )

with stress_lab:
    st.subheader("Stress-test lab")
    st.markdown(
        '<div class="section-note">Select an event from the feed. The sidebar threshold controls whether its scenario triggers.</div>',
        unsafe_allow_html=True,
    )
    candidates = [
        signal
        for signal in signals
        if signal["event_classification"] in {
            "Geopolitical", "Macroeconomic", "Credit Event", "Merger/Acquisition", "Product Launch"
        }
    ]
    if not candidates:
        st.info("No supported event types are available in the current feed.")
    else:
        selected_index = st.selectbox(
            "Event to simulate",
            range(len(candidates)),
            format_func=lambda index: (
                f"{candidates[index]['event_classification']} · impact {candidates[index]['impact_score']} · "
                f"{candidates[index]['text'][:90]}"
            ),
        )
        selected_signal = candidates[selected_index]
        render_headline_cues(selected_signal["text"])
        simulate_signal(selected_signal, portfolio_payload, impact_threshold)

with datasets:
    st.subheader("Synthetic dataset studio")
    st.caption("Generated data is reproducible from seed 20261008. No fictional figure is a genuine observation.")
    try:
        catalogue = fetch_json("/simulation/status")
        cols = st.columns(3)
        cols[0].metric("Corpus events", f"{catalogue['event_count']:,}")
        cols[1].metric("Fictional holdings", f"{catalogue['holdings_count']:,}")
        cols[2].metric("Fictional issuers", f"{catalogue['entities_count']:,}")
        st.write(catalogue["methodology"])
        st.caption("6 events emitted per 10-second tick; latest 120 replay events displayed. The 12,000-record corpus cycles.")
        for filename, label in (("portfolio.csv", "Download full synthetic portfolio CSV"),
                                ("events.jsonl", "Download all synthetic news/social records"),
                                ("manifest.json", "Download generation manifest")):
            st.link_button(label, f"{API_URL}/simulation/download/{filename}")
        if demo:
            portfolio_frame = pd.read_csv(StringIO(demo["portfolio"]["csv_text"]))
            c1, c2 = st.columns(2)
            c1.bar_chart(portfolio_frame.groupby("asset_type")["notional"].sum(), color="#31b7c8")
            c2.bar_chart(portfolio_frame.groupby("sector")["notional"].sum(), color="#ef788c")
            st.dataframe(portfolio_frame, hide_index=True, width="stretch")
    except requests.RequestException as error:
        st.error(f"Dataset metadata is unavailable: {api_error(error)}")

st.markdown(
    '<div class="section-note">Signal &amp; Stress · Prototype results are illustrative and are not investment advice.</div>',
    unsafe_allow_html=True,
)

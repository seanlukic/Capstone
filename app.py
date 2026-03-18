import streamlit as st

from views.event_setup_page import render as render_event_setup_page
from views.landing_page import render as render_landing_page
from views.participant_setup_page import render as render_participant_setup_page
from views.results_page import render as render_results_page

st.set_page_config(page_title="Group Formation Studio", page_icon="groups", layout="wide")


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700&family=DM+Sans:wght@400;500;700&display=swap');
        :root {
            --bg: #090f1d;
            --card: #121b2e;
            --text: #edf2ff;
            --muted: #b7c2dc;
            --accent: #4f8cff;
            --accent-2: #25b5a8;
            --border: #273453;
        }

        .stApp {
            background:
                radial-gradient(circle at 10% 10%, rgba(79, 140, 255, 0.17), transparent 40%),
                radial-gradient(circle at 90% 5%, rgba(37, 181, 168, 0.14), transparent 38%),
                var(--bg);
            color: var(--text);
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1100px;
        }

        h1, h2, h3 {
            color: var(--text);
            letter-spacing: -0.01em;
        }

        .app-subtitle {
            color: var(--muted);
            margin-top: 0.35rem;
        }

        .hero {
            background: linear-gradient(125deg, #15213a 0%, #121b2e 100%);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1.3rem 1.1rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
        }

        .landing-shell {
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.9rem 1.4rem;
            margin: 0.3rem 0 1.1rem;
            background:
                radial-gradient(circle at 8% 12%, rgba(79, 140, 255, 0.23), transparent 42%),
                radial-gradient(circle at 88% 20%, rgba(37, 181, 168, 0.21), transparent 38%),
                linear-gradient(135deg, #121f38 0%, #101a2d 100%);
            box-shadow: 0 16px 42px rgba(4, 8, 18, 0.45);
        }

        .landing-kicker {
            text-transform: uppercase;
            letter-spacing: 0.09em;
            font-size: 0.78rem;
            color: #96c4ff;
            margin: 0 0 0.5rem 0;
            font-weight: 700;
            animation: fade-up 360ms ease-out both;
        }

        .landing-title {
            margin: 0 0 0.7rem 0;
            font-family: "Sora", "DM Sans", sans-serif;
            font-weight: 700;
            font-size: clamp(2rem, 4.8vw, 3rem);
            letter-spacing: -0.02em;
            line-height: 1.1;
            color: #f7fbff;
            animation: fade-up 480ms ease-out both;
        }

        .landing-subtitle {
            margin: 0;
            color: #c2d5f3;
            max-width: 60ch;
            font-size: 1.02rem;
            line-height: 1.55;
            animation: fade-up 620ms ease-out both;
        }

        .landing-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.85rem;
            margin-top: 1.05rem;
            animation: fade-up 740ms ease-out both;
        }

        .landing-metric {
            border: 1px solid #2a3a5f;
            border-radius: 12px;
            background: rgba(11, 19, 33, 0.62);
            padding: 0.72rem 0.82rem;
        }

        .landing-metric-label {
            color: #9eb4d7;
            font-size: 0.77rem;
            margin: 0 0 0.25rem 0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 700;
        }

        .landing-metric-value {
            margin: 0;
            color: #ffffff;
            font-size: 1rem;
            font-weight: 700;
        }

        .landing-feature {
            border: 1px solid #2a3a5f;
            border-radius: 16px;
            background: rgba(12, 18, 31, 0.72);
            padding: 0.95rem;
            height: 100%;
        }

        .landing-feature-title {
            margin: 0 0 0.35rem 0;
            color: #e8f1ff;
            font-size: 1rem;
            font-family: "Sora", "DM Sans", sans-serif;
            font-weight: 600;
        }

        .landing-feature-copy {
            margin: 0;
            color: #a8bddf;
            line-height: 1.45;
            font-size: 0.92rem;
        }

        .card {
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 0.85rem;
            background: var(--card);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
            height: 100%;
        }

        .card-title {
            font-weight: 650;
            color: var(--text);
            margin-bottom: 0.25rem;
        }

        .card-copy {
            color: var(--muted);
            font-size: 0.95rem;
            line-height: 1.35;
            margin-bottom: 0;
        }

        div[data-testid="stButton"] > button {
            border-radius: 999px;
            padding: 0.55rem 1.05rem;
            font-weight: 600;
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            background: #52b788 !important;
            color: #0d1b12 !important;
            border: none !important;
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: #40a070 !important;
            border: none !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"] {
            background: transparent;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
        }

        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            border-color: #52b788 !important;
            color: #52b788 !important;
        }

        .stDownloadButton > button {
            background: #52b788 !important;
            color: #0d1b12 !important;
            border: none !important;
            border-radius: 999px !important;
            font-weight: 700 !important;
        }

        .stDownloadButton > button:hover {
            background: #40a070 !important;
            color: #0d1b12 !important;
        }

        .stTextInput input,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] > div,
        .stTextArea textarea {
            border-radius: 10px;
            border: 1px solid var(--border) !important;
            background: #0f1728 !important;
            color: var(--text) !important;
        }

        div[data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid var(--border);
            background: #0f1728;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--card);
            border: 1px solid var(--border) !important;
        }

        [data-testid="stMarkdownContainer"] ul,
        [data-testid="stMarkdownContainer"] li {
            color: #ffffff !important;
        }

        [data-testid="stSidebar"] {
            display: none !important;
        }

        [data-testid="collapsedControl"] {
            display: none !important;
        }

        @keyframes fade-up {
            from {
                opacity: 0;
                transform: translateY(8px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @media (max-width: 860px) {
            .landing-grid {
                grid-template-columns: 1fr;
            }
        }

        label, p, span, div, li, strong {
            color: var(--text);
            font-family: "DM Sans", sans-serif;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_progress(current_step: int, total_steps: int = 4) -> None:
    progress_value = max(0.0, min(1.0, current_step / total_steps))
    st.progress(progress_value)
    st.caption(f"Step {current_step} of {total_steps}")


inject_global_styles()

PAGE_BY_STEP = {}


def go_to(step: int) -> None:
    st.session_state["step"] = step
    target_page = PAGE_BY_STEP.get(step)
    if target_page is None:
        st.rerun()
    st.switch_page(target_page)


# Resets the app to return to home page.
def start_over() -> None:
    for key in list(st.session_state.keys()):
        if key not in {"theme"}:
            del st.session_state[key]
    go_to(1)


def _render_step(step: int, render_fn) -> None:
    st.session_state["step"] = step
    render_progress(step, total_steps=4)

    if step > 1: 
        col_back, col_over, _ = st.columns([1.2, 1.5, 7.3])
        with col_back:
            if st.button("← Back", type="primary", key=f"back_{step}"):
                go_to(step - 1)
        with col_over:
            if st.button("Start Over", type="primary", key=f"start_over_{step}"):
                start_over()

    render_fn(go_to)


def _landing_route() -> None:
    _render_step(1, render_landing_page)


def _event_setup_route() -> None:
    _render_step(2, render_event_setup_page)


def _participant_setup_route() -> None:
    _render_step(3, render_participant_setup_page)


def _results_route() -> None:
    _render_step(4, render_results_page)


st.session_state.setdefault("step", 1)
st.session_state.setdefault("event_name", "")

landing_page = st.Page(_landing_route, title="Landing", url_path="landing", default=True)
event_setup_page = st.Page(_event_setup_route, title="Event Setup", url_path="event-setup")
participant_setup_page = st.Page(_participant_setup_route, title="Participant Setup", url_path="participant-setup")
results_page = st.Page(_results_route, title="Results", url_path="results")

PAGE_BY_STEP = {
    1: landing_page,
    2: event_setup_page,
    3: participant_setup_page,
    4: results_page,
}

current_page = st.navigation(
    [landing_page, event_setup_page, participant_setup_page, results_page],
    position="hidden",
)
current_page.run()

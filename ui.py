import streamlit as st


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
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

        .stButton > button {
            background: linear-gradient(120deg, var(--accent) 0%, var(--accent-2) 100%);
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px;
            padding: 0.55rem 1.05rem;
            font-weight: 600;
        }

        .stDownloadButton > button {
            border-radius: 10px !important;
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

        label, p, span, div, li, strong {
            color: var(--text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h2 style="margin:0;">{title}</h2>
            <p class="app-subtitle">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_progress(current_step: int, total_steps: int = 4) -> None:
    progress_value = max(0.0, min(1.0, current_step / total_steps))
    st.progress(progress_value)
    st.caption(f"Step {current_step} of {total_steps}")


def render_start_over_button(button_key: str) -> None:
    if st.button("Start Over", key=button_key):
        keys_to_keep = {"theme"}
        for key in list(st.session_state.keys()):
            if key not in keys_to_keep:
                del st.session_state[key]
        st.switch_page("app.py")

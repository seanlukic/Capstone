import streamlit as st

_STEPS = [
    {
        "num": "Step 1",
        "title": "Configure event",
        "copy": "Define tables, capacities, and rounds in the downloadable template.",
    },
    {
        "num": "Step 2",
        "title": "Upload participants",
        "copy": "Import traits, optional locks, and target constraints in one pass.",
    },
    {
        "num": "Step 3",
        "title": "Generate groupings",
        "copy": "Review optimized seatings and export group assignments for event.",
    },
]

_CSS = """
<style>
/* ── Kicker ───────────────────────────────────────────────── */
.landing-kicker {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #52b788;
    margin: 0 0 1rem;
}

/* ── Hero text ────────────────────────────────────────────── */
.landing-title {
    font-size: clamp(1.75rem, 3vw, 2.75rem);
    font-weight: 700;
    line-height: 1.15;
    margin: 0 0 1rem;
}

.landing-subtitle {
    font-size: 1rem;
    line-height: 1.75;
    opacity: 0.6;
    max-width: 560px;
    margin: 0 0 2rem;
}

/* ── Divider ──────────────────────────────────────────────── */
.landing-divider {
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    margin: 0 0 1.75rem;
}

/* ── Metric strip ─────────────────────────────────────────── */
.landing-metrics {
    display: flex;
    gap: 2.5rem;
    margin-bottom: 2.5rem;
    flex-wrap: wrap;
}

.landing-metric-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    opacity: 0.45;
    margin: 0 0 0.3rem;
}

.landing-metric-value {
    font-size: 0.9rem;
    font-weight: 500;
    margin: 0;
    opacity: 0.9;
}

/* ── Step cards ───────────────────────────────────────────── */
.landing-feature {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 1.25rem 1.25rem 1.5rem;
    min-height: 160px;
    box-sizing: border-box;
}

.landing-feature-num {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #52b788;
    margin: 0 0 0.75rem;
}

.landing-feature-title {
    font-size: 1rem;
    font-weight: 600;
    margin: 0 0 0.5rem;
    line-height: 1.3;
}

.landing-feature-copy {
    font-size: 0.875rem;
    line-height: 1.65;
    opacity: 0.55;
    margin: 0;
}

/* ── CTA button ───────────────────────────────────────────── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #52b788;
    border: none;
    border-radius: 100px;
    padding: 0.6rem 1.75rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: #0d1b12;
    transition: background 0.15s ease;
}

div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #40a070;
    border: none;
}
</style>
"""


def render(go_to) -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # Hero — no wrapper div, content flows openly
    st.markdown(
        """
        <p class="landing-kicker">Group Formation Studio</p>
        <h1 class="landing-title">Multi-Step Optimization Model for Group Formation</h1>
        <p class="landing-subtitle">
            Build balanced groups with fewer manual tradeoffs. Configure your event,
            upload one template, and let the optimizer produce table assignments with
            diversity constraints, trait targets, and optional participant locks that
            you set.
        </p>
        <hr class="landing-divider">
        <div class="landing-metrics">
            <div>
                <p class="landing-metric-label">Input format</p>
                <p class="landing-metric-value">Excel template upload</p>
            </div>
            <div>
                <p class="landing-metric-label">Result output</p>
                <p class="landing-metric-value">Group assignments &amp; Excel exports</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Step cards
    for col, step in zip(st.columns(3), _STEPS):
        with col:
            st.markdown(
                f"""
                <div class="landing-feature">
                    <p class="landing-feature-num">{step["num"]}</p>
                    <h3 class="landing-feature-title">{step["title"]}</h3>
                    <p class="landing-feature-copy">{step["copy"]}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")
    if st.button("Start Setup →", type="primary"):
        go_to(2)

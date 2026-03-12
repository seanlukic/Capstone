import streamlit as st

# Step 1: Home page with app title, description, and button to start setup.
def render(go_to) -> None:
    st.markdown(
        """
        <section class="landing-shell">
            <p class="landing-kicker">Group Formation Studio</p>
            <h1 class="landing-title">Build balanced groups with fewer manual tradeoffs.</h1>
            <p class="landing-subtitle">
                Configure your event, upload one template, and let the optimizer produce table assignments
                with diversity constraints, trait targets, and optional participant locks that you set.
            </p>
            <div class="landing-grid">
                <div class="landing-metric">
                    <p class="landing-metric-label">Input format</p>
                    <p class="landing-metric-value">Excel template upload</p>
                </div>
                <div class="landing-metric">
                    <p class="landing-metric-label">Result output</p>
                    <p class="landing-metric-value">Participant + schedule CSVs</p>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
            <div class="landing-feature">
                <h3 class="landing-feature-title">1. Configure Event</h3>
                <p class="landing-feature-copy">
                    Define tables, capacities, and rounds in the downloadable template.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            """
            <div class="landing-feature">
                <h3 class="landing-feature-title">2. Upload Participants</h3>
                <p class="landing-feature-copy">
                    Import participant traits, optional locks, and target constraints in one pass.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            """
            <div class="landing-feature">
                <h3 class="landing-feature-title">3. Generate Groupings</h3>
                <p class="landing-feature-copy">
                    Review optimized seatings and export complete outputs for facilitation.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("Start Setup", type="primary"):
        go_to(2)

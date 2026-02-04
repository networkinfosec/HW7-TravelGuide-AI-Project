# travel_guide.py
# -------------------------------------------------------
# Travel Guide (Streamlit + OpenAI)
# - Collects trip inputs (destination, days, interests, guardrails)
# - Calls ChatGPT via OpenAI SDK with fallbacks
# - Displays a day-by-day plan
# - Generates a clean PDF using ReportLab
# - Includes a Reset Form button
# -------------------------------------------------------

import os
from datetime import datetime
from textwrap import dedent

import streamlit as st                  # UI framework (forms/buttons/output)
from dotenv import load_dotenv          # Loads OPENAI_API_KEY from .env
from openai import OpenAI               # OpenAI client

# PDF generation (ReportLab)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
)

# -------------------------------------------------------
# Dependency self-check (helps beginners: clear error msg)
# -------------------------------------------------------
try:
    import streamlit
    import openai
    import reportlab
    import dotenv
except ImportError as e:
    raise SystemExit(
        "\n❌ Missing dependency.\n"
        "Run:\n"
        "  pip install -r requirements.txt\n\n"
        f"Details: {e}\n"
    )

# -------------------------------------------------------
# ENV + OpenAI client setup
# -------------------------------------------------------
# Reads .env (same approach as your Career Coach)
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------------------------------------
# Streamlit page config
# -------------------------------------------------------
st.set_page_config(
    page_title="Travel Guide (ChatGPT)",
    page_icon="🧭",
    layout="centered",
)

# -------------------------------------------------------
# Session state keys (so Reset can clear everything)
# -------------------------------------------------------
FORM_KEYS = [
    "destination",
    "num_days",
    "interests",
    "guardrails",
]

def init_form_state():
    # If key doesn't exist, create it with a default value
    st.session_state.setdefault("destination", "")
    st.session_state.setdefault("num_days", 3)
    st.session_state.setdefault("interests", "")
    st.session_state.setdefault("guardrails", "")
    st.session_state.setdefault("plan_md", "")

def reset_all_callback():
    # Clears the form and also clears the generated plan
    st.session_state["destination"] = ""
    st.session_state["num_days"] = 3
    st.session_state["interests"] = ""
    st.session_state["guardrails"] = ""
    st.session_state["plan_md"] = ""
    st.session_state.pop("last_model_used", None)
    st.session_state.pop("last_usage", None)

init_form_state()

# -------------------------------------------------------
# UI header
# -------------------------------------------------------
st.title("🧭 Travel Guide")
st.caption("Streamlit + OpenAI demo (generates a day-by-day plan + PDF)")

with st.expander("What this app does", expanded=False):
    st.markdown(
        "- Takes your trip details\n"
        "- Generates a **day-by-day itinerary**\n"
        "- Respects **guardrails** (constraints)\n"
        "- Lets you **download a PDF**"
    )

# -------------------------------------------------------
# Prompting
# -------------------------------------------------------
SYSTEM_PROMPT = dedent("""
You are a precise travel planner.
Rules:
- You MUST respect the user’s guardrails. If something conflicts, replace it with an alternative.
- Do not include unsafe or illegal activities.
- Provide practical details: timing blocks (morning/afternoon/evening), transit style (car/public transit/short rides),
  and a short reason why each stop matches the interests.
- Keep it realistic for the number of days.
- Avoid excessive walking if user says no walking tours.
- If user says wheelchair accessible or kid-friendly, ensure every suggestion matches.
Output format MUST be Markdown with these sections:
## Trip Summary
## Day-by-Day Plan
(Use H3 headings like: ### Day 1, ### Day 2, etc.)
## Food Suggestions
## Tips & Notes
""").strip()

def build_user_prompt(destination: str, num_days: int, interests: str, guardrails: str) -> str:
    return dedent(f"""
    TRIP INPUTS
    - Destination: {destination}
    - Number of days: {num_days}
    - Special interests: {interests or "No special interests provided"}
    - Guardrails / constraints: {guardrails or "None"}

    REQUIREMENTS
    - Create a complete plan for all {num_days} days.
    - Divide each day into Morning / Afternoon / Evening.
    - For each activity, give a short reason why it fits the interests.
    - Make sure every item respects the guardrails.
    - Keep it readable (around 800–1400 words depending on trip length).
    """).strip()

# -------------------------------------------------------
# Model fallback + robust text extractor
# (Same pattern as your Career Coach app)
# -------------------------------------------------------
FALLBACK_MODELS = ["gpt-5", "gpt-5-mini", "gpt-4.1"]

def _extract_text_from_chat_completion(comp) -> str:
    try:
        txt = comp.choices[0].message.content
        if isinstance(txt, str) and txt.strip():
            return txt
        if isinstance(txt, list):
            parts = []
            for p in txt:
                if isinstance(p, str):
                    parts.append(p)
                elif isinstance(p, dict) and isinstance(p.get("text"), str):
                    parts.append(p["text"])
            joined = "\n".join(parts).strip()
            if joined:
                return joined
    except Exception:
        pass
    return ""

def get_plan_markdown(user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for model_name in FALLBACK_MODELS:
        try:
            comp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_completion_tokens=2200,
            )
            text = _extract_text_from_chat_completion(comp)
            if text.strip():
                st.session_state["last_model_used"] = model_name
                st.session_state["last_usage"] = getattr(comp, "usage", None)
                return text
            last_error = RuntimeError(f"Model '{model_name}' returned empty content.")
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All model attempts failed. Last error: {last_error}")

# -------------------------------------------------------
# PDF helpers (Markdown -> ReportLab flowables)
# -------------------------------------------------------
def markdown_to_flowables(md_text: str, styles):
    """
    Lightweight Markdown support:
    - '## ' -> Heading2
    - '### ' -> Heading3
    - Bullets '-', '*', '•' -> unordered lists
    - Otherwise -> paragraph
    """
    flow = []
    body = styles["BodyText"]
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6)
    h3 = ParagraphStyle("H3", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4)

    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            flow.append(Spacer(1, 6))
            i += 1
            continue

        if line.startswith("## "):
            flow.append(Paragraph(line[3:].strip(), h2))
            i += 1
            continue

        if line.startswith("### "):
            flow.append(Paragraph(line[4:].strip(), h3))
            i += 1
            continue

        if line.lstrip().startswith(("-", "*", "•")):
            items = []
            while i < len(lines) and lines[i].lstrip().startswith(("-", "*", "•")):
                bullet_text = lines[i].lstrip()[1:].strip()
                items.append(ListItem(Paragraph(bullet_text, body), leftIndent=12))
                i += 1
            flow.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=6))
            flow.append(Spacer(1, 4))
            continue

        flow.append(Paragraph(line, body))
        i += 1

    return flow

def write_pdf(markdown_text: str, filename: str = "travel_plan.pdf") -> str:
    # Letter with clean margins (same idea as Career Coach)
    doc = SimpleDocTemplate(
        filename,
        pagesize=LETTER,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Travel Plan",
        author="Travel Guide App",
    )
    styles = getSampleStyleSheet()

    header = ParagraphStyle(
        "Header",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=12,
    )

    story = []
    story.append(Paragraph("Travel Plan", header))
    meta = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    story.append(Paragraph(meta, styles["Normal"]))
    story.append(Spacer(1, 10))

    story.extend(markdown_to_flowables(markdown_text, styles))
    doc.build(story)
    return filename

# -------------------------------------------------------
# Input form
# -------------------------------------------------------
with st.form("travel_inputs"):
    st.text_input(
        "1) Destination to Travel",
        placeholder="e.g., Chicago, IL",
        key="destination",
    )

    st.number_input(
        "2) Number of Days",
        min_value=1,
        max_value=30,
        step=1,
        key="num_days",
    )

    st.text_area(
        "3) Special Interests",
        placeholder="e.g., Museums, Food & Cuisine, Historic sites, Nature",
        key="interests",
    )

    st.text_area(
        "4) Guardrails / Constraints",
        placeholder="e.g., No walking tours, only kid-friendly activities, wheelchair accessible places",
        key="guardrails",
    )

    submitted = st.form_submit_button("Generate Travel Plan")

# -------------------------------------------------------
# Optional: quick diagnostics (helps if key/model issues)
# -------------------------------------------------------
with st.expander("Diagnostics (optional)", expanded=False):
    if st.button("Run quick API self-test"):
        try:
            ping = client.chat.completions.create(
                model=FALLBACK_MODELS[0],
                messages=[{"role": "user", "content": "Reply with the single word: READY"}],
                max_completion_tokens=10,
            )
            st.success("Self-test response:")
            st.code(_extract_text_from_chat_completion(ping))
        except Exception as e:
            st.error(f"Self-test failed: {e}")

# -------------------------------------------------------
# Main action
# -------------------------------------------------------
if submitted:
    # Basic validation (don’t call the API if required fields are missing)
    if not st.session_state["destination"]:
        st.warning("Please enter a **Destination**.")
    else:
        with st.spinner("Generating your travel plan..."):
            user_prompt = build_user_prompt(
                st.session_state["destination"],
                int(st.session_state["num_days"]),
                st.session_state["interests"],
                st.session_state["guardrails"],
            )
            st.session_state["plan_md"] = get_plan_markdown(user_prompt)

# -------------------------------------------------------
# Output rendering + PDF download
# -------------------------------------------------------
if st.session_state.get("plan_md", "").strip():
    st.success("Plan generated!")
    st.caption(f"Model: {st.session_state.get('last_model_used', 'unknown')}")
    if st.session_state.get("last_usage"):
        st.caption(f"Usage: {st.session_state['last_usage']}")

    st.subheader("Your Travel Plan")
    st.markdown(st.session_state["plan_md"], unsafe_allow_html=False)

    with st.expander("Show raw text (copy-friendly)"):
        st.text_area("Plan (raw)", st.session_state["plan_md"], height=400)

    # PDF export
    try:
        pdf_path = write_pdf(st.session_state["plan_md"], filename="travel_plan.pdf")
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="⬇️ Download PDF",
                data=f.read(),
                file_name="travel_plan.pdf",
                mime="application/pdf",
            )
    except Exception as e:
        st.error(f"PDF generation error: {e}")
        st.info("You can still copy the plan above while we sort out PDF export.")

# -------------------------------------------------------
# Reset button (outside the form)
# -------------------------------------------------------
st.divider()
st.button("🔁 Reset Form (clear fields + plan)", type="secondary", on_click=reset_all_callback)
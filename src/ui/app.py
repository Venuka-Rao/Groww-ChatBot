"""Single-screen facts chat. Visual source: the Stitch export in design/stitch."""

import html
import re

import streamlit as st

from src.pipeline.ask import ask

DISCLAIMER = "Facts-only. No investment advice."
WELCOME = (
    "Ask a published fact about the 25 covered HDFC direct-growth schemes on Groww, "
    "such as expense ratio, exit load, minimum SIP, lock-in, riskometer, or benchmark."
)
EXAMPLES = (
    "What is the expense ratio of HDFC Large Cap Fund?",
    "What is the exit load of HDFC Mid Cap Fund?",
    "What is the minimum SIP of HDFC Small Cap Fund?",
)
_SOURCE = re.compile(
    r"\n+###### Source link\n+\[([^\]]+)\]\((https?://[^)\s]+)\)\s*\Z",
    re.DOTALL,
)

def _theme_css(dark: bool) -> str:
    if dark:
        page, card, border = "#060809", "#1E2224", "#2E2E2E"
        text, secondary, faint = "#F0EFFF", "#A1A3AD", "#7C7E8C"
        notice, hover = "#0F251D", "#0F251D"
    else:
        page, card, border = "#FFFFFF", "#F8F8F8", "#E9E9EB"
        text, secondary, faint = "#44475B", "#7C7E8C", "#A1A3AD"
        notice, hover = "#E9FAF3", "#E9FAF3"
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] {{ font-family: Inter, sans-serif; }}
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stBottom"],
    [data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {{
      background: {page} !important; color: {text};
    }}
    header[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"] {{ display: none; }}
    .block-container {{ max-width: 760px; padding-top: 3.5rem; padding-bottom: 14rem; }}
    [class*="st-key-dark_mode"] {{
      position: fixed !important; top: 16px; right: 24px; z-index: 1000;
      width: fit-content !important; background: transparent !important;
      height: auto !important; min-height: 0 !important;
    }}
    .notice {{
      display: flex; justify-content: space-between; align-items: center; gap: 12px;
      background: {notice}; border: 1px solid rgba(4, 180, 136, 0.3);
      border-radius: 8px; padding: 10px 16px; margin-bottom: 28px;
    }}
    .notice-left {{ display: flex; align-items: center; gap: 8px; color: {text}; font-size: 12px; font-weight: 500; }}
    .dot {{ width: 8px; height: 8px; border-radius: 99px; background: #04B488; }}
    .notice-right {{ color: {secondary}; font-size: 11px; font-weight: 500; letter-spacing: 0.04em; }}
    h1.facts-title {{ color: {text}; font-size: 24px; font-weight: 600; letter-spacing: -0.015em; margin: 0 0 8px; }}
    p.facts-intro {{ color: {secondary}; font-size: 14px; line-height: 22px; margin: 0 0 28px; }}
    p.section-label {{ color: {faint}; font-size: 11px; font-weight: 600; letter-spacing: 0.06em; margin: 0 0 10px; }}
    div[data-testid="stButton"] > button {{
      background: {page}; color: {text}; border: 1px solid {border}; border-radius: 8px;
      text-align: left; font-weight: 400; font-size: 14px; padding: 14px 16px;
      display: flex; justify-content: space-between; align-items: center;
    }}
    div[data-testid="stButton"] > button:hover {{
      background: {hover}; border-color: #04B488; color: {text};
    }}
    div[data-testid="stButton"] > button::after {{ content: "↗"; color: {faint}; margin-left: 12px; }}
    .user-row {{ display: flex; justify-content: flex-end; margin: 18px 0 12px; }}
    .user-chip {{
      max-width: 85%; background: {card}; border: 1px solid {border}; border-radius: 8px;
      padding: 12px 16px; color: {text}; font-size: 14px;
    }}
    .answer-card {{
      background: {page}; border: 1px solid {border}; border-radius: 16px; padding: 24px; margin-bottom: 8px;
    }}
    .answer-head {{
      display: flex; justify-content: space-between; gap: 12px; align-items: center;
      border-bottom: 1px solid {border}; padding-bottom: 12px; margin-bottom: 12px;
    }}
    .answer-title {{ color: {text}; font-size: 12px; font-weight: 600; }}
    .answer-tag {{ color: {faint}; font-size: 11px; }}
    .answer-body {{ color: {text}; font-size: 14px; line-height: 22px; margin-bottom: 16px; }}
    .source-box {{ background: {card}; border: 1px solid {border}; border-radius: 8px; padding: 16px; }}
    .source-label {{ color: {text}; font-size: 12px; font-weight: 500; margin-bottom: 6px; }}
    .source-box a {{ color: #04B488; font-size: 13px; text-underline-offset: 2px; }}
    .answer-foot {{
      display: flex; justify-content: space-between; gap: 12px;
      border-top: 1px solid {border}; margin-top: 16px; padding-top: 12px;
      color: {faint}; font-size: 12px;
    }}
    .plain-note {{ color: {text}; font-size: 14px; line-height: 22px; margin: 12px 0; }}
    .composer-note {{ color: {faint}; font-size: 11px; text-align: center; margin-top: 28px; }}
    div[data-testid="stChatInput"], div[data-testid="stChatInput"] > div {{
      background: {page} !important; border-color: {border} !important;
    }}
    div[data-testid="stChatInput"] textarea {{
      background: {page}; border: 1px solid {border}; border-radius: 8px; color: {text};
    }}
    div[data-testid="stChatInput"] textarea:focus {{ border-color: #04B488; }}
    div[data-testid="stChatInput"] button {{ background: #04B488; border-radius: 8px; color: #FFFFFF; }}
    </style>
    """


st.set_page_config(page_title="HDFC scheme facts", layout="centered")
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
st.toggle("Dark", key="dark_mode")
st.markdown(_theme_css(st.session_state.dark_mode), unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="notice">
      <div class="notice-left"><span class="dot"></span>{html.escape(DISCLAIMER)}</div>
      <div class="notice-right">25 HDFC DIRECT SCHEMES</div>
    </div>
    <h1 class="facts-title">HDFC scheme facts</h1>
    <p class="facts-intro">{html.escape(WELCOME)}</p>
    <p class="section-label">SUGGESTED QUERIES</p>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []


def submit(question: str) -> None:
    cleaned = question.strip()
    if not cleaned:
        return
    with st.spinner("Looking up the published fact..."):
        try:
            answer = ask(cleaned)
        except Exception as exc:
            st.session_state.messages.append({"role": "user", "text": cleaned})
            st.session_state.messages.append(
                {"role": "assistant", "text": str(exc), "plain": True, "intent": "error", "stamp": ""}
            )
            return
    st.session_state.messages.append({"role": "user", "text": cleaned})
    st.session_state.messages.append(
        {
            "role": "assistant",
            "text": answer.text,
            "plain": answer.intent == "pii",
            "intent": answer.intent,
            "stamp": answer.source_stamp,
            "refusal": answer.refusal,
        }
    )


for question in EXAMPLES:
    if st.button(question, use_container_width=True):
        submit(question)

typed = st.chat_input("Ask a published fact")
if typed:
    submit(typed)


def _split_source(text: str) -> tuple[str, str, str]:
    match = _SOURCE.search(text.strip())
    if not match:
        return text.strip(), "", ""
    return text[: match.start()].strip(), match.group(1), match.group(2)


def _card(message: dict) -> str:
    if message.get("plain"):
        return f'<p class="plain-note">{html.escape(message["text"])}</p>'
    fact, label, url = _split_source(message["text"])
    verified = message.get("intent") == "answer" and not message.get("refusal")
    title = "Published Fact Verification" if verified else "Facts-only reply"
    stamp = message.get("stamp") or ""
    stamp_line = f"Last updated from sources: {html.escape(stamp)}." if stamp else ""
    source = ""
    if label and url:
        source = (
            '<div class="source-box">'
            '<div class="source-label">Source link</div>'
            f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'
            "</div>"
        )
    return (
        '<div class="answer-card">'
        '<div class="answer-head">'
        f'<span class="answer-title">{title}</span>'
        '<span class="answer-tag">Direct Growth Scheme</span>'
        "</div>"
        f'<div class="answer-body">{html.escape(fact)}</div>'
        f"{source}"
        '<div class="answer-foot">'
        f"<span>{stamp_line}</span>"
        "</div>"
        "</div>"
    )


for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(
            f'<div class="user-row"><div class="user-chip">{html.escape(message["text"])}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(_card(message), unsafe_allow_html=True)

st.markdown(
    '<p class="composer-note">Only official SID, KIM, and factsheet numbers are indexed. '
    "No performance comparisons or advice provided.</p>",
    unsafe_allow_html=True,
)

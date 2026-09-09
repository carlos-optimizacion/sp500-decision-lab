"""Estilos de interfaz; la evidencia cuantitativa permanece en componentes nativos."""

from __future__ import annotations

import streamlit as st


CSS = """
<style>
  :root { color-scheme: dark; }
  .stApp, [data-testid="stAppViewContainer"] { background: #0B1120; color: #E5E7EB; }
  [data-testid="stHeader"] { background: rgba(11, 17, 32, .94); }
  .block-container { max-width: 1240px; padding-top: 1.4rem; padding-bottom: 3rem; }
  [data-testid="stSidebar"] { background: #070C16; border-right: 1px solid #263247; }
  [data-testid="stSidebar"] * { color: #F8FAFC; }
  [data-testid="stSidebar"] .stButton button { background: #315FC5; color: white; border: 1px solid #4F7CE0; }
  h1, h2, h3 { color: #F8FAFC; letter-spacing: -0.02em; }
  .eyebrow { color: #79A2FF; font-size: .76rem; font-weight: 750; letter-spacing: .10em; text-transform: uppercase; }
  .hero-title { color: #F8FAFC; font-size: 2.25rem; line-height: 1.08; font-weight: 760; margin: .15rem 0 .45rem; }
  .hero-copy { color: #A7B2C5; font-size: 1rem; max-width: 820px; margin-bottom: 1rem; }
  .state-card { background: #172033; border: 1px solid #2A3952; border-radius: 14px; padding: 18px 20px; color: white; margin: .4rem 0 1rem; }
  .state-card .label { opacity: .72; font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }
  .state-card .value { font-size: 1.35rem; font-weight: 720; margin-top: 5px; }
  .soft-card { background: #111827; border: 1px solid #293548; border-radius: 12px; padding: 14px 16px; min-height: 112px; }
  .soft-card .kicker { color: #A7B2C5; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }
  .soft-card .big { color: #F8FAFC; font-size: 1.6rem; font-weight: 750; margin: .25rem 0; }
  .soft-card .note { color: #A7B2C5; font-size: .8rem; }
  div[data-testid="stMetric"] { background: #111827; border: 1px solid #293548; border-radius: 12px; padding: 13px 15px; }
  div[data-testid="stPlotlyChart"] { background: #111827; border: 1px solid #293548; border-radius: 12px; padding: 2px; }
  .section-note { color: #A7B2C5; font-size: .88rem; margin-top: -.45rem; margin-bottom: .75rem; }
  .source-line { color: #A7B2C5; font-size: .78rem; }
  .pill { display: inline-block; padding: 4px 9px; border-radius: 999px; background: #1D315C; color: #AFC7FF; font-size: .75rem; font-weight: 650; margin-right: 6px; }
  .warning-strip { background: #2B2415; border-left: 4px solid #E6B85C; padding: 11px 14px; color: #F5DFA8; border-radius: 4px; }
  @media (max-width: 760px) {
    .hero-title { font-size: 1.75rem; }
    .block-container { padding-left: 1rem; padding-right: 1rem; }
  }
</style>
"""


def inject_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(eyebrow: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="eyebrow">{eyebrow}</div><div class="hero-title">{title}</div><div class="hero-copy">{copy}</div>',
        unsafe_allow_html=True,
    )


def state_card(label: str, value: str, detail: str = "") -> None:
    st.markdown(
        f'<div class="state-card"><div class="label">{label}</div><div class="value">{value}</div><div style="opacity:.72;font-size:.84rem;margin-top:5px">{detail}</div></div>',
        unsafe_allow_html=True,
    )


def soft_card(kicker: str, value: str, note: str) -> None:
    st.markdown(
        f'<div class="soft-card"><div class="kicker">{kicker}</div><div class="big">{value}</div><div class="note">{note}</div></div>',
        unsafe_allow_html=True,
    )

"""Shared sidebar — call render() at the top of every page."""
import streamlit as st


def render() -> None:
    st.sidebar.markdown("""
<div style="padding: 4px 0 12px 0;">
  <div style="font-size: 16px; font-weight: 600; color: #1A1A2E;">PBCP Research Demo</div>
  <div style="font-size: 11px; color: #6B7280; margin-top: 2px;">IACG v2.0 · Keerthi Rapolu &amp; Sreeja Katta</div>
</div>
""", unsafe_allow_html=True)
    st.sidebar.divider()
    st.sidebar.markdown("""
<div style="font-size: 12px; color: #6B7280; line-height: 1.8;">
<b style="color:#1A1A2E;">Pages</b><br>
Use the sidebar links above to navigate.
</div>
""", unsafe_allow_html=True)

"""Shared visual identity for the simulator and student workshop."""
from pathlib import Path

import streamlit as st

LOGO = Path(__file__).with_name('assets') / 'viu-logo.png'


def render_brand_header():
    st.logo(str(LOGO), size='large', link='https://www.universidadviu.com/es/')
    st.image(str(LOGO), width=310)
    st.caption('LABORATORIO DE ÓPTICA GEOMÉTRICA · OPGSim')

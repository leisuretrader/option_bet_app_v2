import streamlit as st
import pandas as pd
import numpy as np
import os

from bet_logic import bet_logic


st.set_page_config(layout='wide', page_title = 'Option Bet', page_icon=":smiley:")
st.markdown("""<style>
        body{background-color: #fbfff0}
        </style>""", unsafe_allow_html=True)
st.markdown("""<style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>""" ,unsafe_allow_html=True)

base_dir = str(os.path.dirname(os.path.realpath(__file__))) + "/"

screen = st.sidebar.selectbox("View", (
                        'Option_Bet',
                        'Equity Fundamental'
                        ))
st.title("Option Betting")

data_dir = None

if screen == 'Option_Bet':
    # st.write("")
    bet_logic()


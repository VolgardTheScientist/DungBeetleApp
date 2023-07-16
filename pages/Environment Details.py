import streamlit as st
import ifcopenshell
import pandas as pd
from tools import ifchelper
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
import numpy as np
import io
from google.cloud import storage
from google.oauth2.service_account import Credentials
import tempfile

# ========== Page title and welcome message, page config ==========

st.set_page_config(layout="centered")
st.title("Environment Details")
st.write("")
st.write("Pandas: ", pd.__version__)
st.write("Streamlit: ", st.__version__)
st.write("Numpy: ", np.__version__)


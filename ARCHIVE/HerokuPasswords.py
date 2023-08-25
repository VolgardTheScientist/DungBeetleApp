import json
import streamlit as st
import toml
import os
from google.oauth2.service_account import Credentials

# ========== Fetch SECRETS Admin Login ==========

# Initialize correct_password to an empty string
correct_password = ""

# First, try to get the password from the Heroku environment variable
toml_string = os.environ.get("SECRETS_TOML", "")
if toml_string:
    parsed_toml = toml.loads(toml_string)
    correct_password = parsed_toml.get("ADMIN_CREDENTIALS", {}).get("password", "")

# If the above fails, then try to get the password using Streamlit's built-in secrets management
if not correct_password:
    try:
        correct_password = st.secrets["ADMIN_CREDENTIALS"]["password"]
    except (FileNotFoundError, KeyError):
        pass  # Handle the exception gracefully or log an appropriate message if needed

if correct_password:
    st.write("Correct password successfully loaded.")
else:
    st.write("Failed to load correct password.")

# ========== Fetch SECRETS Google Credentials ==========

# Initialize credentials to None
credentials = ""

# First, try to get the credentials from the Heroku environment variable
toml_string = os.environ.get("SECRETS_TOML", "")
if toml_string:
    parsed_toml = toml.loads(toml_string)
    google_app_credentials = parsed_toml.get("GOOGLE_APPLICATION_CREDENTIALS", {})
    if google_app_credentials:
        credentials = Credentials.from_service_account_info(google_app_credentials)

# If the above fails, then try to get the credentials using Streamlit's built-in secrets management
if not credentials:
    try:
        credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
    except KeyError:
        st.write("KeyError: Unable to find GOOGLE_APPLICATION_CREDENTIALS in secrets.")
    except FileNotFoundError:
        st.write("FileNotFoundError: Couldn't find the Google Credentials file.")
    except Exception as e:
        st.write(f"An error occurred: {e}")

if credentials:
    st.write("Credentials successfully loaded.")
else:
    st.write("Failed to load credentials.")


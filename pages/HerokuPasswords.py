import streamlit as st
import toml
import os

# ========== Fetch SECRETS ==========

try:
    # Try to get the password using Streamlit's built-in secrets management
    correct_password = st.secrets["ADMIN_CREDENTIALS"]["password"]
except (FileNotFoundError, KeyError):
    # If that fails, try to get the password from the Heroku environment variable
    toml_string = os.environ.get("SECRETS_TOML", "")
    if toml_string:
        parsed_toml = toml.loads(toml_string)
        correct_password = parsed_toml.get("ADMIN_CREDENTIALS", {}).get("password", "")

# Now you can use `correct_password` in your code

st.write(correct_password)
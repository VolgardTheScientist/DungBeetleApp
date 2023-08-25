import streamlit as st
import toml
import os

# ========== Fetch SECRETS ==========

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

# Now you can use `correct_password` in your code


st.write(correct_password)
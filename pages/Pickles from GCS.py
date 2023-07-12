import os
import pandas as pd
import pickle
import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
import ifcopenshell
import tempfile
import base64
import requests
from pages.ifc_viewer.ifc_viewer import ifc_viewer
from google.cloud import storage
from google.oauth2.service_account import Credentials
import json

st.set_page_config(layout="wide")
st.title("Accessing GCS Pickles Warehouse")

# Create a Google Cloud Storage client
storage_client = storage.Client()

def download_file_from_gcs(bucket_name, blob_name, destination_file_name):
    credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(destination_file_name)
    st.write("Blob {} downloaded to {}.".format(blob_name, destination_file_name))


# Other function definitions...

def get_gcs_bucket_files(bucket_name):
    credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
    storage_client = storage.Client(credentials=credentials)

    # Get the bucket from the Google Cloud Storage
    bucket = storage_client.get_bucket(bucket_name)
    
    # Get the list of all blobs in the bucket
    blobs = bucket.list_blobs()
    
    # Get the list of pickle file names
    return [blob.name for blob in blobs if blob.name.endswith('.pickle')]

# Other function definitions...

bucket_name = 'pickle_warehouse'
pickle_files = get_gcs_bucket_files(bucket_name)

for pickle_file in pickle_files:
    local_path = tempfile.gettempdir() + '/' + pickle_file  # using tempfile for cross-platform compatibility
    download_file_from_gcs(bucket_name, pickle_file, local_path)
    with open(local_path, 'rb') as f:
        df = pickle.load(f)
    # Rest of your code...

# The remaining parts of your script...

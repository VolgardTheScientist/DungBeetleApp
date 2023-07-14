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
import os

# Create a Google Cloud Storage client
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
storage_client = storage.Client(credentials=credentials)

def save_to_bucket(uploaded_file, blob_name):
    """Save a file to a GCS bucket."""
    bucket = storage_client.bucket('warehouse_processing_directory')
    blob = bucket.blob(blob_name)
    blob.upload_from_file(uploaded_file)

def delete_from_bucket(blob_name):
    """Delete a file from a GCS bucket."""
    bucket = storage_client.bucket('warehouse_processing_directory')
    blob = bucket.blob(blob_name)    
    blob.delete()

def download_from_bucket(blob_name):
    """Download a file from a GCS bucket."""
    bucket = storage_client.bucket('warehouse_processing_directory')
    blob = bucket.blob(blob_name)
    _, temp_local_filename = tempfile.mkstemp()
    with open(temp_local_filename, 'wb') as f:
        storage_client.download_blob_to_file(blob, f)
    return temp_local_filename


def get_project_geocoordinates(generated_df):
    locator = Nominatim(user_agent="OpenMapQuest")
    geocode = RateLimiter(locator.geocode, min_delay_seconds=1)
    generated_df['location'] = generated_df['Complete address'].apply(geocode)
    generated_df['point'] = generated_df['location'].apply(lambda loc: tuple(loc.point) if loc else (np.nan, np.nan, np.nan))
    generated_df['latitude'] = np.nan
    generated_df['longitude'] = np.nan
    generated_df['altitude'] = np.nan
    for idx, point in generated_df['point'].iteritems():
        if not np.isnan(point[0]):
            generated_df.at[idx, 'latitude'] = point[0]
            generated_df.at[idx, 'longitude'] = point[1]
            generated_df.at[idx, 'altitude'] = point[2]
    generated_df['latitude'] = generated_df['latitude'].astype('float64')
    generated_df['longitude'] = generated_df['longitude'].astype('float64')
    generated_df['altitude'] = generated_df['altitude'].astype('float64')
    generated_df.drop(columns=['location', 'point', 'altitude'], inplace=True)


def get_project_address(ifc_file_admin_upload):
    building = ifc_file_admin_upload.by_type("IfcBuilding")[0]
    building_ID = building.GlobalId if building.GlobalId else ""
    street = building.BuildingAddress[4][0] if building.BuildingAddress[4][0] else ""
    town = building.BuildingAddress[6] if building.BuildingAddress[6] else""
    canton = building.BuildingAddress[7] if building.BuildingAddress[7] else ""
    post_code = building.BuildingAddress[8] if building.BuildingAddress[8] else ""
    country = building.BuildingAddress[9] if building.BuildingAddress[9] else ""
    complete_address = [street, ', ', post_code, ', ',town, ', ',canton, ', ',country]
    complete_address = ''.join(complete_address)
    return building_ID, street, post_code, town, canton, country, complete_address


IfcEntities = ["IfcSanitaryTerminal", "IfcDoor", "IfcCovering", "IfcWall"]

ifcEntity_dataframes = {}
for entity in IfcEntities:
    ifcEntity_dataframes["wh_" + entity] = pd.DataFrame()

uploaded_file = st.file_uploader("Upload an IFC file", type=["ifc"])

if uploaded_file is not None:
    # Save the uploaded file to the bucket
    blob_name = uploaded_file.name
    save_to_bucket(uploaded_file, blob_name)
    
    # Download the file back from the bucket to a local file
    local_filename = download_from_bucket(blob_name)
    ifc_file_admin_upload = ifcopenshell.open(local_filename)

    # Get the project address
    building_ID, street, post_code, town, canton, country, complete_address = get_project_address(ifc_file_admin_upload)

    # Loop through the IfcEntities and append data to the respective dataframe
    for entity in IfcEntities:
        warehouse_data = ifchelper.get_objects_data_by_class(ifc_file_admin_upload, entity)
        generated_df = ifchelper.create_pandas_dataframe(warehouse_data)
        generated_df['Building ID'] = building_ID
        generated_df['Project ID'] = uploaded_file.name[:-4]
        generated_df['Street'] = street
        generated_df['Post code'] = post_code
        generated_df['Town'] = town
        generated_df['Canton'] = canton
        generated_df['Country'] = country
        generated_df['Complete address'] = complete_address
        get_project_geocoordinates(generated_df)
        # Remove rows with missing latitude or longitude values
        generated_df = generated_df.dropna(subset=['latitude', 'longitude'])
        ifcEntity_dataframes["wh_" + entity] = pd.concat([ifcEntity_dataframes["wh_" + entity], generated_df], ignore_index=True)

    # Print the dataframes and provide download button
    for entity, generated_df in ifcEntity_dataframes.items():
        st.write(f"{entity}:")
        st.write(generated_df)
        st.map(generated_df)
        
        pickle_data = io.BytesIO()
        generated_df.to_pickle(pickle_data)
        pickle_data.seek(0)

        st.download_button(
            label=f"Download {entity}.pickle",
            data=pickle_data,
            file_name=f"{entity}.pickle",
            mime="application/octet-stream",
        )
        
    # Delete the file from the bucket after processing is done
    os.remove(local_filename)
    delete_from_bucket(blob_name)

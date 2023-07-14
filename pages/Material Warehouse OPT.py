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
st.title("Digital material warehouse")

# point to the key file - ONLY for LOCAL TESTING
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), '..', 'keys', 'able-analyst-392315-77bb94fe797e.json')

# Create a Google Cloud Storage client
storage_client = storage.Client()

def download_file_from_gcs(bucket_name, blob_name, destination_file_name):
    credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(destination_file_name)

def get_gcs_bucket_files(bucket_name):
    credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
    storage_client = storage.Client(credentials=credentials)

    # Get the bucket from the Google Cloud Storage
    bucket = storage_client.get_bucket(bucket_name)
    
    # Get the list of all blobs in the bucket
    blobs = bucket.list_blobs()
    
    # Get the list of pickle file names
    return [blob.name for blob in blobs if blob.name.endswith('.pickle')]

def download_file_from_github(url, local_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we got a valid response
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

def get_github_repo_files(user, repo, path):
    url = f"https://api.github.com/repos/{user}/{repo}/contents/{path}"
    response = requests.get(url)
    json_response = response.json()

    if isinstance(json_response, dict) and 'message' in json_response:
        st.error(f"Error getting files: {json_response['message']}")
        return []

    if isinstance(json_response, list):
        return [file['name'] for file in json_response if file['name'].endswith('.pickle')]
    
    st.error("Unexpected response format.")
    return []


def download_ifc_file_from_github(ifc_file_name):
    # GitHub repository's raw content path
    github_repo_raw_path = f'https://raw.githubusercontent.com/{github_user}/{github_repo}/main/{github_path}/'
    url = github_repo_raw_path + ifc_file_name
    local_path = os.path.join(tempfile.gettempdir(), ifc_file_name)  # using tempfile for cross-platform compatibility
    # Call the updated download_file_from_github function
    download_file_from_github(url, local_path)
    # Debugging code: st.write(local_path)
    return local_path

def upload_to_gcs(data, bucket_name, blob_name):
    credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"])
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    # List all blobs and convert the iterator to a list
    blobs = list(bucket.list_blobs())    
    # Delete all existing blobs in the bucket
    if len(blobs) > 0:
        bucket.delete_blobs(blobs)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(data)
    # Make the blob publicly readable
    blob.make_public()
    return blob.public_url

# GitHub repository details
github_user = 'VolgardTheScientist'
github_repo = 'DungBeetleApp'
github_path = 'warehouse'

pickle_files = get_github_repo_files(github_user, github_repo, github_path)

# GitHub repository's raw content path
github_repo_raw_path = f'https://raw.githubusercontent.com/{github_user}/{github_repo}/main/{github_path}/'
path = github_repo_raw_path

dataframes = {}

column_map = {
    'PredefinedType': 'Product Type',
    'Material': 'Material',
    'PropertySets.Pset_ManufacturerTypeInformation.Manufacturer': 'Manufacturer',
    'PropertySets.Pset_ManufacturerTypeInformation.ModelLabel': 'Model',
    'PropertySets.Pset_ManufacturerTypeInformation.ArticleNumber': 'Article number',
    'QuantitySets.ArchiCADQuantities.Length (A)': 'Lenght',
    'QuantitySets.ArchiCADQuantities.Width': 'Width',
    'QuantitySets.ArchiCADQuantities.Height': 'Height',
    'PropertySets.Pset_ManufacturerTypeInformation.ProductionYear': 'Production year',
    'PropertySets.D4D.10_Connection_type': 'Connection type',
    'PropertySets.D4D.50_Planned_decosntruction_date': 'Approx. availability date',
    'Global ID': 'Global ID',
    'Project ID': 'Project ID',
    'Town': 'Town',
    'Country': 'Country',
    'Complete address': 'Complete address',
    'latitude': 'latitude',
    'longitude': 'longitude'
}

tab_map = {
    'wh_IfcSanitaryTerminal': 'Sanitary fixtures & fittings',
    'wh_IfcCovering': 'Finishes',
    'wh_IfcWall': 'Walls',
    'wh_IfcDoor': 'Doors'
}

pickle_bucket_name = 'pickle_warehouse'
pickle_files = get_gcs_bucket_files(pickle_bucket_name)

for pickle_file in pickle_files:
    local_path = tempfile.gettempdir() + '/' + pickle_file  # using tempfile for cross-platform compatibility
    download_file_from_gcs(pickle_bucket_name, pickle_file, local_path)
    with open(local_path, 'rb') as f:
        df = pickle.load(f)

    # Keep only the columns present in both the dataframe and the column_map
    columns_to_keep = list(set(df.columns) & set(column_map.keys()))

    # Rearrange the columns according to the order in column_map
    ordered_columns = [col for col in column_map.keys() if col in columns_to_keep]
    df = df.loc[:, ordered_columns]

    df.rename(columns=column_map, inplace=True)
    df_name = pickle_file[:-7]
    dataframes[df_name] = df


# Make sure only the tabs that have a corresponding dataframe are displayed
tab_names = [tab_map.get(df_name, df_name) for df_name in dataframes.keys() if df_name in tab_map]

selected_tab = st.sidebar.selectbox("Select a product group", tab_names)

def download_product_by_guid(input_file_name, guid):
    src_ifc_file = ifcopenshell.open(download_ifc_file_from_github(f"{input_file_name}.ifc"))

    new_ifc_file = ifcopenshell.file(schema="IFC4")
    product = src_ifc_file.by_guid(guid)
    new_product = new_ifc_file.add(product)

    # Copy over the IfcUnitAssignment and related IfcSIUnits
    original_project = src_ifc_file.by_type('IfcProject')[0]
    new_project = new_ifc_file.add(original_project)

    for unit_assignment in src_ifc_file.by_type("IfcUnitAssignment"):
        new_project.UnitsInContext = new_ifc_file.add(unit_assignment)

    for unit in src_ifc_file.by_type("IfcUnit"):
        new_project.UnitsInContext.Units.append(new_ifc_file.add(unit))

    new_ifc_file_str = new_ifc_file.to_string()
    
    return new_ifc_file_str, f"{os.path.splitext(input_file_name)[0]}_{guid}.ifc"


def get_binary_file_downloader_link(file_path, file_label):
    with open(file_path, "rb") as f:
        bytes_content = f.read()
    b64 = base64.b64encode(bytes_content).decode()
    href = f'<a download="{file_label}" href="data:application/octet-stream;base64,{b64}">Download {file_label}</a>'
    return href

def AgGrid_with_display_rules(df):
    gd = GridOptionsBuilder.from_dataframe(df)
    gd.configure_pagination(enabled=True)
    gd.configure_default_column(editable=False, groupable=True)
    gd.configure_selection(selection_mode='multiple', use_checkbox=True)
    gridoptions = gd.build()
    grid_table = AgGrid(df, gridOptions=gridoptions,
                        update_mode=GridUpdateMode.SELECTION_CHANGED,
                        height=400,
                        allow_unsafe_jscode=True
                        )
    sel_row = grid_table["selected_rows"]
    st.write(sel_row)
    return grid_table, sel_row

# Note we can use theme="balham" toas AgGrid argument past the allow_unsafe to change colours

def create_user_interface():
    for df_name, df in dataframes.items():
        if tab_map.get(df_name, df_name) == selected_tab:
            st.write('Filter the database below to find suitable product and to download the IFC digital product representation')
            grid_table, sel_row = AgGrid_with_display_rules(df)
            sel_row_for_map = pd.DataFrame(sel_row)
            # st.write("See map below for location of our building products, choose product group from the sidebar")
            # Initialize the columns
            col1, col2 = st.columns(2)

            with col1:
                st.subheader('Product location')             
                st.map(sel_row_for_map)
            with st.sidebar:
                st.write('To preview & download an IFC file, select a single product from the list and press download button below')
            if 'Global ID' in sel_row_for_map.columns and not sel_row_for_map.empty:
                Global_ID = sel_row_for_map['Global ID'].iloc[0]
                Global_ID = str(Global_ID)
            else:
                Global_ID = None

            if 'Project ID' in sel_row_for_map.columns and not sel_row_for_map.empty:
                Project_ID = sel_row_for_map['Project ID'].iloc[0]
                Project_ID = str(Project_ID)
            else:
                Project_ID = None       

            with st.sidebar:
                input_file_name = Project_ID
                input_guid = None  # Initialize input_guid as None

                # Initialize url_to_ifc_file as an empty string
                url_to_ifc_file = ''
                url = None

                # Check if the 'Global ID' column exists in the dataframe
                if 'Global ID' in sel_row_for_map.columns:
                    input_guid = sel_row_for_map['Global ID'].iloc[0]

                if st.button("Preview"):
                    if input_file_name and input_guid:
                        new_ifc_file_str, new_ifc_file_name = download_product_by_guid(input_file_name, input_guid)

                        # Upload the IFC data to Google Cloud Storage
                        url_to_ifc_file = upload_to_gcs(new_ifc_file_str, 'streamlit_warehouse', new_ifc_file_name)
                        url = url_to_ifc_file

            # Call the IFC viewer function
            with col2:
                st.subheader('Product preview')  
                ifc_viewer(url)

            st. write('To order the products export your selection to Excel by clicking with the right mouse button on the spreadsheet. Send your selection to dung.beetle@reuse.com')

create_user_interface()
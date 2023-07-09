import os
import pandas as pd
import pickle
import streamlit as st
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
import ifcopenshell
import tempfile
import base64
import requests

# def download_file_from_github(url, local_path):
#     response = requests.get(url)
#     with open(local_path, 'wb') as f:
#         f.write(response.content)

def download_file_from_github(url, local_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we got a valid response
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def get_github_repo_files(user, repo, path):
    url = f"https://api.github.com/repos/{user}/{repo}/contents/{path}"
    response = requests.get(url)
    files = [file['name'] for file in response.json() if file['name'].endswith('.pickle')]
    return files

def download_ifc_file_from_github(ifc_file_name):
    # GitHub repository's raw content path
    github_repo_raw_path = f'https://raw.githubusercontent.com/{github_user}/{github_repo}/main/{github_path}/'
    url = github_repo_raw_path + ifc_file_name
    local_path = os.path.join(tempfile.gettempdir(), ifc_file_name)  # using tempfile for cross-platform compatibility
    # Call the updated download_file_from_github function
    download_file_from_github(url, local_path)
    # Debugging code: st.write(local_path)
    return local_path


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

for pickle_file in pickle_files:
    url = github_repo_raw_path + pickle_file
    local_path = tempfile.gettempdir() + '/' + pickle_file  # using tempfile for cross-platform compatibility
    download_file_from_github(url, local_path)
    with open(local_path, 'rb') as f:
        df = pickle.load(f)
    # Rest of your code...

    # Keep only the columns present in both the dataframe and the column_map
    columns_to_keep = list(set(df.columns) & set(column_map.keys()))

    # Rearrange the columns according to the order in column_map
    ordered_columns = [col for col in column_map.keys() if col in columns_to_keep]
    df = df.loc[:, ordered_columns]

    df.rename(columns=column_map, inplace=True)
    df_name = pickle_file[:-7]
    dataframes[df_name] = df

st.set_page_config(layout="wide")
st.title("Digital material warehouse")

# Make sure only the tabs that have a corresponding dataframe are displayed
tab_names = [tab_map.get(df_name, df_name) for df_name in dataframes.keys() if df_name in tab_map]

selected_tab = st.sidebar.selectbox("Select a product group", tab_names)

def download_product_by_guid(input_file_name, guid):
    # Load the source IFC file
    ifc_file_path = download_ifc_file_from_github(f"{input_file_name}.ifc")
    st.write(f"Attempting to open file at: {ifc_file_path}")
    src_ifc_file = ifcopenshell.open(ifc_file_path)

    # Create a new IFC file (IFC4 schema)
    new_ifc_file = ifcopenshell.file(schema="IFC4")

    # Extract the requested product by GUID
    product = src_ifc_file.by_guid(guid)

    # Add the product and its PSets and QSets to the new IFC file
    new_ifc_file.add(product)


    # Check if the downloaded file is a valid IFC file by adding a try-except block when opening the file
    try:
        src_ifc_file = ifcopenshell.open(ifc_file_path)
    except Exception as e:
        st.write(f"Failed to open IFC file. Exception: {e}")
        return None, None

    # Save the new IFC file as a temporary file
    new_ifc_file_name = f"{os.path.splitext(ifc_file_path)[0]}_{guid}.ifc"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as temp_file:
        new_ifc_file.write(temp_file.name)
        temp_file_path = temp_file.name

    return temp_file_path, new_ifc_file_name

def get_binary_file_downloader_link(file_path, file_label):
    with open(file_path, "rb") as f:
        bytes_content = f.read()
    b64 = base64.b64encode(bytes_content).decode()
    href = f'<a download="{file_label}" href="data:application/octet-stream;base64,{b64}">Download {file_label}</a>'
    return href

def AgGrid_with_display_rules():
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
    return grid_table, sel_row

# Note we can use theme="balham" toas AgGrid argument past the allow_unsafe to change colours

for df_name, df in dataframes.items():
    if tab_map.get(df_name, df_name) == selected_tab:
        st.write('Filter the database below to find suitable product and to download the IFC digital product representation')
        grid_table, sel_row = AgGrid_with_display_rules()
        sel_row_for_map = pd.DataFrame(sel_row)
        st.write("See map below for location of our building products, choose product group from the sidebar")
        st.map(sel_row_for_map)
        with st.sidebar:
            st.write('To download an IFC file, select a single product from the list and press download button below')

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

            # Check if the 'Global ID' column exists in the dataframe
            if 'Global ID' in sel_row_for_map.columns:
                input_guid = sel_row_for_map['Global ID'].iloc[0]

            if st.button("Preview"):
                if input_file_name and input_guid:  # Ensure both input_file_name and input_guid are not None
                    temp_file_path, new_ifc_file_name = download_product_by_guid(input_file_name, input_guid)

                    # Create a download link for the new IFC file
                    download_link = get_binary_file_downloader_link(temp_file_path, new_ifc_file_name)
                    st.markdown(download_link, unsafe_allow_html=True)

                    st. write('To order the products export your selection to Excel by clicking with the right mouse button on the spreadsheet. Send your selection to dung.beetle@reuse.com')



          # if st.button("Download"):
          #     if input_file_name and input_guid:  # Ensure both input_file_name and input_guid are not None
          #         ifc_file_path = os.path.join(path, f"{input_file_name}.ifc")
          #         temp_file_path, new_ifc_file_name = download_product_by_guid(ifc_file_path, input_guid)

          #         # Create a download link for the new IFC file
          #         download_link = get_binary_file_downloader_link(temp_file_path, new_ifc_file_name)
          #         st.markdown(download_link, unsafe_allow_html=True)

          #         st. write('To order the products export your selection to Excel by clicking with the right mouse button on the spreadsheet. Send your selection to dung.beetle@reuse.com')

        

import streamlit as st
import os
import ifcopenshell
import pandas as pd
from tools import ifchelper
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
import numpy as np
import tempfile
import base64



# Define how to get geocoordinates from project's address
def get_project_geocoordinates(df):
    locator = Nominatim(user_agent="OpenMapQuest")
    # 1 - convenient function to delay between geocoding calls
    geocode = RateLimiter(locator.geocode, min_delay_seconds=1)
    # 2 - create location column
    df['location'] = df['Complete address'].apply(geocode)
    # 3 - create longitude, latitude, and altitude from location column (returns tuple)
    df['point'] = df['location'].apply(lambda loc: tuple(loc.point) if loc else (np.nan, np.nan, np.nan))
    # 4 - initialize latitude, longitude, and altitude columns with np.nan values
    df['latitude'] = np.nan
    df['longitude'] = np.nan
    df['altitude'] = np.nan
    # 5 - assign latitude, longitude, and altitude values from point column
    for idx, point in df['point'].iteritems():
        if not np.isnan(point[0]):
            df.at[idx, 'latitude'] = point[0]
            df.at[idx, 'longitude'] = point[1]
            df.at[idx, 'altitude'] = point[2]
    # 6 - convert latitude and longitude columns to numeric data types
    #df['latitude'] = pd.to_numeric(df['latitude'])
    #df['longitude'] = pd.to_numeric(df['longitude'])
    df['latitude'] = df['latitude'].astype('float64')
    df['longitude'] = df['longitude'].astype('float64')
    df['altitude'] = df['altitude'].astype('float64')
    # df['point'] = df['point'].astype('object')
    # df['location'] = df['location'].astype('object')
    # df = df.drop(columns=['location', 'point', 'altitude'])
    df.drop(columns=['location', 'point', 'altitude'], inplace=True)





# Define function for checking address data
def get_project_address(ifc_file):
    building = ifc_file.by_type("IfcBuilding")[0]
    building_ID = building.GlobalId if building.GlobalId else ""
    street = building.BuildingAddress[4][0] if building.BuildingAddress[4][0] else ""
    town = building.BuildingAddress[6] if building.BuildingAddress[6] else""
    canton = building.BuildingAddress[7] if building.BuildingAddress[7] else ""
    post_code = building.BuildingAddress[8] if building.BuildingAddress[8] else ""
    country = building.BuildingAddress[9] if building.BuildingAddress[9] else ""
    complete_address = [street, ', ', post_code, ', ',town, ', ',canton, ', ',country]
    complete_address = ''.join(complete_address)
    return building_ID, street, post_code, town, canton, country, complete_address

# Define the list of IfcEntities
IfcEntities = ["IfcSanitaryTerminal", "IfcDoor", "IfcCovering", "IfcWall"]

# Create a dictionary to store the dataframes
dataframes = {}
for entity in IfcEntities:
    dataframes["wh_" + entity] = pd.DataFrame()

uploaded_file = st.file_uploader("Upload IFC file", type="ifc")
if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False) as fp:
        fp.write(uploaded_file.getvalue())
        temp_path = fp.name
    
    # Open the IFC file
    ifc_file = ifcopenshell.open(temp_path)
    # Get the project address
    ### building_ID, street, post_code, town, canton, country, complete_address = get_project_address(ifc_file)
    # Loop through the IfcEntities and append data to the respective dataframe
    for entity in IfcEntities:
        warehouse_data = ifchelper.get_objects_data_by_class(ifc_file, entity)
        df = ifchelper.create_pandas_dataframe(warehouse_data)
        df['Building ID'] = building_ID
        df['Project ID'] = uploaded_file.name[:-4]
        df['Street'] = street
        df['Post code'] = post_code
        df['Town'] = town
        df['Canton'] = canton
        df['Country'] = country
        df['Complete address'] = complete_address
        ### get_project_geocoordinates(df)
        # Remove rows with missing latitude or longitude values
        df = df.dropna(subset=['latitude', 'longitude'])
        dataframes["wh_" + entity] = pd.concat([dataframes["wh_" + entity], df], ignore_index=True)

    # Remove the temporary file
    os.unlink(temp_path)

# Print the dataframes
for entity, df in dataframes.items():
    st.write(f"{entity}:")
    st.write(df)
    st.map(df)
    pickle_path = os.path.join(tempfile.gettempdir(), f"{entity}.pickle")
    df.to_pickle(pickle_path)

    # Create download button for the generated pickle
    if st.button(f'Download {entity} Dataframe as Pickle'):
        with open(pickle_path, 'rb') as f:
            bytes = f.read()
            b64 = base64.b64encode(bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download=\'{entity}.pickle\'>\
                Click to download {entity} dataframe pickle</a>'
            st.markdown(href, unsafe_allow_html=True)

import streamlit as st
import os
import ifcopenshell
import pandas as pd
from tools import ifchelper
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
import numpy as np


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

# Load the list of project file names
project_file_names_path = r"C:\Users\Piotr\dung-beetle\dung-beetle-app\warehouse\ProjectFileNames.csv"
project_file_names = set()
if os.path.exists(project_file_names_path):
    with open(project_file_names_path, "r") as f:
        project_file_names = set(line.strip() for line in f.readlines())

# Loop through the IFC files in the folder
folder_path = r"C:\Users\Piotr\dung-beetle\dung-beetle-app\warehouse"
for file_name in os.listdir(folder_path):
    if file_name.endswith(".ifc"):
        file_path = os.path.join(folder_path, file_name)
        if file_name in project_file_names:
            # Skip the file if it is already in the project file names list
            continue
        # Open the IFC file
        ifc_file = ifcopenshell.open(file_path)
        # Get the project address
        building_ID, street, post_code, town, canton, country, complete_address = get_project_address(ifc_file)
        # Loop through the IfcEntities and append data to the respective dataframe
        for entity in IfcEntities:
            warehouse_data = ifchelper.get_objects_data_by_class(ifc_file, entity)
            df = ifchelper.create_pandas_dataframe(warehouse_data)
            df['Building ID'] = building_ID
            df['Project ID'] = file_name[:-4]
            df['Street'] = street
            df['Post code'] = post_code
            df['Town'] = town
            df['Canton'] = canton
            df['Country'] = country
            df['Complete address'] = complete_address
            get_project_geocoordinates(df)
            # Remove rows with missing latitude or longitude values
            df = df.dropna(subset=['latitude', 'longitude'])
            dataframes["wh_" + entity] = pd.concat([dataframes["wh_" + entity], df], ignore_index=True)
        # Add the file name to the project file names list
        project_file_names.add(file_name)

# Save the updated project file names list
with open(project_file_names_path, "w") as f:
    f.writelines(name + "\n" for name in sorted(project_file_names))

# Print the dataframes
for entity, df in dataframes.items():
    st.write(f"{entity}:")
    st.write(df)
    st.map(df)
    pickle_path = os.path.join(folder_path, f"{entity}.pickle")
    df.to_pickle(pickle_path)

# Need to avoid Applying automatic fixes for column types to make the dataframe Arrow-compatible. -> probably a dtype is incorret - run print(df.dtypes) 
# The issue is caused by the get_project_geocoordinates(df) function
# This line solves it: df.drop(columns=['location', 'point', 'altitude'], inplace=True)
# One of the columns must contain an incorrect dtype

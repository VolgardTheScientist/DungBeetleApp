import ifcopenshell
import numpy as np
import pandas as pd
import streamlit as st
import tempfile
import time
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim


# ========== Functions ==========

def get_ifc_schema(ifc_file):
    try:
        schema = ifc_file.schema
        return f"The schema of your IFC file is: {schema}", schema
    except Exception as e:
        return f"An error occurred: {e}", schema
    
    
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


def display_project_address(building_ID, street, post_code, town, canton, country, complete_address):
    st.write("Building ID: " + building_ID)
    st.write("Street: " + street)
    st.write("Post code: " + post_code)
    st.write("Town: " + town)
    st.write("Canton: " + canton)
    st.write("Country: " + country)
    st.write("Complete address: " + complete_address)


def get_project_geocoordinates(complete_address):
    locator = Nominatim(user_agent="OpenMapQuest")
    geocode = RateLimiter(locator.geocode, min_delay_seconds=1)
    
    if complete_address is not None: 
        location = geocode(complete_address)
        point = tuple(location.point) if location else (np.nan, np.nan, np.nan)
        
        # Get the lat lon and alt for later inclusion in DataFrame
        latitude = point[0]
        longitude = point[1]

    else:
        latitude = np.nan
        longitude = np.nan

    df_geo_coordinates = pd.DataFrame({
        'lat': [latitude],
        'lon': [longitude]
        })   
          
    return df_geo_coordinates


def validate_geo_coordinates(df_geo_coordinates):
    coordinates_invalid = df_geo_coordinates.isnull().values.any()  
    return coordinates_invalid
    

def input_address():
    building = ifc_file.by_type("IfcBuilding")[0]
    building_ID = building.GlobalId if building.GlobalId else ""
    street = st.text_input('Street', 'Please provide street name and number')
    st.write('Street: ', street)
    post_code = st.text_input('Post code', "Please provide project's post code")
    st.write("Post code: " + post_code)
    town = st.text_input('Town', "Please provide project's town")
    st.write("Town: " + town)
    canton = st.text_input('Canton', "Please provide project's canton (leave empty if not applicable)")
    st.write("Canton: " + canton)
    country = st.text_input('Country', "Please provide project's country")
    st.write("Country: " + country)
    complete_address = [street, ', ', post_code, ', ',town, ', ',canton, ', ',country]
    complete_address = ''.join(complete_address)
    st.write("Complete address: " + complete_address)
    return building_ID, street, post_code, town, canton, country, complete_address


def display_coordinates_and_map():
    st.write("Dung Beetle calculated your project's coordinates:")
    st.dataframe(df_geo_coordinates, hide_index=True)
    st.write("Please review the map to check if the location is correct - if not, correct your address.")
    st.map(df_geo_coordinates)

# ========== Main app ==========

uploaded_file = st.file_uploader("Choose an IFC file", type=['ifc'])

if uploaded_file:
    st.subheader("STEP 1: Checking file schema")
    original_filename = uploaded_file.name.split('.')[0]
    with st.spinner("Your file's schema is being checked..."):
        time.sleep(1)
        tfile = tempfile.NamedTemporaryFile(delete=False) 
        tfile.write(uploaded_file.read())
        temp_path = tfile.name
        ifc_file = ifcopenshell.open(tfile.name)
        result, schema = get_ifc_schema(ifc_file)
        st.write(result)
        st.write(" ")

    if schema == "IFC4":
        st.subheader("STEP 2: Proceed to address check")
        coordinates_invalid = True
        complete_address = []
        proceed_to_step_3 = False
        building_ID, street, post_code, town, canton, country, complete_address = get_project_address(ifc_file)
        display_project_address(building_ID, street, post_code, town, canton, country, complete_address)
        df_geo_coordinates = get_project_geocoordinates(complete_address)
        coordinates_invalid = validate_geo_coordinates(df_geo_coordinates)
        if coordinates_invalid == True:
            st.warning("""Your address is faulty or incomplete, Dung Beetle cannot find project coordinates.
                   Please input full address below""")
            building_ID, street, post_code, town, canton, country, complete_address = input_address()
            df_geo_coordinates = get_project_geocoordinates(complete_address)     
            revised_coordinates_invalid = validate_geo_coordinates(df_geo_coordinates)
            if revised_coordinates_invalid == False:
                display_coordinates_and_map()
                st.success("Your project location was successfuly validated!")
                proceed_to_step_3 = True
        if coordinates_invalid == False:
            display_coordinates_and_map()
            st.success("Your project location was successfuly validated!")
            proceed_to_step_3 = True
        

    if schema =="IFC2X3":
        st.subheader("INFO:")
        st.write("IFC 2X3 is currently not supported.")

    if proceed_to_step_3 == True:
        st.subheader("STEP 3: Extract data from IFC and save as DataFrame")



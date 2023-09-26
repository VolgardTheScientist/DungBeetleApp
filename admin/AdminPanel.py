import csv
import ifcopenshell
import ifcopenshell.util.element as Element
import numpy as np
import pandas as pd
import streamlit as st
import tempfile
import time
import toml
import os
import sys

sys.path.append("../")
sys.path.append("./vendor/")

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from google.cloud import storage
from google.oauth2.service_account import Credentials
from ifcopenshell.util.shape import get_bbox, get_vertices
from tools.BoundingBox import *
from tools import ifchelper
from tools.ifchelper import get_material_psets
from vendor import ifcpatch


# ========== Initialize session states ==========

if 'step' not in st.session_state:
    st.session_state.step = 0

# === Approve button ===
if 'button_approve' not in st.session_state:
    st.session_state.button_approve = False

# ========== DEBUGGING ==========
# All IN PROGRESS & DEBUGGING code goes in this section:

def get_bbox_local(file, entity, conversion_factor): #PROTOTYPE
    data = []
    settings = ifcopenshell.geom.settings()
    
    elements = file.by_type(entity)
    for element in elements:
        found = False
        name = element.Name if element.Name else "N/A"
        global_id = element.GlobalId if element.GlobalId else "N/A"
        x, y, z = None, None, None  # Default values

        if hasattr(element, "Representation") and element.Representation is not None:
            for rep in element.Representation.Representations:
                if rep.is_a("IfcShapeRepresentation"):
                    for item in rep.Items:
                        if item.is_a("IfcBoundingBox"):
                            x = item.XDim
                            y = item.YDim
                            z = item.ZDim
                            found = True
                            break
                    if found:
                        break

            if not found:   
                elements = file.by_type(entity)
                for element in elements:
                    shape = ifcopenshell.geom.create_shape(settings, element)
                    geometry = shape.geometry
                    vertices = get_vertices(geometry)
                    bbox = get_bbox(vertices)

                    # Extract min and max coordinates
                    min_coords, max_coords = bbox

                    # Extract individual min and max values for x, y, z
                    minx, miny, minz = min_coords
                    maxx, maxy, maxz = max_coords

                    # Calculate dimensions
                    x = maxx - minx
                    y = maxy - miny
                    z = maxz - minz

            data.append([name, global_id, x, y, z])  # Only append here, inside the loop

    df = pd.DataFrame(data, columns=["Name", "Global ID", "Length_[cm]", "Width_[cm]", "Height_[cm]"])
    df["Conversion_factor"] = [conversion_factor] * len(df)
    df = multiply_and_round(df)

    return df


# ========== Page title and welcome message, page config ==========

st.set_page_config(layout="centered")
st.title("Dung Beetle Administration Panel")
st.markdown("""<p>Welcome to the Dung Beetle digital material warehouse administration page.</p>
    <p>Here you can check the quality of IFC files and if satisifed, merge them with the main warehouse DataFrame.</p>
    <p>Please note that at this time only <strong>IFC 4</strong> files are being accepted.</p>
    <p>Support for files in IFC 2x3 is currently under development.</p>""", unsafe_allow_html=True)
st.write("")

# Display the download link in the Streamlit sidebar
with st.sidebar:
    with st.expander("Dung Beetle - user manual"):
        st.write("""To upload your BIM project into the Dung Beetle Warehouse use the settings from the attached ArchiCAD template. 
                 At this stage ArchiCAD 26 is supported, templates for other BIM programms and previous ArchiCAD versions are planned for future releases.""")
        st.markdown("[Download ArchiCAD template](https://storage.googleapis.com/dungbeetle_media/DungBeetleMaterialWarehouseTemplateAC26.tpl)")

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

# Now you can use `correct_password` in your code

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
    except (FileNotFoundError, KeyError):
        pass  # Handle the exception gracefully or log an appropriate message if needed

# Now you can use `credentials` in your code

# ========== Create a Google Cloud Storage client ==========

# credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_APPLICATION_CREDENTIALS"]) -> This code worked with StreamlitCloud
storage_client = storage.Client(credentials=credentials)

# ========== Functions ==========
# === IFC Schema ===

def get_ifc_schema(ifc_file):
    try:
        schema = ifc_file.schema
        return f"The schema of your IFC file is: {schema}", schema
    except Exception as e:
        return f"An error occurred: {e}", schema


# === Get object properties & material data ===

def get_objects_data_by_class(file, class_type):
    objects_data = []
    objects = file.by_type(class_type)
    for object in objects:       
        objects_data.append({
                "Express ID": object.id(),
                "Global ID": object.GlobalId,
                "Parent's GUID": Element.get_aggregate(object).GlobalId
                if Element.get_aggregate(object)
                else "",             
                "Class": object.is_a(),
                "PredefinedType": Element.get_predefined_type(object),
                "Name": object.Name,
                "Level": Element.get_container(object).Name
                if Element.get_container(object)
                else "",
                "ObjectType": Element.get_type(object).Name
                if Element.get_type(object)
                else "",                  
                "QuantitySets": Element.get_psets(object, qtos_only=True),
                "PropertySets": Element.get_psets(object, psets_only=True),
                "Material": Element.get_material(object).Name
                if Element.get_material(object)
                else get_parts_material_data(object), 
                "MaterialPsets": get_material_psets(object)
                if Element.get_material(object)
                else "",         
                
        })       
    return objects_data


def get_parts_material_data(element):
    material_names = set()  # Using a set to avoid duplicate material names

    # Check if the object has parts (IsDecomposedBy)
    if hasattr(element, 'IsDecomposedBy'):
        for rel in element.IsDecomposedBy:
            for related_object in rel.RelatedObjects:
                # If the related object is a part
                if related_object.is_a("IfcBuildingElementPart"):
                    # Loop through the material associations for the part
                    if hasattr(related_object, 'HasAssociations'):
                        for association in related_object.HasAssociations:
                            if association.is_a("IfcRelAssociatesMaterial"):
                                material_select = association.RelatingMaterial
                                material_name = getattr(material_select, 'Name', 'N/A')
                                material_names.add(material_name)
                         
                                
    # Convert set to string
    material_names_str = ', '.join(material_names) if material_names else "N/A"

    return material_names_str  


# === Project Address, Geolocation & Map ===

def get_project_address(ifc_file):
    building = ifc_file.by_type("IfcBuilding")[0]
    building_ID = building.GlobalId if building.GlobalId else ""
    street = building.BuildingAddress[4][0] if building.BuildingAddress and building.BuildingAddress[4] and building.BuildingAddress[4][0] else ""
    town = building.BuildingAddress[6] if building.BuildingAddress and building.BuildingAddress[6] else ""
    canton = building.BuildingAddress[7] if building.BuildingAddress and building.BuildingAddress[7] else ""
    post_code = building.BuildingAddress[8] if building.BuildingAddress and building.BuildingAddress[8] else ""
    country = building.BuildingAddress[9] if building.BuildingAddress and building.BuildingAddress[9] else ""
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


# === Get IFC Entities to extract ===

def list_of_IfcEntities_from_CSV(csv_file_name):
    csv_entities = set()
    with open(csv_file_name, 'r', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            csv_entities.add(row[0])
    return csv_entities


# === Extract building products and save as independent components ===

def move_to_origin(ifc_file, guid):
    part = ifc_file.by_guid(guid)
    new_matrix = np.eye(4)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=part, matrix=new_matrix)
    return ifc_file

def move_storey_to_origin(ifc_file, storey):
    new_matrix = np.eye(4)
    storey.Name = "Floor plan"
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=storey, matrix=new_matrix)
    return ifc_file

def move_site_origin_to_000(ifc_file):
    site = ifc_file.by_type("IfcSite")[0]
    new_matrix = np.eye(4)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=site, matrix=new_matrix)
    return ifc_file

def move_building_origin_to_000(ifc_file):
    building = ifc_file.by_type("IfcBuilding")[0]
    building.Name = "Dung Beetle - Digital Material Warehouse"
    new_matrix = np.eye(4)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=building, matrix=new_matrix)
    return ifc_file

def change_project_name(ifc_file):
    project = ifc_file.by_type("IfcProject")[0]
    project.Name = "Dung Beetle - Digital Material Warehouse"
    return ifc_file

def change_site_name(ifc_file):
    site = ifc_file.by_type("IfcSite")[0]
    site.Name = "Dung Beetle - Digital Material Warehouse"
    return ifc_file

def extract_and_save_element(ifc_file, guid, save_dir, original_filename):
    extracted_ifc = ifcpatch.execute({"input": ifc_file, "file": ifc_file, "recipe": "ExtractElements", "arguments": [f"{guid}"]})
    extracted_ifc = move_to_origin(extracted_ifc, guid)
    extracted_ifc = move_site_origin_to_000(extracted_ifc)
    extracted_ifc = move_building_origin_to_000(extracted_ifc)
    extracted_ifc = change_project_name(extracted_ifc)
    extracted_ifc = change_site_name(extracted_ifc)
    # Adjust IfcStorey - move to 0,0,0 and rename to "Floor plans"
    z_min = 0.0  # Storey elevation we want to move our extracted file
    storey = extracted_ifc.by_type("IfcBuildingStorey")[0]
    extracted_ifc = move_storey_to_origin(extracted_ifc, storey)
    # Ensure the bottom edge of storey is located at 0,0
    storey.Elevation = z_min
    temp_file_path = os.path.join(save_dir, f"{original_filename}_{guid}.ifc")
    extracted_ifc.write(temp_file_path)


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
    
        st.subheader("STEP 2: Proceed to address check")
        coordinates_invalid = True
        complete_address = []
        proceed_to_step_3 = False
        proceed_to_step_4 = False
        proceed_to_step_5 = False
        proceed_to_step_6 = False
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


    if schema == "IFC4":
        if proceed_to_step_3 == True:
            st.subheader("STEP 3: Extract data from IFC and save as DataFrame")
            # Get the list of entities we want to extract from IFC file.
            # This list is set up outside the app and saved in CSV format.
            # Prepare DataFrame placeholders for object data from each IfcEntity 
            IfcEntities4 = list_of_IfcEntities_from_CSV("ifcentitiesIfc4.csv")
            ifcEntity4_dataframes = {}       
            with st.spinner("Getting Property & Quantity Set data for all objects sorted by IfcEntity"):
                time.sleep(1)
                for entity in IfcEntities4:
                    ifcEntity4_dataframes["temp_" + entity] = pd.DataFrame()           
                    warehouse_data = get_objects_data_by_class(ifc_file, entity)
                    generated_df = ifchelper.create_pandas_dataframe(warehouse_data)
                    rows, cols = generated_df.shape
                    if rows > 0:
                        st.write(f"{entity} DataFrame has {rows} items and {cols} properties.")
                        st.dataframe(generated_df)
            st.success("Property & Quantity Sets were successfully extracted!")
            proceed_to_step_4 = True

            if proceed_to_step_4 == True:
                st.subheader("STEP 4: Calculate object bounding box dimensions")
                # Get the length unit and its corresponding conversion factor
                length_unit, conversion_factor = get_length_unit_and_conversion_factor(ifc_file)
                conversion_factor = display_ifc_project_units(conversion_factor, length_unit)
                for entity in IfcEntities4:
                    dimensions_df = get_bounding_box_dimensions(ifc_file, entity, conversion_factor)
                    dim_rows, dim_cols = dimensions_df.shape
                    if dim_rows > 0:
                        st.write(f"{entity} DataFrame has {dim_rows} items and {dim_cols} properties.")
                        st.dataframe(dimensions_df)
                st.success("Object bounding box dimensions were calculated successfuly!")
                proceed_to_step_5 = True

                if proceed_to_step_5 == True:
                    st.subheader("STEP 5: Upload IFC data to Google Cloud Services")
                    folder_name = os.path.splitext(uploaded_file.name)[0]
                    col1, col2 = st.columns(2)  # Create two columns
                    with col1:
                        st.write("""If you are not satisifed with the content of the IFC file and wish not to merge it with the warehouse database, 
                                 click REJECT. This will remove all temporary data you have created, including DataFrames and IFC files.""")  
                        if st.button("REJECT"):
                            st.success("Data was rejected")      
                                  
                    with col2:
                        st.write("""If you've carefully examined the content of the dataframe and found it to be in line with the standards set by Dung Beetle, 
                                 click the APPROVE button. By doing so, your dataset will be incorporated into the primary database.""")
                        if st.button("APPROVE"):
                            bucket_name = 'ifc_warehouse'
                            bucket = storage_client.bucket(bucket_name)                    
                            blob = bucket.blob(f"{folder_name}/")
                            blob.upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')
                            proceed_to_step_6 = True

                        

                # === Extract buidling products and save as independent IFC files: ===

                if proceed_to_step_6 == True:
                    st.success(f"Folder '**{folder_name}**' was successfuly created in bucket '**{bucket_name}**'")
                    with st.spinner("Your products are being extracted..."):
                        # Check what IfcEntity types exist in the Ifc file
                        unique_entity_types = set()

                        for entity in ifc_file:
                            unique_entity_types.add(entity.is_a())  # 'is_a' gives the type of the entity

                        all_elements = []
                        for entity_type in unique_entity_types:
                            if entity_type in IfcEntities4:
                                elements_of_type = ifc_file.by_type(entity_type)
                                all_elements.extend(elements_of_type)

                        # Create a set to store unique IfcElement types in the file
                        unique_element_types = set()

                        # Create a local directory for saving parts:
                        save_dir = r"C:\Users\Piotr\Extracted_IFCs_001"

                        for elem in all_elements:
                            unique_element_types.add(elem.is_a())

                        # Loop through each unique IfcElement type to extract and save elements
                        for element_type in unique_element_types:
                            elements = ifc_file.by_type(element_type)
                            for element in elements:
                                guid = element.GlobalId
                                extract_and_save_element(ifc_file, guid, save_dir, original_filename)

                        
                        st.success(f"All elements have been extracted and saved.")



                       







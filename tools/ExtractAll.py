import csv
import streamlit as st
import ifcopenshell
import ifcopenshell.util
from ifcopenshell.util.selector import Selector
import ifcopenshell.util.placement 
import ifcopenshell.api
import numpy as np
import tempfile
from vendor import ifcpatch
import os
import time
import sys

sys.path.append('./vendor')

def list_of_IfcEntities_from_CSV():
    csv_entities = set()
    with open('ifcentities.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            csv_entities.add(row[0])
    return csv_entities

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

save_dir = r"C:\Users\Piotr\Extracted"

st.title('BIMease: extract all products')

st.markdown("""
This app will extract all products from your IFC file and save these as independent IFC files
""")

csv_entities = list_of_IfcEntities_from_CSV()

uploaded_file = st.file_uploader("Choose an IFC file", type=['ifc'])


if uploaded_file:
    original_filename = uploaded_file.name.split('.')[0]
    
    with st.spinner("Your products are being extracted..."):
        time.sleep(2)
        tfile = tempfile.NamedTemporaryFile(delete=False) 
        tfile.write(uploaded_file.read())
        temp_path = tfile.name
        ifc = ifcopenshell.open(tfile.name)

        # Get all IfcElement instances and populate the set with their types
        # all_elements = ifc.by_type("IfcElement")

        # Check what IfcEntity types exist in the Ifc file
        unique_entity_types = set()

        # Iterate through IFC file to check available IfcEntities, append them to unique_entity_types 
        for entity in ifc:
            unique_entity_types.add(entity.is_a())  # 'is_a' gives the type of the entity

        # DEBUGGING
        st.write(unique_entity_types)

        all_elements = []
        for entity_type in unique_entity_types:
            if entity_type in csv_entities:
                elements_of_type = ifc.by_type(entity_type)
                all_elements.extend(elements_of_type)

        # Create a set to store unique IfcElement types in the file
        unique_element_types = set()

        for elem in all_elements:
            unique_element_types.add(elem.is_a())

        # Loop through each unique IfcElement type to extract and save elements
        for element_type in unique_element_types:
            elements = ifc.by_type(element_type)
            for element in elements:
                guid = element.GlobalId
                extract_and_save_element(ifc, guid, save_dir, original_filename)

        st.write(f"All elements have been extracted and saved.")
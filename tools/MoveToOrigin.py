import streamlit as st
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util
import ifcopenshell.util.placement 
import ifcopenshell.api
import tempfile


def move_to_origin(ifc_file, guid):
    part = ifc_file.by_guid(guid)
    old_matrix = ifcopenshell.util.placement.get_local_placement(part.ObjectPlacement)
    # DEBUG: st.write(old_matrix)
    new_matrix = np.eye(4)
    # DEBUG: st.write(new_matrix)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=part, matrix=new_matrix)

    # Save the modified IFC file to a temporary location and return the path
    output_path = tempfile.mktemp(suffix=".ifc")
    ifc_file.write(output_path)
    return output_path

st.title('Move IFC Element to Origin')

uploaded_file = st.file_uploader("Choose an IFC file", type=['ifc'])
guid = st.text_input("Enter the GUID of the element to move:")

if uploaded_file and guid:
    tfile = tempfile.NamedTemporaryFile(delete=False) 
    tfile.write(uploaded_file.read())

    ifc_file = ifcopenshell.open(tfile.name)
    
    # Move the element to origin and get the modified IFC file path
    updated_ifc_path = move_to_origin(ifc_file, guid)
    
    # Read the modified IFC file as binary data
    with open(updated_ifc_path, "rb") as f:
        binary_ifc_data = f.read()
    
    # Provide a download button for the modified IFC file
    st.download_button(
        "Download Modified IFC File", 
        binary_ifc_data, 
        file_name='modified.ifc'
    )

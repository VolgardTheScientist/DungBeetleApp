import streamlit as st
import pandas as pd
import ifcopenshell
import tempfile

def extract_dimensions_from_ifc(file_path):
    # Parse the IFC file
    ifc_file = ifcopenshell.open(file_path)

    data = []

    # Get all entities in the file
    all_entities = ifc_file.by_type("IfcElement")
    
    for entity in all_entities:
        if hasattr(entity, "Representation"):
            for rep in entity.Representation.Representations:
                if rep.is_a("IfcShapeRepresentation"):
                    for item in rep.Items:
                        if item.is_a("IfcBoundingBox"):
                            name = entity.Name if entity.Name else "N/A"
                            global_id = entity.GlobalId if entity.GlobalId else "N/A"
                            x = item.XDim
                            y = item.YDim
                            z = item.ZDim
                            data.append([name, global_id, x, y, z])

    return pd.DataFrame(data, columns=["Name", "GlobalId", "X", "Y", "Z"])

# Streamlit app
st.title("IFC Bounding Box Extractor")

uploaded_file = st.file_uploader("Upload an IFC file", type=["ifc"])

if uploaded_file:
    # Save uploaded file to a temporary location
    tfile = tempfile.NamedTemporaryFile(delete=False) 
    tfile.write(uploaded_file.getvalue())

    with st.spinner("Extracting data from IFC..."):
        df = extract_dimensions_from_ifc(tfile.name)
        st.dataframe(df)

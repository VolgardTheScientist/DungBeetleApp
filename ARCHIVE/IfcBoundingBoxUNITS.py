import streamlit as st
import pandas as pd
import ifcopenshell
import tempfile

def extract_dimensions_from_ifc(file_path):
    # Parse the IFC file
    ifc_file = ifcopenshell.open(file_path)

    data = []

    # Get all entities of type IfcElement
    all_elements = ifc_file.by_type("IfcElement")
    
    for element in all_elements:
        if hasattr(element, "Representation"):
            for rep in element.Representation.Representations:
                if rep.is_a("IfcShapeRepresentation"):
                    for item in rep.Items:
                        if item.is_a("IfcBoundingBox"):
                            name = element.Name if element.Name else "N/A"
                            global_id = element.GlobalId if element.GlobalId else "N/A"
                            x = item.XDim
                            y = item.YDim
                            z = item.ZDim
                            data.append([name, global_id, x, y, z])

    return pd.DataFrame(data, columns=["Name", "GlobalId", "X", "Y", "Z"]), ifc_file

def get_length_unit(ifc_file):
    # Fetch the IfcProject entity (assuming there's only one in the file)
    project = ifc_file.by_type("IfcProject")[0]
    
    # Extract units from the IfcUnitAssignment
    for unit in project.UnitsInContext.Units:
        if unit.is_a("IfcSIUnit") and unit.UnitType == "LENGTHUNIT":
            # Return the name of the unit (e.g., "METER")
            return unit.Name

    return None

# Streamlit app
st.title("IFC Bounding Box Extractor")

uploaded_file = st.file_uploader("Upload an IFC file", type=["ifc"])

if uploaded_file:
    # Save uploaded file to a temporary location
    tfile = tempfile.NamedTemporaryFile(delete=False) 
    tfile.write(uploaded_file.getvalue())

    with st.spinner("Extracting data from IFC..."):
        df, ifc_file = extract_dimensions_from_ifc(tfile.name)
        st.dataframe(df)

        # Display the length unit
        length_unit = get_length_unit(ifc_file)
        if length_unit:
            st.write(f"The model was created using units of: {length_unit}")
        else:
            st.write("Could not determine the length unit used in the model.")

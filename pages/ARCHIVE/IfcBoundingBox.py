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

def get_length_unit_and_conversion_factor(ifc_file):
    # Fetch the IfcProject entity (assuming there's only one in the file)
    project = ifc_file.by_type("IfcProject")[0]
    
    # Extract units from the IfcUnitAssignment
    for unit in project.UnitsInContext.Units:
        if unit.is_a("IfcSIUnit") and unit.UnitType == "LENGTHUNIT":
            if unit.Name == "METRE" and unit.Prefix == None:
                return unit.Name, 100 #Convertion of M to CM
            elif unit.Name == "METRE" and unit.Prefix == "MILLI":
                return unit.Name, 0.1 #Convertion of MM to CM
            elif unit.Name == "METRE" and unit.Prefix == "CENTI":
                return unit.Name, 1 #No conversion required
    
    return None, 1  # Defaulting to a conversion factor of 1 if no matching SI unit is found


def get_length_unit(ifc_file):
    # Fetch the IfcProject entity (assuming there's only one in the file)
    project = ifc_file.by_type("IfcProject")[0]
    
    # Extract units from the IfcUnitAssignment
    for unit in project.UnitsInContext.Units:
        if unit.is_a("IfcSIUnit") and unit.UnitType == "LENGTHUNIT":
            # Return the name of the unit (e.g., "METER")
            return unit.Name

    return None

def rename_columns(df):
    new_column_names = {
        'X': 'Length_[cm]',
        'Y': 'Width_[cm]',
        'Z': 'Height_[cm]'
    }
    df.rename(columns=new_column_names, inplace=True)
    return df



# Function to multiply and round columns
def multiply_and_round(df, columns_to_multiply):
    for col in columns_to_multiply:
        df[col] = (df[col] * df['Conversion_factor']).round(1)
    return df

# List of columns to multiply
columns_to_multiply = ['X', 'Y', 'Z']





# Streamlit app
st.title("IFC Bounding Box Extractor")

uploaded_file = st.file_uploader("Upload an IFC file", type=["ifc"])

if uploaded_file:
    # Save uploaded file to a temporary location
    tfile = tempfile.NamedTemporaryFile(delete=False) 
    tfile.write(uploaded_file.getvalue())

    with st.spinner("Extracting data from IFC..."):
        df, ifc_file = extract_dimensions_from_ifc(tfile.name)
        
        # Get the length unit and its conversion factor
        length_unit, conversion_factor = get_length_unit_and_conversion_factor(ifc_file)
        # length_unit = get_length_unit(ifc_file)
        
        # Append the conversion factor to the dataframe
        df["Conversion_factor"] = [conversion_factor] * len(df)
        df = multiply_and_round(df, columns_to_multiply)
        rename_columns(df)

        st.dataframe(df)

        # Display the length unit and potentially a warning
        if length_unit:
            st.write(f"The model was created using units of: {length_unit}")
            if conversion_factor == 1 and length_unit not in ["METER", "MILIMETER", "CENTIMETER"]:
                st.warning("No SI unit defined in this project.")
        else:
            st.write("Could not determine the length unit used in the model.")

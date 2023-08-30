# DungBeetle - Digital Building Material Bank
# Copyright (C) 2023 Piotr Piotrowski
# <piotr.piotrowski@uni.li>
#
# This file is part of DungBeetle.
#
# DungBeetle is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# DungBeetle is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# See a copy of the GNU Lesser General Public License here:
# <http://www.gnu.org/licenses/>.

import pandas as pd
import streamlit as st
import ifcopenshell
import ifcopenshell.geom
from ifcopenshell.util.shape import get_x, get_y, get_z

def get_bounding_box_dimensions(file, entity, conversion_factor):
    data = []
    settings = ifcopenshell.geom.settings() 
     
    # DEBUG:
    # project = file.by_type("IfcProject")[0]
    # for unit in project.UnitsInContext.Units:
    #     if unit.is_a("IfcSIUnit") and unit.UnitType == "LENGTHUNIT":
    #         st.write(f"Unit Name: {unit.Name}, Prefix: {unit.Prefix}")
    
    elements = file.by_type(entity)
    for element in elements: 
        found = False   
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
                            found = True
                            break
                if found:
                    break
            if not found:
                representation = element.Representation.Representations[0]
                geometry = ifcopenshell.geom.create_shape(settings, representation)
                name = element.Name if element.Name else "N/A"
                global_id = element.GlobalId if element.GlobalId else "N/A"
                x = get_x(geometry)
                y = get_y(geometry)
                z = get_z(geometry)
                data.append([name, global_id, x, y, z])
                # DEBUG: # st.write(data)
    
    df = pd.DataFrame(data, columns=["Name", "Global ID", "Length_[cm]", "Width_[cm]", "Height_[cm]"])
    df["Conversion_factor"] = [conversion_factor] * len(df)
    # DEBUG: # st.write(df)
    # DEBUG: # st.write(conversion_factor)



    df = multiply_and_round(df)
    # DEBUG: # st.write(df)
    # DEBUG: # Check if 'Global ID' exists in df, if not add it
    if 'Global ID' not in df.columns:
        df['Name'] = None
        df['Global ID'] = None
        df['Length_[cm]'] = None
        df['Width_[cm]'] = None
        df['Height_[cm]'] = None
    
    return df




def get_bounding_box(file, conversion_factor=1.0):
    data = []
    settings = ifcopenshell.geom.settings()

    for element in file:
        try:
            if hasattr(element, "Representation"):
                found = False
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
                                found = True
                                break
                    if found: 
                        break

                if not found:
                    representation = element.Representation.Representations[0]
                    geometry = ifcopenshell.geom.create_shape(settings, representation)
                    name = element.Name if element.Name else "N/A"
                    global_id = element.GlobalId if element.GlobalId else "N/A"
                    x = get_x(geometry)
                    y = get_y(geometry)
                    z = get_z(geometry)
                    data.append([name, global_id, x, y, z])

        except Exception as e:
            print(f"Failed to process {element.GlobalId} due to {e}. Skipping...")

    df = pd.DataFrame(data, columns=["Name", "Global ID", "Length_[cm]", "Width_[cm]", "Height_[cm]"])
    df["Conversion_factor"] = [conversion_factor] * len(df)
    df = multiply_and_round(df)

    if 'Global ID' not in df.columns:
        df['Name'] = None
        df['Global ID'] = None
        df['Length_[cm]'] = None
        df['Width_[cm]'] = None
        df['Height_[cm]'] = None

    return df




# ========== Get IfcBoundingBox dimensions ==========

def get_IfcBoundingBox_dimensions(file, entity, conversion_factor):
    data = []
    
    elements = file.by_type(entity)
    for element in elements:
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
    
    df = pd.DataFrame(data, columns=["Name", "Global ID", "Length_[cm]", "Width_[cm]", "Height_[cm]"])
    df["Conversion_factor"] = [conversion_factor] * len(df)
    df = multiply_and_round(df)
    # Check if 'Global ID' exists in df, if not add it
    if 'Global ID' not in df.columns:
        df['Name'] = None
        df['Global ID'] = None
        df['Length_[cm]'] = None
        df['Width_[cm]'] = None
        df['Height_[cm]'] = None
    
    return df

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


# Function to multiply and round columns
def multiply_and_round(df):
    # List of columns to multiply
    columns_to_multiply = ["Length_[cm]", "Width_[cm]", "Height_[cm]"]   
    for col in columns_to_multiply:
        df[col] = (df[col] * df['Conversion_factor']).round(1)
    return df

def display_ifc_project_units(conversion_factor, length_unit):       
    if length_unit:
        st.write(f"The model was created using units of: {length_unit}")
        if conversion_factor == 1 and length_unit not in ["METER", "MILIMETER", "CENTIMETER"]:
            st.warning("No SI unit defined in this project.")
    else:
        st.write("Could not determine the length unit used in the model.")

def merge_dimensions_with_generated_df(dimensions_df, generated_df):
    # Create an empty DataFrame if dimensions_df is empty
    if dimensions_df.empty:
        for col in ['Length_[cm]', 'Width_[cm]', 'Height_[cm]']:
            generated_df[col] = None
    else:
        # Merge only selected columns from dimensions_df into generated_df based on "Global ID"
        selected_columns = ['Global ID', 'Length_[cm]', 'Width_[cm]', 'Height_[cm]']
        filtered_dimensions_df = dimensions_df[selected_columns]
        
        generated_df = pd.merge(
            generated_df,
            filtered_dimensions_df,
            on='Global ID',
            how='left'
        )
    return generated_df
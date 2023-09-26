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
from ifcopenshell.util.shape import get_x, get_y, get_z, get_bbox, get_vertices


# ========== Get BoundingBox dimensions ==========


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
                    vertices = get_vertices(element, geometry)
                    bbox = get_bbox(vertices)

                    # Extract min and max coordinates
                    min_coords, max_coords = bbox

                    # Extract individual min and max values for x, y, z
                    minx, miny, minz = min_coords
                    maxx, maxy, maxz = max_coords

                    # Calculate dimensions
                    length_x = maxx - minx
                    width_y = maxy - miny
                    height_z = maxz - minz

                    # Store into DataFrame
                    data = {
                        'Length_X': [length_x],
                        'Width_Y': [width_y],
                        'Height_Z': [height_z]
                    }

            data.append([name, global_id, x, y, z])  # Only append here, inside the loop

    df = pd.DataFrame(data, columns=["Name", "Global ID", "Length_[cm]", "Width_[cm]", "Height_[cm]"])
    df["Conversion_factor"] = [conversion_factor] * len(df)
    df = multiply_and_round(df)

    return df


def get_bounding_box_dimensions(file, entity, conversion_factor):
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
                representation = element.Representation.Representations[0] if element.Representation else None
                try:
                    if representation:
                        geometry = ifcopenshell.geom.create_shape(settings, representation)
                        x = get_x(geometry)
                        y = get_y(geometry)
                        z = get_z(geometry)
                    else:
                        x, y, z = None, None, None
                except RuntimeError:
                    print(f"Failed to process representation for element {element.GlobalId}. Skipping.")
                    x, y, z = None, None, None  # set to None if failed

            data.append([name, global_id, x, y, z])  # Only append here, inside the loop
            
    df = pd.DataFrame(data, columns=["Name", "Global ID", "Length_[cm]", "Width_[cm]", "Height_[cm]"])
    df["Conversion_factor"] = [conversion_factor] * len(df)
    df = multiply_and_round(df)

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


# Function to multiply and round columns using the conversion factor
def multiply_and_round(df):
    columns_to_multiply = ["Length_[cm]", "Width_[cm]", "Height_[cm]"]
    
    for col in columns_to_multiply:
        if pd.isna(df[col]).any():  # Checks if any value in the column is None or NaN
            df[col] = df[col] * df['Conversion_factor']
        else:
            df[col] = (df[col] * df['Conversion_factor']).round(1)
    
    return df


def display_ifc_project_units(conversion_factor, length_unit):       
    if length_unit:
        st.write(f"The model was created using units of: {length_unit}, the proposed conversion factor is: {conversion_factor}")
        text_input = st.text_input(
            "If you wish to override the conversion factor, provide it in the box below:"
            )
        if text_input:
            st.write("The new conversion factor is: ", text_input)
            try:
                float_value = float(text_input)
            except ValueError:
                st.write("Invalid input. Please enter a number.")
                st.stop()
            conversion_factor = float_value
        if conversion_factor == 1 and length_unit not in ["METER", "MILIMETER", "CENTIMETER"]:
            st.warning("No SI unit defined in this project.")
    else:
        st.write("Could not determine the length unit used in the model.")
    return conversion_factor


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
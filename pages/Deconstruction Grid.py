#%%

import pandas as pd
import ifcopenshell
import numpy as np
from tools import ifchelper
from tools import pandashelper
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, DataReturnMode
import streamlit as st
import streamlit.components.v1 as components
import altair as alt
import base64
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)

session = st.session_state


def callback_upload():
    st.session_state["file_name"] = st.session_state["uploaded_file"].name
    st.session_state["is_file_uploaded"] = True
    st.session_state["array_buffer"] = st.session_state["uploaded_file"].getvalue()
    st.session_state["ifc_file"] = ifcopenshell.file.from_string(st.session_state["uploaded_file"].getvalue().decode("utf-8"))

@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

def get_ifc_pandas():
    data = ifchelper.get_objects_data_by_class(
        session.ifc_file,
        "IfcBuildingElement"
    )
    df = ifchelper.create_pandas_dataframe(data)
    return df

def get_ifc_data():
    file_data = ifchelper.get_objects_data_by_class(
        session.ifc_file,
        "IfcBuildingElement"
    )
    return file_data

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df

def df_with_location_data():
    df_loc = get_ifc_pandas()
    df_loc['Country']='Liechtenstein'
    df_loc['City']='Vaduz'
    df_loc['lat']='47.1410'
    df_loc['lon']='9.5209'
    df_loc.loc[0, ["lat"]] = '47.3904'
    df_loc.loc[0, ["lon"]] = '8.0457'
    df_loc.loc[0, ["Country"]] = 'Switzerland'
    df_loc.loc[0, ["City"]] = 'Aarau'
    df_loc['lat'] = df_loc['lat'].astype(float)
    df_loc['lon'] = df_loc['lon'].astype(float)
    return df_loc

def draw_configured_aggrid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_pagination(paginationAutoPageSize=True) #Add pagination
    gb.configure_side_bar() #Add a sidebar
    #gb.configure_selection(selection_mode="multiple", use_checkbox=True)
    gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren="Group checkbox select children") #Enable multi-row selection, but it crashes 
    gridOptions = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=gridOptions,
        data_return_mode='AS_INPUT', 
        update_mode='MODEL_CHANGED', 
        fit_columns_on_grid_load=False,
        enable_enterprise_modules=True,
        height=600, 
        width='100%',
        reload_data=False #it was originaly set to True, but then it casues the selection to disappear on multiselect, presumably with False data is not being sent back to streamlit... - review this https://pablocfonseca-streamlit-aggrid-examples-example-jyosi3.streamlit.app/
    )

    df = grid_response['data']
    selected = grid_response['selected_rows'] 
    df = pd.DataFrame(selected) #Pass the selected rows to a new dataframe df

def create_Dung_Beetle_columns(df):    
    df.insert(9, "Volume", None, allow_duplicates=False)
    df.insert(10, "Mass", None, allow_duplicates=False)
    df.insert(11, "Embodied_CO2", None, allow_duplicates=False)    
    return df

def calculate_CO2_from_material_weight_and_AC_data(df):
    df['MaterialPsets.Embodied Carbon'] = df['MaterialPsets.Embodied Carbon'].fillna(0) 
    df['MaterialPsets.Embodied Carbon'] = df['MaterialPsets.Embodied Carbon'].str.rstrip(" (kgCO₂/kg)") 
    df['MaterialPsets.Embodied Carbon'] = df['MaterialPsets.Embodied Carbon'].astype(float)
    df["Carbon_from_material_calculations"] = df['MaterialPsets.Embodied Carbon'] * df['Mass']

def consolidate_volume_data(df):
    df_keys = list(df)
    matchers = ['NetVolume', 'Volume (Net)', 'Volumen (netto)']
    matching = [s for s in df_keys if any(xs in s for xs in matchers)]

    print(matching)

    for text in matching:
        print(text)
        df['Volume'] = df['Volume'].fillna(df[text])
    return df

def old_consolidate_volume_data(df):
    df['Volume'] = df['Volume'].fillna(df["QuantitySets.Qto_SlabBaseQuantities.NetVolume"])
    df['Volume'] = df['Volume'].fillna(df["QuantitySets.Component Quantities.Schicht/Komponenten Volumen (netto)"])
    return df

def consolidate_mass_data(df):
    df_keys = list(df)
    matchers = ['Mass']
    matching = [s for s in df_keys if any(xs in s for xs in matchers)]

    print(matching)

    for text in matching:
        print(text)
        df['Mass'] = df['Mass'].fillna(df[text])
    return df

def consolidate_carbon_data(df):
    df_keys = list(df)
    matchers1 = ['CO2']
    matching1 = [s for s in df_keys if any(xs in s for xs in matchers1)]

    matchers2 = ['Embodied Carbon']
    matching2 = [s for s in df_keys if any(xs in s for xs in matchers2)]

    for text in matching1:
        print(text)
        df['Embodied_CO2'] = df['Embodied_CO2'].fillna(df[text])

    for text in matching2:
        print(text)
        df['Embodied_CO2'] = df['Embodied_CO2'].fillna(df[text])

    return df

def drop_containers(df):
    nc = df.drop(df[df["Global ID"].isin(df["Parent's GUID"])].index) 
    return nc

def drop_parts(df):
    np = df.drop(df[df["Parent's GUID"].isin(df["Global ID"])].index) 
    return np

def cleanup_CO2_data(df):
    df["Embodied_CO2"] = df["Embodied_CO2"].str.rstrip(" (kgCO₂)")  
    df["Embodied_CO2"] = df["Embodied_CO2"].str.rstrip(" (kgCO₂/kg)")  
    df["Embodied_CO2"] = df["Embodied_CO2"].fillna(0)
    df["Embodied_CO2"] = df["Embodied_CO2"].astype(float)
    return df

def cleanup_mass_data(df):
    df["Mass"] = df["Mass"].replace(r'^\s*$', np.nan, regex=True)
    df["Mass"] = df["Mass"].fillna(0)
    df["Mass"] = df["Mass"].astype(float)
    return df

def cleanup_material_data(df):
    df["Material"] = df["Material"].astype(str)
    df["Material"] = df["Material"].replace(r'^\s*$', np.nan, regex=True)
    df["Material"] = df["Material"].fillna("Not defined")
    return df

def cleanup_profile_material_data(df):
    if "PropertySets.ArchiCADProperties.Structure Type" in df.columns:
        df.loc[df["PropertySets.ArchiCADProperties.Structure Type"] == "Complex Profile", "Material"] = df["PropertySets.ArchiCADProperties.Building Materials (All)"]
    elif "PropertySets.ArchiCADProperties.Struktur-Typ" in df.columns:
        df.loc[df["PropertySets.ArchiCADProperties.Struktur-Typ"] == "Profil", "Material"] = df["PropertySets.ArchiCADProperties.Baustoffe (Alle)"]
    return df

def consolidate_connection_data(df):
    df["Connection_type"] = df["Connection_type"].fillna(df["MaterialPsets.Connection type"])
    return df

def rename_connection_type_column(df):
    df.columns = df.columns.str.replace('PropertySets.D4D.10_Connection_type', 'Connection_type')
    consolidate_connection_data(df)
    df["Connection_type"] = df["Connection_type"].fillna("Not defined")
    return df

def create_chart(df, yaxis):
    connection_to_color =  {
        'Fixed (other)' : '#db4132', 
        'Cast in-situ' : '#db4132',
        'Resin bonding' : '#db4132',   
        'Adhesive' : '#f78d53', 
        'Welded' : '#f78d53', 
        'Riveted fixing' : '#fed183',   
        'PU-foam' : '#fed183', 
        'Mortar (cement)' : '#fed183',     
        'Mortar (lime)' : '#f9f7ae',
        'Nail fixing' : '#cae986',   
        'Doweled fixing' : '#84ca68', 
        'Screw fixing' : '#84ca68',     
        'Friction fixing' : '#33a054',
        'Bolt fixing' : '#33a054',   
        'Clip fixing' : '#33a054', 
        'Loose laid' : '#33a054',     
        'Hanging hooks' : '#33a054',
        'Unknown' : '#c0c0c0',
        'Not defined' : '#c0c0c0',
        'Mixed' : '#969696',
    }  

    present_domains = [connection for connection in connection_to_color.keys() if connection in df['Connection_type'].unique()]

    domain_scale = alt.Scale(
            domain=present_domains,
            range=[connection_to_color[domain] for domain in present_domains],
            )

    chart_vol = alt.Chart(df).mark_bar().encode(
        x='Material',
        y=yaxis,
        tooltip=['Material', 'Name', 'Class', 'PredefinedType', 'Global ID'],
        color=alt.Color('Connection_type', scale=domain_scale),
        shape=alt.Shape('Connection_type', scale=alt.Scale(domain=domain_scale.domain),
        
    )).properties(height=700).interactive()
    return chart_vol

def execute():
    st.title("Dung Beetle Deconstruction Grid")
    st.write(
        """Upload your IFC project data to review your deconstruction and material recovery potential. Remember to assign Connection Types to your building components. 
        """
)
    
    session["Dataframe"] = get_ifc_pandas()
    #df = get_ifc_pandas()
    
    data = ifchelper.get_objects_data_by_class(
        session.ifc_file,
        "IfcElement"
    )

    df = ifchelper.create_pandas_dataframe(data)    

    #st.dataframe(df)

    #configured_aggrid()
    #AgGrid(df)
    #draw_aggrid_df(df)
    
    #st.write("Check if DataFrame is being created:")
    #st.dataframe(df)
    create_Dung_Beetle_columns(df)    
    rename_connection_type_column(df)
    
    consolidate_volume_data(df)
    consolidate_mass_data(df)
    consolidate_carbon_data(df)
    consolidate_connection_data(df)
    #st.dataframe(df)
    cleanup_CO2_data(df)    
    cleanup_material_data(df)
    cleanup_profile_material_data(df)
    cleanup_mass_data(df)
    #calculate_CO2_from_material_weight_and_AC_data(df)
    nc = drop_containers(df)
    np = drop_parts(df)
    

    #st.header("All building components except container elements:")
    #draw_configured_aggrid(nc)

    # Create charts
    chart_vol = create_chart(nc, "Volume")
    chart_mass = create_chart(nc, "Mass")
    chart_CO2 = create_chart(nc, "Embodied_CO2")
    #chart_vol = alt.Chart(np).mark_bar().encode(x="Material", y="Volume", color="Connection_type", tooltip=['Name', 'Class', 'PredefinedType', 'Global ID']).properties(height=700)
    #chart_mass = alt.Chart(nc).mark_bar().encode(x="Material", y="Mass", color="Connection_type").properties(height=700)
    #chart_CO2 = alt.Chart(nc).mark_bar().encode(x="Material", y="Embodied_CO2", color="Connection_type").properties(height=700)

    chart_vol_test = alt.Chart(df).mark_bar().encode(x='Material', y="Volume", color="Connection_type").properties(height=700)
    # st.altair_chart(chart_vol_test, use_container_width=True)

    st.header("Volumes of contruction materials (m³):")
    st.altair_chart(chart_vol, use_container_width=True)
    st.header("Mass of construction materials (kg):")
    st.altair_chart(chart_mass, use_container_width=True)
    st.header("Embodied CO₂ of construction materials (kgCO₂):")
    st.altair_chart(chart_CO2, use_container_width=True)   

    #st.write("Special thanks go to Dr. Kosek for healing the pain - respect!")
    #st.map(df) 
    
    st.header("All building components contained in your project:")
    draw_configured_aggrid(df)  

uploaded_file = st.sidebar.file_uploader("Choose a file", type="ifc", key="uploaded_file", on_change=callback_upload)
if uploaded_file:
    # Read the contents of the uploaded file
    file_contents = uploaded_file.read()
    # Encode the file contents as base64
    base64_file_contents = base64.b64encode(file_contents).decode()
    # Create a data URL
    url = f"data:application/octet-stream;base64,{base64_file_contents}"
    # Use data_url wherever you need it
    # Example: passing it to another Streamlit component
    # st.some_component(data_url)
    # Create a hyperlink to download the file
    url = f"data:application/octet-stream;base64,{base64_file_contents}"
    st.session_state["IFC_href_ready"] = True
    st.session_state["url"] = url
    
# don't get why is there the part after and below...
if "is_file_uploaded" in st.session_state and st.session_state["is_file_uploaded"]:
    st.sidebar.success("File is loaded")
    st.sidebar.write ("Your project is ready to be reviewed. Reduce, reuse, recycle, recover. ♺")
    execute()
else:
    st.title("Dung Beetle Deconstruction Grid")
    st.write(
        """Upload your IFC project data to review your deconstruction and material recovery potential. Remember to assign Connection Types to your building components. 
        """
)



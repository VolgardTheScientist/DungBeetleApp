import streamlit as st
import ifcopenshell
import base64
import numpy as np
import pandas as pd
import pkg_resources

session = st.session_state

def callback_upload():
    st.session_state["file_name"] = st.session_state["uploaded_file"].name
    st.session_state["is_file_uploaded"] = True
    st.session_state["array_buffer"] = st.session_state["uploaded_file"].getvalue()
    st.session_state["ifc_file"] = ifcopenshell.file.from_string(st.session_state["uploaded_file"].getvalue().decode("utf-8"))

def get_project_name():
    return st.session_state["ifc_file"].by_type("IfcProject")[0].Name

def change_project_name():
    st.session_state["ifc_file"].by_type("IfcProject")[0].Name = st.session_state["project_name_input"]

@st.cache_data
def load_video(url):
    video = url
    return video

def main():      
    st.set_page_config(
        layout= "wide",
        page_title="Dung Beetle - Re-Use Building Materials",
    )

    # Add App logo
    with open("dung_beetle.jpg", "rb") as image_file:
        IMAGE_BASE64 = base64.b64encode(image_file.read()).decode()

    st.markdown(
        f"""
        <style>
        #beetle {{
            font-size: 10rem;
            line-height: 8rem;
            font-weight: 900;
            text-transform: uppercase;
            background-image: url(data:image/jpg;base64,{IMAGE_BASE64});
            background-size: auto;
            -webkit-background-clip: text;
            color: transparent;
            position: relative;
            margin-left: -0.75rem;  /* Change this as per your requirement */
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


    # Use st.markdown to create text with a custom class
    st.markdown('<div id="beetle">Dung</br>Beetle</div>', unsafe_allow_html=True)


    # st.image('Dung_Beetle.png')
    st.title("Re-use building material")
    
    # Create columns
    col1, col2 = st.columns(2)  # Create two columns

    col3, col4, col5, col6, col7 = st.columns(5)
    
    with col1:
        st.markdown(
            """
            In the construction industry demolition waste poses a significant problem. It forms the largest waste stream in Switzerland, EU, US, Australia and China, amplifying the urgency for more sustainable approaches to building and demolition. It is this pressing issue that Dung Beetle aims to tackle.

        Welcome to Dung Beetle, a web application developed under the auspices of the **University of Liechtenstein**, that offers an innovative solution for addressing the global waste issue in the construction industry. Spearheaded by Piotr Piotrowski and supervised by Prof. Daniel Stockhammer and Prof. Andreas Putz, Dung Beetle leverages Building Information Modelling (BIM) to promote a shift from a linear to a circular economy.

        This tool allows architects to utilize BIM technology to analyze their designs, helping to assess the deconstruction potential and the end-of-life impact of their buildings. Dung Beetle also provides access to IFC models of parts for potential reuse, integrating them seamlessly into the planning process and easing the search for reusable components.

        By transitioning from the conventional 'take, make, dispose' model to the more sustainable 'make, use, recycle, re-use' approach, Dung Beetle is a valuable aid for architects and builders seeking to reduce the environmental impact of their projects. Join us in using Dung Beetle to tackle the demolition waste problem and contribute to building a more sustainable future.

        If you're an architect, builder, or involved in a construction project that might be intended for demolition in the coming decade, your contribution can be crucial to our research. Whether your project was planned using ArchiCAD or you have available IFC data, we are interested.

        Help us discover your project's reuse potential and contribute to a more sustainable construction industry. Please contact us at **piotr.piotrowski@uni.li** to participate or for further details. Your involvement can make a significant difference in addressing the construction waste problem.


        """
        )



    with col2:
        video = load_video('https://storage.googleapis.com/dungbeetle_media/DungBeetleIntro.mp4')
        st.video(video)
    

    with st.container():        
        with col3:
            st.image("https://storage.googleapis.com/dungbeetle_media/IFCjs.png", width=100)
            st.write("IFCjs BIM Toolkit for JavaScript")
        with col4:
            st.image("https://storage.googleapis.com/dungbeetle_media/IfcOpenShell.png", width=100)
            st.write("IfcOpenShell IFC toolkit and geometry engine")
        with col5:
            st.image("https://storage.googleapis.com/dungbeetle_media/python_BW.png", width=100)
            st.write("Python Programming Language")
        with col6:
            st.image("https://storage.googleapis.com/dungbeetle_media/streamlit.png", width=100)
            st.write("Streamlit app framework")
        with col7:
            st.image("https://storage.googleapis.com/dungbeetle_media/JavaScript.png", width=100)
            st.write("JavaScript Programming Language")
    st.subheader("Dung Beetle© is powered by Open Source")

    with st.expander("See environment details"):
        ifcPenShellVersion = pkg_resources.get_distribution("ifcopenshell").version
        agGridVersion = pkg_resources.get_distribution("streamlit-aggrid").version
        st.write("Pandas: ", pd.__version__)
        st.write("Streamlit: ", st.__version__)
        st.write("Numpy: ", np.__version__)
        st.write("IfcOpenShell: ", ifcPenShellVersion)
        st.write("AGgrid: ", agGridVersion)


    #uploaded_file = st.sidebar.file_uploader("Choose a file", type="ifc", key="uploaded_file", on_change=callback_upload)
#
    #if uploaded_file:
    #    # Read the contents of the uploaded file
    #    file_contents = uploaded_file.read()
#
    #    # Encode the file contents as base64
    #    base64_file_contents = base64.b64encode(file_contents).decode()
#
    #    # Create a data URL
    #    url = f"data:application/octet-stream;base64,{base64_file_contents}"
#
    #    # Use data_url wherever you need it
    #    # Example: passing it to another Streamlit component
    #    # st.some_component(data_url)
#
    #    # Create a hyperlink to download the file
    #    url = f"data:application/octet-stream;base64,{base64_file_contents}"
    #    st.session_state["IFC_href_ready"] = True
    #    st.session_state["url"] = url
    #    
#
#
    ## don't get why is there the part after and below...
#
    #if "is_file_uploaded" in st.session_state and st.session_state["is_file_uploaded"]:
#
    #    st.sidebar.success("File is loaded")
    #    st.sidebar.write ("Your project is ready to be reviewed. Reduce, reuse, recycle, recover. ♺")
            

    # "Check session state", st.session_state

if __name__ == "__main__":
    main()
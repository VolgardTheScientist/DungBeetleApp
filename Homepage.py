import streamlit as st
import ifcopenshell

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

def main():      
    st.set_page_config(
        layout= "wide",
        page_title="IFC Stream",
        page_icon="✍️",
    )
    st.image('Dung_Beetle.png')
    st.title("Re-use building material")
    st.title("TESTING NEW BUILD")
    st.markdown(
        """
        Transition from linear (take, make, dispose) towards circular economy (make, use, recycle) is a fundamental prerequisite for achieving a sustainable growth and limiting global warming.
    Digitalization and management of material flows play a central role in the circular economy. Construction and demolition waste is particularly important, as it is the largest waste stream in many developed countries,
    e.g. in the EU, USA, Australia, China and Switzerland. In the world of digital transformation, a BIM model is a digital representation of a physical asset. Such virtual material banks hold enormous potential for
    innovation in sustainable design, (de-)construction, finance and investment related to the built environment.
    Dung Beetle is a research project exploring possibilities of using BIM models to analyse deconstruction potential of buildings and to use BIM data as a basis for digital material banks. 

    Would you like to find out more or find out how much re-use potential does your own building project have? Get in touch with us: piotr.piotrowski[at]uni.li, or just go ahead and upload your IFC4 MVD: Reference View file 
    and check the results. 
    """)

    st.markdown(
        """
        ### Click on Browse file to begin (only IFC 4 Reference View files)
        """
    )
    uploaded_file = st.sidebar.file_uploader("Choose a file", type="ifc", key="uploaded_file", on_change=callback_upload)

    # don't get why is there the part after and below...

    if "is_file_uploaded" in st.session_state and st.session_state["is_file_uploaded"]:
        st.sidebar.success("File is loaded")
        st.sidebar.write ("Your project is ready to be reviewed. Reduce, reuse, recycle, recover. ♺")

        col1, col2 = st.columns(2)
        with col1:
            st.write(get_project_name())
        with col2: 
            st.sidebar.text_input("✏️ Change project name below", key = "project_name_input", on_change=change_project_name)
            st.sidebar.button("Apply",  key = "project_name_apply", on_click=change_project_name)
            

    "Check session state", st.session_state

if __name__ == "__main__":
    main()
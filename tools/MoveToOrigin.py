import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util
import ifcopenshell.util.placement 
import ifcopenshell.api



def move_to_origin(ifc_file, guid):
    part = ifc_file.by_guid(guid)
    old_matrix = ifcopenshell.util.placement.get_local_placement(part.ObjectPlacement)
    # DEBUG: st.write(old_matrix)
    new_matrix = np.eye(4)
    # DEBUG: st.write(new_matrix)
    ifcopenshell.api.run("geometry.edit_object_placement", ifc_file, product=part, matrix=new_matrix)

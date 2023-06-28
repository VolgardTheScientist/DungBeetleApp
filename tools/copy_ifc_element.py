import ifcopenshell
import uuid

def copy_ifc_element(ifc_file, element_guid):
    # Find the original element
    original_element = ifc_file.by_guid(element_guid)

    # Create a new element with the same type as the original element
    new_element = ifc_file.createIfcCopy(original_element, include_inverse=False)
    
    # Assign a new GlobalId to the new element
    new_element.GlobalId = ifcopenshell.guid.compress(uuid.uuid1().hex)

    # Copy all Psets and Qsets from the original element to the new element
    for rel_defines in ifc_file.get_inverse(original_element):
        if rel_defines.is_a("IfcRelDefinesByProperties"):
            # Create a new IfcRelDefinesByProperties instance for the new element
            new_rel_defines = ifc_file.createIfcCopy(rel_defines, include_inverse=False)
            new_rel_defines.RelatedObjects = (new_element,)

            # Copy properties
            for prop_set in rel_defines.RelatingPropertyDefinition.PropertySetDefinitions:
                if prop_set.is_a("IfcPropertySet") or prop_set.is_a("IfcElementQuantity"):
                    # Create a copy of the property set or element quantity
                    new_prop_set = ifc_file.createIfcCopy(prop_set, include_inverse=False)
                    
                    # Add the new property set or element quantity to the new IfcRelDefinesByProperties instance
                    new_rel_defines.RelatingPropertyDefinition.PropertySetDefinitions.append(new_prop_set)

    return new_element

ifc_file_path = "your_ifc_file.ifc"
element_guid_to_copy = "your_element_guid"

# Read the IFC file
ifc_file = ifcopenshell.open(ifc_file_path)

# Copy the element
new_element = copy_ifc_element(ifc_file, element_guid_to_copy)

# Save the modified IFC file
new_ifc_file_path = "modified_ifc_file.ifc"
ifc_file.write(new_ifc_file_path)

print(f"New element '{new_element.GlobalId}' has been created.")

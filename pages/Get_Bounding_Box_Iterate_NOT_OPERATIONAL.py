import streamlit as st
import ifcopenshell
import ifcopenshell.geom as geom
import numpy as np
import tempfile
import pandas as pd





# Include the geometry processing functions you provided above

settings = ifcopenshell.geom.settings() 

tol = 1e-6


def is_x(value, x):
    return abs(x - value) < tol


def get_volume(geometry):
    def signed_triangle_volume(p1, p2, p3):
        v321 = p3[0] * p2[1] * p1[2]
        v231 = p2[0] * p3[1] * p1[2]
        v312 = p3[0] * p1[1] * p2[2]
        v132 = p1[0] * p3[1] * p2[2]
        v213 = p2[0] * p1[1] * p3[2]
        v123 = p1[0] * p2[1] * p3[2]
        return (1.0 / 6.0) * (-v321 + v231 + v312 - v132 - v213 + v123)

    verts = geometry.verts
    faces = geometry.faces
    grouped_verts = [[verts[i], verts[i + 1], verts[i + 2]] for i in range(0, len(verts), 3)]
    volumes = [
        signed_triangle_volume(grouped_verts[faces[i]], grouped_verts[faces[i + 1]], grouped_verts[faces[i + 2]])
        for i in range(0, len(faces), 3)
    ]
    return abs(sum(volumes))


def get_x(geometry):
    x_values = [geometry.verts[i] for i in range(0, len(geometry.verts), 3)]
    return max(x_values) - min(x_values)


def get_y(geometry):
    y_values = [geometry.verts[i + 1] for i in range(0, len(geometry.verts), 3)]
    return max(y_values) - min(y_values)


def get_z(geometry):
    z_values = [geometry.verts[i + 2] for i in range(0, len(geometry.verts), 3)]
    return max(z_values) - min(z_values)


def get_area_vf(vertices, faces):
    # Calculate the triangle normal vectors
    v1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    v2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    triangle_normals = np.cross(v1, v2)

    # Normalize the normal vectors to get their length (i.e., triangle area)
    triangle_areas = np.linalg.norm(triangle_normals, axis=1) / 2

    # Sum up the areas to get the total area of the mesh
    mesh_area = np.sum(triangle_areas)

    return mesh_area


def get_area(geometry):
    verts = geometry.verts
    faces = geometry.faces
    vertices = np.array([[verts[i], verts[i + 1], verts[i + 2]] for i in range(0, len(verts), 3)])
    faces = np.array([[faces[i], faces[i + 1], faces[i + 2]] for i in range(0, len(faces), 3)])
    return get_area_vf(vertices, faces)


def get_side_area(geometry):
    verts = geometry.verts
    faces = geometry.faces
    vertices = np.array([[verts[i], verts[i + 1], verts[i + 2]] for i in range(0, len(verts), 3)])
    faces = np.array([[faces[i], faces[i + 1], faces[i + 2]] for i in range(0, len(faces), 3)])

    # Calculate the triangle normal vectors
    v1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    v2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    triangle_normals = np.cross(v1, v2)

    # Normalize the normal vectors
    triangle_normals = triangle_normals / np.linalg.norm(triangle_normals, axis=1)[:, np.newaxis]

    # Find the faces with a normal vector pointing in the desired +Y normal direction
    filtered_face_indices = np.where(triangle_normals[:, 1] > tol)[0]
    filtered_faces = faces[filtered_face_indices]
    return get_area_vf(vertices, filtered_faces)


def get_footprint_area(geometry):
    verts = geometry.verts
    faces = geometry.faces
    vertices = np.array([[verts[i], verts[i + 1], verts[i + 2]] for i in range(0, len(verts), 3)])
    faces = np.array([[faces[i], faces[i + 1], faces[i + 2]] for i in range(0, len(faces), 3)])

    # Calculate the triangle normal vectors
    v1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    v2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    triangle_normals = np.cross(v1, v2)

    # Normalize the normal vectors
    triangle_normals = triangle_normals / np.linalg.norm(triangle_normals, axis=1)[:, np.newaxis]

    # Find the faces with a normal vector pointing in the desired +Z normal direction
    filtered_face_indices = np.where(triangle_normals[:, 2] > tol)[0]
    filtered_faces = faces[filtered_face_indices]
    return get_area_vf(vertices, filtered_faces)


def get_outer_surface_area(geometry):
    verts = geometry.verts
    faces = geometry.faces
    vertices = np.array([[verts[i], verts[i + 1], verts[i + 2]] for i in range(0, len(verts), 3)])
    faces = np.array([[faces[i], faces[i + 1], faces[i + 2]] for i in range(0, len(faces), 3)])

    # Calculate the triangle normal vectors
    v1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    v2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    triangle_normals = np.cross(v1, v2)

    # Normalize the normal vectors
    triangle_normals = triangle_normals / np.linalg.norm(triangle_normals, axis=1)[:, np.newaxis]

    # Find the faces with a normal vector that isn't +Z or -Z
    filtered_face_indices = np.where(abs(triangle_normals[:, 2]) < tol)[0]
    filtered_faces = faces[filtered_face_indices]
    return get_area_vf(vertices, filtered_faces)


def get_footprint_perimeter(geometry):
    verts = geometry.verts
    faces = geometry.faces
    vertices = np.array([[verts[i], verts[i + 1], verts[i + 2]] for i in range(0, len(verts), 3)])
    faces = np.array([[faces[i], faces[i + 1], faces[i + 2]] for i in range(0, len(faces), 3)])

    # Calculate the triangle normal vectors
    v1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
    v2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
    triangle_normals = np.cross(v1, v2)

    # Normalize the normal vectors
    triangle_normals = triangle_normals / np.linalg.norm(triangle_normals, axis=1)[:, np.newaxis]

    # Find the faces with a normal vector pointing in the negative Z direction
    negative_z_face_indices = np.where(triangle_normals[:, 2] < -tol)[0]
    negative_z_faces = faces[negative_z_face_indices]

    # Initialize the set of counted edges and the perimeter
    all_edges = set()
    shared_edges = set()
    perimeter = 0

    # Loop through each face
    for face in negative_z_faces:
        # Loop through each edge of the face
        for i in range(3):
            # Get the indices of the two vertices that define the edge
            edge = (face[i], face[(i + 1) % 3])
            # Keep track of shared edges. Perimeter edges are unshared.
            if (edge[1], edge[0]) in all_edges or (edge[0], edge[1]) in all_edges:
                shared_edges.add((edge[0], edge[1]))
                shared_edges.add((edge[1], edge[0]))
            else:
                all_edges.add(edge)

    return sum([np.linalg.norm(vertices[e[0]] - vertices[e[1]]) for e in (all_edges - shared_edges)])

# Streamlit App
def process_ifc_element(ifc_entity, geometry):
    try:
        x_dim = get_x(geometry)  # Implement your own get_x, get_y, get_z
        y_dim = get_y(geometry)
        z_dim = get_z(geometry)

        return {
            "GlobalId": ifc_entity.GlobalId,
            "Type": ifc_entity.is_a(),
            "X": x_dim,
            "Y": y_dim,
            "Z": z_dim
        }
    except Exception as e:
        st.warning(f"Failed to process {ifc_entity.GlobalId} due to {str(e)}")
        return None

def main():
    st.title("IFC File Processor")

    # Load your IFC file
    uploaded_file = st.file_uploader("Upload an IFC file", type=["ifc"])
    if uploaded_file:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        ifc_file = ifcopenshell.open(tfile.name)

        settings = ifcopenshell.geom.settings()

        # Initialize the iterator
        iterator = ifcopenshell.geom.iterate(settings, ifc_file)

        for shape in iterator:
            st.write("Inspecting shape object:")
            for attribute in dir(shape):
                if not attribute.startswith("__"):
                    st.write(f"{attribute}: {getattr(shape, attribute)}")

            ifc_entity = shape.product  # This seems to be the IfcProduct (e.g., IfcWall, IfcSlab)
            geometry = shape.geometry  # This seems to be the geometry

            st.write(f"Processing IFC Entity: {ifc_entity.is_a()}, GlobalId: {ifc_entity.GlobalId}")

            # Access vertices and faces
            vertices = geometry.verts
            faces = geometry.faces

            st.write(f"Vertices: {vertices}")
            st.write(f"Faces: {faces}")

            processed_data = process_ifc_element(ifc_entity, geometry)

            if processed_data:
                st.write("Processed Data:", processed_data)

if __name__ == "__main__":
    main()
import os
import streamlit as st
from google.cloud import storage  # import the storage client

# point to the key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), 'able-analyst-392315-56e86dad6fde.json')

# Function to upload a file to Google Cloud Storage

def upload_to_gcs(bucket_name, source_file_content, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # Delete any existing .txt files
    blobs = bucket.list_blobs()
    for blob in blobs:
        if blob.name.endswith('.txt') and blob.name != file_name:
            blob.delete()

    # Create a blob for the new file
    blob = bucket.blob(file_name)
    
    blob.upload_from_string(source_file_content)
    
    # Make the blob publicly viewable
    blob.make_public()

    public_url = blob.public_url

    return public_url


# Get input from user
input_text = st.text_input('Enter some text')

# Button to start upload process
if st.button('Cloud'):
    if len(input_text) < 5:
        st.write('Please enter at least 5 characters.')
    else:
        # Create a text file content from the textbox input
        file_content = input_text
        
        # Get the first 5 characters of the input as the file name
        file_name = input_text[:5] + '.txt'

        # Name of your Google Cloud Storage bucket
        bucket_name = 'streamlit_warehouse'
        
        # Upload the file content to Google Cloud Storage
        gcs_url = upload_to_gcs(bucket_name, file_content, file_name)
        
        # Display the URL of the uploaded file
        st.write(f'Uploaded file can be accessed at: {gcs_url}')

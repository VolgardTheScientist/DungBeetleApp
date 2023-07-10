from google.cloud import storage
import os

# point to the key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.path.dirname(__file__), 'able-analyst-392315-363ff32d54d8.json')

def set_bucket_cors(bucket_name):
    """Set CORS policy on the bucket"""
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    bucket.reload()

    bucket.cors = [
        {
            "origin": ["*"],
            "responseHeader": ["Content-Type"],
            "method": ["GET"],
            "maxAgeSeconds": 3600
        }
    ]

    bucket.patch()

    print("Set CORS policies for bucket {} to:".format(bucket.name))
    print(bucket.cors)

set_bucket_cors('streamlit_warehouse')

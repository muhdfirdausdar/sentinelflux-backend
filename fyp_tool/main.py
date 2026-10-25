import json
import os
from utils import fetch_data

def setup(id: int, query_id: int = 1):
    # Setup fetching data from the server# Example ID to fetch data like domain id = 1 in database

    # 1,2,3
    query=[
        f"domain?id={id}", # Query for basic domain info
        f"domain/details?id={id}", # Query for detailed domain info
        "db_status", # Query for server status
        "sf_metadata", # Query for server metadata
    ]

    # Define the API URL and API key
    base_url = os.environ["SENTINELFLUX_API_URL"].rstrip("/")
    api_url = f"{base_url}/{query[query_id-1]}"

    try:
        # Fetch data using the utility function
        data = fetch_data(api_url)
        return data

    except Exception as e:
        print(f"Error: {e}")

def main():
    response = setup(id=266, query_id=3)  
    # Process the response as needed
    # For example, you can print the response or save it to a file
    # or perform any other operations you need
    print(json.dumps(response, indent=4))

if __name__ == "__main__":
    main()
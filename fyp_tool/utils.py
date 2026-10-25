import os
import requests


## Please dont share the API key publicly
# API key for authentication
# Dont modifying this key in the code and dont upload or share it to anyone or anywhere

def fetch_data(api_url: str):
    """
    Fetch data from the server using the provided API URL and API key.

    Args:
        api_url (str): The API endpoint URL.
        params (dict, optional): Query parameters to include in the request.

    Returns:
        dict: The JSON response from the server.

    Raises:
        Exception: If the request fails or the server returns an error.
    """
    headers = {
        "X-API-Key": os.environ["SENTINELFLUX_API_KEY"],
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching data: {e}")
from locust import HttpUser, task, between
from dotenv import load_dotenv
import os
import random

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("API_KEY")

MIN_DOMAIN_ID = 1  # Set your minimum domain_id
MAX_DOMAIN_ID = 10000  # Set your maximum domain_id


class FastAPITestUser(HttpUser):
    wait_time = between(1, 5)  # Wait between 1 to 5 seconds between tasks
    api_key = API_KEY

    @task
    def get_domain(self):
        domain_id = random.randint(MIN_DOMAIN_ID, MAX_DOMAIN_ID)
        headers = {
            "accept": "application/json",
            "X-API-Key": self.api_key  # Add the API key header
        }
        self.client.get(f"/domain/details?id={domain_id}", headers=headers)
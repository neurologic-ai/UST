# from locust import HttpUser, task, between
# import datetime

# class RecommendationUser(HttpUser):
#     wait_time = between(1, 2)  # Wait 1–2 seconds between tasks

#     @task
#     def post_recommendation(self):
#         url = "/api/v2/recommendation"
#         headers = {
#             "accept": "application/json",
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "cartItems": [],
#             "topN": 4,
#             "currentHour": datetime.datetime.utcnow().hour,
#             "currentDateTime": datetime.datetime.utcnow().isoformat() + "Z",
#             "tenantId": "682db13b29b7dee813deffc6",
#             "locationId": "location_1",
#             "storeId": "store_2",
#             "latitude": 19.4326,
#             "longitude": 99.1332
#         }

#         self.client.post(
#             url,
#             headers=headers,
#             params={"api_key": "FTTjar1GWbRt5T4yeo_LwhEsMbsZQa0WW2DzzMmCDwE"},
#             json=payload
#         )

from locust import HttpUser, task, between
import datetime

class RecommendationUser(HttpUser):
    wait_time = between(1, 2)  # Wait between 1 and 2 seconds

    @task
    def post_recommendation(self):
        url = "/api/v2/recommendation"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
            "cartItems": [],
            "topN": 4,
            "currentHour": datetime.datetime.utcnow().hour,
            "currentDateTime": datetime.datetime.utcnow().isoformat() + "Z",
            "tenantId": "682db13b29b7dee813deffc6",
            "locationId": "location_1",
            "storeId": "store_2",
            "latitude": 19.4326,
            "longitude": 99.1332
        }

        self.client.post(
            url,
            headers=headers,
            params={"api_key": "FTTjar1GWbRt5T4yeo_LwhEsMbsZQa0WW2DzzMmCDwE"},
            json=payload
        )

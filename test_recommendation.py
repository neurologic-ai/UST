import json
import asyncio
from molotov import scenario

# ✅ Scenario 1 — your actual API
@scenario(weight=1)
async def test_actual_api(session):
    # print("🚀 Running actual recommendation API test")

    url = "https://api.repls.dmo.fcust.com/api/v2/recommendation?api_key=FTTjar1GWbRt5T4yeo_LwhEsMbsZQa0WW2DzzMmCDwE"

    payload = {
        "cartItems": [],
        "topN": 4,
        "currentHour": 16,
        "currentDateTime": "2025-06-30T17:39:37.266Z",
        "tenantId": "682db13b29b7dee813deffc6",
        "locationId": "location_1",
        "storeId": "store_2",
        "latitude": 19.4326,
        "longitude": 99.1332
    }

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        async with session.post(url, json=payload, headers=headers) as resp:
            status = resp.status
            # print(f"✅ Received response with status: {status}")
            if status != 200:
                body = await resp.text()
                print(f"❌ Unexpected response body: {body}")
    except Exception as e:
        print(f"🔥 Exception occurred: {e}")

    await asyncio.sleep(0.5)

# ✅ Scenario 2 — fallback test to check setup
@scenario(weight=0)
async def test_httpbin(session):
    print("🌐 Testing fallback to httpbin.org")
    try:
        async with session.get("https://httpbin.org/get") as resp:
            print("✅ httpbin GET response:", resp.status)
    except Exception as e:
        print("❌ Failed to call httpbin:", e)

    await asyncio.sleep(0.5)

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from twilio.rest import Client
from dotenv import load_dotenv
import json
import os
import datetime

load_dotenv()
app = FastAPI()

@app.get("/")
async def root():
    return RedirectResponse(url="/demo")

# Fallback SMS Adapter as per issues.md logic
try:
    twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
except Exception as e:
    print("Warning: Twilio client initialization failed. Falling back to print logs.")
    twilio_client = None

def send_sms(to_number, message):
    if twilio_client:
        try:
            twilio_client.messages.create(
                body=message,
                from_=os.getenv("TWILIO_FROM_NUMBER"),
                to=to_number
            )
            return "sent"
        except Exception as e:
            print(f"Twilio API Error: {e}")
            print(f"Simulated SMS to {to_number}: {message}")
            return "simulated"
    else:
        print(f"Simulated SMS to {to_number}: {message}")
        return "simulated"

MATCH_THRESHOLD = 70

def match_score(buyer: dict, listing: dict) -> int:
    score = 0
    # City match (40 points)
    if buyer["city"].lower() == listing["city"].lower():
        score += 40
    # Budget (30 points)
    if listing["price"] <= buyer["budget_max"]:
        score += 30
    elif listing["price"] <= buyer["budget_max"] * 1.1:
        score += 15
    # Bedrooms (20 points)
    if listing["beds"] >= buyer["beds_min"]:
        score += 20
    elif listing["beds"] == buyer["beds_min"] - 1:
        score += 10
    # Property type (10 points)
    if buyer["type"].lower() == listing["type"].lower():
        score += 10
    return score

@app.post("/new-listing")
async def new_listing(listing: dict):
    # Load buyers
    with open("buyers.json") as f:
        buyers = json.load(f)

    fired = []
    for buyer in buyers:
        score = match_score(buyer, listing)
        print(f"{buyer['name']}: score {score}")
        if score >= MATCH_THRESHOLD:
            msg = (
                f"🏠 SnapAlert: New match in {listing['city']}!\n"
                f"{listing['address']} — ${listing['price']:,}\n"
                f"{listing['beds']} beds · {listing['type']}\n"
                f"Match: {score}/100\n"
                f"View: https://snaphomz.com/listing/{listing['id']}"
            )
            status = send_sms(buyer["phone"], msg)
            fired.append({"buyer": buyer["name"], "score": score, "status": status})

    # Log to alerts.json
    log_entry = {
        "timestamp": str(datetime.datetime.now()),
        "listing": listing,
        "alerts_fired": fired
    }
    try:
        with open("alerts.json", "r") as f:
            logs = json.load(f)
    except FileNotFoundError:
        logs = []
    logs.append(log_entry)
    with open("alerts.json", "w") as f:
        json.dump(logs, f, indent=2)

    return JSONResponse({"matched": len(fired), "alerts": fired})

@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    return """
    <html>
    <head><title>SnapAlert Demo</title></head>
    <body style="font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 20px;">
        <h2>🏠 SnapAlert – New Listing Simulator</h2>
        <p>Click the button below to simulate a new property hitting the market. Matched buyers will receive an SMS in seconds.</p>
        <button id="fireBtn" style="background:#4F46E5; color:white; padding:12px 24px; font-size:16px; border:none; border-radius:8px; cursor:pointer;">
            🚀 New Listing Just Hit the Market
        </button>
        <pre id="result" style="margin-top:20px; background:#f4f4f4; padding:16px; border-radius:8px;"></pre>
        <script>
            const listing = {
                id: "L999",
                address: "123 Oak Street, Pasadena, CA",
                city: "Pasadena",
                price: 649000,
                beds: 3,
                type: "single-family"
            };
            document.getElementById("fireBtn").onclick = async () => {
                const res = await fetch("/new-listing", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify(listing)
                });
                const data = await res.json();
                document.getElementById("result").textContent = JSON.stringify(data, null, 2);
            };
        </script>
    </body>
    </html>
    """

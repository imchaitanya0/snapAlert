# SnapAlert: Hyper-Personalised Deal Alert Engine

## Overview
**Problem:** Good homes in competitive California markets go under contract in 48-72 hours. Buyers checking portals daily miss deals because email alerts have a 20% open rate and are often ignored. The window between 'listed' and 'offer accepted' is too short for passive search.
**Solution:** SnapAlert is a real-time matching engine that compares incoming property listings against a buyer's stored preference vector. When a listing exceeds the match threshold, it instantly fires an SMS to the buyer with a one-tap link to schedule a showing, ensuring zero-latency "speed to lead."

---

## System Architecture

Our MVP architecture is designed for speed, decoupling the heavy lifting from the final SMS delivery to ensure that the application never crashes under load or third-party API restrictions.

1. **Incoming Data Layer:** A RESTful `POST /new-listing` endpoint built with **FastAPI**. In production, this receives webhooks directly from MLS providers (like RealEstateAPI.com).
2. **Matching Engine:** A synchronous Python evaluator that loops through buyer preference vectors loaded from local storage (`buyers.json`) and calculates a weighted score out of 100 based on City, Budget, Bedrooms, and Property Type.
3. **Communication Layer (Adapter Pattern):** An abstracted SMS dispatcher. It attempts to connect to the **Twilio API** for real-world SMS delivery.
4. **Audit & Logging:** Every processed listing and its resulting alerts are logged sequentially to `alerts.json` (acting as our NoSQL document store) to maintain a complete audit trail.

---

## Technical Trade-offs & Scope Management

Building a production-ready application in 60 minutes requires ruthless scope management. Senior engineering isn't just about what you build; it's about what you intentionally choose *not* to build. 

Here are the strategic trade-offs we made for this MVP:

### 1. SMS Delivery: Graceful Degradation over Hard Failures
**What we skipped:** Blocking the entire matching pipeline if Twilio 10DLC (10-Digit Long Code) verification fails or if a trial account restricts messaging to unverified numbers.
**What we used instead:** We built a **Fallback SMS Adapter**. 
**Why:** Twilio's A2P 10DLC registration takes days to process, making it hostile for rapid hackathons. If Twilio throws a `400 Bad Request` (e.g., trying to send to an unverified number), our adapter catches the exception, gracefully degrades to a simulated terminal log, and returns a "simulated" status. This ensures that a failure at the final carrier level never crashes the core matching engine. The SMS provider is treated strictly as a configurable plug-in.

### 2. Data Ingestion: Manual Trigger over Live Webhooks
**What we skipped:** Integrating a live, authenticated MLS webhook feed.
**What we used instead:** An HTML/JS Simulator UI (`/demo`) that POSTs an identical JSON payload to our endpoint.
**Why:** Gaining access to a live MLS feed requires vendor approval and thousands of dollars in access fees. Our simulator creates the exact same JSON payload that a vendor webhook would send. The backend endpoint logic remains 100% identical to what would be deployed in production.

### 3. State Management: JSON over PostgreSQL/Redis
**What we skipped:** Standing up PostgreSQL for buyer profiles and Redis for webhook deduplication.
**What we used instead:** Local JSON files (`buyers.json`, `alerts.json`) acting as our document store.
**Why:** Infrastructure setup (ORM schemas, Docker containers) would consume 40% of the allocated time without proving the core business value. Reading from a JSON file allows us to instantly prove the **weighted scoring algorithm**. In production, swapping `json.load()` for a `psycopg2` or `SQLAlchemy` query is a trivial implementation detail. 
*Note on Redis:* In production, Redis deduplication is critical to prevent spamming users if the MLS accidentally sends duplicate webhooks. For a 1-hour isolated demo, duplicate webhooks are impossible, making Redis a premature optimization.

### 4. Matching Logic: Weighted Heuristics over Vector Embeddings (pgvector)
**What we skipped:** Cosine similarity matching using LLMs and `pgvector`.
**What we used instead:** A deterministic, weighted scoring algorithm (City=40%, Budget=30%, Beds=20%, Type=10%).
**Why:** LLM embeddings are powerful but act as a "black box" and introduce high latency. A buyer wants to know *exactly* why they received a text. Our deterministic algorithm is transparent, executes in microseconds, and sets a strict 70/100 threshold, guaranteeing that buyers only receive high-intent, highly qualified matches.

---

## Business Impact & Revenue Model

SnapAlert doesn't just improve UX; it fundamentally shifts unit economics:
1. **Higher Conversion:** Zillow sends emails (20% open rate). SnapAlert sends SMS (98% open rate within 5 minutes).
2. **Zero CAC Leads:** Instead of buying expensive leads, SnapAlert creates daily active users out of passive buyers.
3. **Direct Revenue:** Every SMS that leads to a booked showing is a Snaphomz-attributed transaction, directly feeding the referral commission model.

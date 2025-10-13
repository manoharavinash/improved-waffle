from flask import Flask, request
from flask_cors import CORS     # << add this
import requests, base64

app = Flask(__name__)
CORS(app)                       # << add this (allows all origins)
# Telegram Bot Details (Manohar Avinash)
BOT_TOKEN = "7832396483:AAEaLj3K5SUWY6LX6MoborA0j04jctG96XU"
CHAT_ID = "7110818193"

@app.route('/')
def home():
    return "✅ Telegram Location & Photo Server Running Successfully!"

@app.route('/send_data', methods=['POST'])
def send_data():
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    photo_data = data.get('photo')

    # Send location message
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": CHAT_ID,
        "text": f"📍 New Emergency Alert:\nhttps://www.google.com/maps?q={lat},{lon}"
    })

    # Send photo
    if photo_data:
        photo_bytes = base64.b64decode(photo_data.split(',')[1])
        files = {'photo': ('photo.jpg', photo_bytes, 'image/jpeg')}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": CHAT_ID}, files=files)

    return "✅ Sent to Telegram", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Загружаем переменные из .env при локальном запуске
load_dotenv()

app = Flask(__name__)

# --- НАСТРОЙКИ API ИЗ ОКРУЖЕНИЯ ---
CRM_BASE_URL = os.getenv("CRM_BASE_URL", "https://avtomag.autocrm.ru/yii/api")
AUTH_HEADER = os.getenv("AUTH_HEADER")

# --- БИЗНЕС-НАСТРОЙКИ (Хардкод) ---
SALON_ID = 1  # ID вашего автосалона

HEADERS = {
    "Authorization": AUTH_HEADER,
    "Content-Type": "application/json"
}

@app.route('/', methods=['GET'])
def health_check():
    return "Webhook server is running!", 200

@app.route('/tilda-webhook', methods=['POST'])
def tilda_webhook():
    if not AUTH_HEADER:
        return jsonify({"error": "Server configuration error: Missing AUTH_HEADER"}), 500

    if request.is_json:
        tilda_data = request.get_json()
    else:
        tilda_data = request.form.to_dict()

    if not tilda_data:
        return jsonify({"error": "No data received"}), 400

    crm_payload = {
        "salon_id": SALON_ID,
        "type": 11,
        "request_type_id": 1,
        "first_name": tilda_data.get('Name', 'Не указано (Тильда)'),
        "phone": tilda_data.get('Phone', ''),
        "email": tilda_data.get('Email', ''),
        "comment": f"Заявка с сайта. Форма: {tilda_data.get('formname', 'Неизвестная форма')}",
        "utm_source": tilda_data.get('utm_source', ''),
        "utm_medium": tilda_data.get('utm_medium', ''),
        "utm_campaign": tilda_data.get('utm_campaign', '')
    }

    try:
        response = requests.post(
            f"{CRM_BASE_URL}/leads/request",
            headers=HEADERS,
            data=json.dumps(crm_payload)
        )
        
        result = response.json()
        
        if response.status_code == 200 and result.get('status') == 0:
            return jsonify({"status": "success", "message": "Lead created"}), 200
        else:
            return jsonify({"error": "CRM API Error", "details": result}), 400

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
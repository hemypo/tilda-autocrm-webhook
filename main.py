import os
import re
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ==========================================
# НАСТРОЙКИ
# ==========================================
CRM_BASE_URL = os.getenv("CRM_BASE_URL", "").strip()
API_KEY = os.getenv("API_KEY", "").strip()

SALON_ID = 1
TYPE = 11
REQUEST_TYPE_ID = 1
SOURCE_ID = 1

# Обновленный словарь актуальных моделей
CARS_DICTIONARY = {
    # Основные модели
    "HAVAL F7": {"brand_id": 152, "model_id": 17458},
    "HAVAL F7x": {"brand_id": 152, "model_id": 18528}, 
    "HAVAL JOLION": {"brand_id": 152, "model_id": 19585},
    "ОБНОВЛЕННЫЙ HAVAL JOLION": {"brand_id": 152, "model_id": 19585},
    "HAVAL DARGO": {"brand_id": 152, "model_id": 21427},
    "HAVAL DARGO X": {"brand_id": 152, "model_id": 21427}, # DARGO X падает в общую карточку DARGO
    "HAVAL M6": {"brand_id": 152, "model_id": 22307},    # Пикапы
    "GWM POER": {"brand_id": 152, "model_id": 19584}
}

def get_headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        # Маскируемся под браузер, чтобы обходить файрволы CRM
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

# ==========================================
# ОСНОВНОЙ ВЕБХУК
# ==========================================
@app.route('/tilda-webhook', methods=['POST'])
def tilda_webhook():
    if not API_KEY:
        print("ВНИМАНИЕ: API_KEY пустой! Проверьте переменные окружения в Amvera.")

    data = request.get_json() if request.is_json else request.form.to_dict()
    if not data:
        data = {}

    name = data.get('Имя', 'Без имени')
    raw_phone = data.get('Телефон', '')
    tilda_model = data.get('Модель', '').strip()

    clean_phone = re.sub(r'[^\d+]', '', raw_phone)
    if clean_phone and clean_phone[0] != '+':
        clean_phone = '+' + re.sub(r'\D', '', clean_phone)

    payload = {
        "salon_id": SALON_ID,
        "type": TYPE,
        "request_type_id": REQUEST_TYPE_ID,
        "source_id": SOURCE_ID,
        "first_name": name,
        "phone": clean_phone,
        "consent_processing_personal_information": 1,
        "consent_obtaining_sms_mailing": 1,
        "comment": "Заявка с сайта."
    }

    if tilda_model:
        found_car = CARS_DICTIONARY.get(tilda_model)
        
        if found_car:
            payload["brand_id"] = found_car["brand_id"]
            payload["model_id"] = found_car["model_id"]
            
            # --- Уточнение для DARGO X ---
            if tilda_model.upper() == "HAVAL DARGO X":
                payload["comment"] += "\nУточнение по модели: речь о DARGO X"
        else:
            payload["comment"] += f"\nКлиент выбрал авто: {tilda_model}"

    api_url = f"{CRM_BASE_URL}/leads/request/"
    
    try:
        requests.post(api_url, headers=get_headers(), json=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки в CRM: {e}")

    return "ok", 200

# ==========================================
# СПРАВОЧНИК МОДЕЛЕЙ (Для проверки)
# ==========================================
@app.route('/get-models', methods=['GET'])
def get_haval_models_dictionary():
    if not API_KEY:
        return "Ошибка: API_KEY не задан в переменных окружения на сервере", 500

    url = f"{CRM_BASE_URL}/refModel/"
    
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        
        if response.status_code == 200:
            json_data = response.json()
            if json_data.get('status') == 1 and json_data.get('result'):
                result_lines = ["=== АКТУАЛЬНЫЕ МОДЕЛИ HAVAL (brand_id: 152) ==="]
                for model in json_data['result']:
                    if str(model.get('brand_id')) == "152" and str(model.get('is_deleted')) == "0":
                        line = f'"{model.get("name")}": {{ "brand_id": 152, "model_id": {model.get("id")} }},  // Актуальность: {model.get("is_recent")}'
                        result_lines.append(line)
                
                result_lines.append("===============================================")
                return "\n".join(result_lines), 200, {'Content-Type': 'text/plain; charset=utf-8'}
            else:
                return f"Ошибка API: {json_data.get('errors')}", 400
        else:
            return f"Ошибка сервера CRM. Код: {response.status_code}\nОтвет: {response.text[:200]}", 500
            
    except Exception as e:
        return f"Ошибка выполнения: {str(e)}", 500

# ==========================================
# ОТЛАДОЧНЫЙ ЭНДПОИНТ
# ==========================================
@app.route('/debug-auth', methods=['GET'])
def debug_auth():
    if not API_KEY:
        return jsonify({"error": "API_KEY пустой"}), 400
        
    masked_key = f"{API_KEY[:5]}...{API_KEY[-5:]}" if len(API_KEY) > 10 else "СЛИШКОМ КОРОТКИЙ"
    
    return jsonify({
        "1_key_length": len(API_KEY),
        "2_masked_key": masked_key,
        "3_header_preview": f"Bearer {masked_key}",
        "4_crm_url": CRM_BASE_URL
    }), 200
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)

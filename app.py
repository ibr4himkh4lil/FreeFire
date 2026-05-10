# ------------------------------------------------------------
# Free Fire Account Info API — Credit: @SENKU_CODEX
# JOIN    : @SENKU_CODEX  FOR MORE SRC | API | BOT CODE | METHOD | 🛐
# Purpose : Fetch Free Fire profile details using UID (JWT + AES)
# Note    : THIS CODE MADE BY SENKU_CODEX — KEEP CREDIT
# Endpoint: /info?uid=<PLAYER_UID>&region=<REGION>
# Example : /info?uid=11111111&region=IND
# Regions Supported : IND | BD | PK (Only these 3 servers work)
# License : Personal / internal use only — retain credit when sharing
# ------------------------------------------------------------

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import requests
from flask import Flask, jsonify, request
from data_pb2 import AccountPersonalShowInfo
from google.protobuf.json_format import MessageToDict
import uid_generator_pb2
import threading
import time

app = Flask(__name__)

jwt_tokens = {"IND": None, "BD": None, "PK": None}
jwt_lock = threading.Lock()
updater_started = {"IND": False, "BD": False, "PK": False}

JWT_ENDPOINTS = {
    "IND": "https://raihan-access-to-jwt.vercel.app/token?uid=4344656844&password=RAIHANHACKER01",
    "BD":  "https://raihan-access-to-jwt.vercel.app/token?uid=4363457346&password=SENKU_692491",
    "PK":  "https://raihan-access-to-jwt.vercel.app/token?uid=4363456802&password=SENKU_692458",
}

# ---------------- JWT HANDLING ----------------
def extract_token_from_response(data, region):
    if not isinstance(data, dict):
        return None
    if data.get("success") is True and "token" in data:
        return data["token"]
    if "token" in data:
        return data["token"]
    return None

def get_jwt_token_sync(region):
    if region not in JWT_ENDPOINTS:
        region = "IND"
    url = JWT_ENDPOINTS[region]
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        token = extract_token_from_response(data, region)
        if token:
            jwt_tokens[region] = token
            print(f"[JWT] Token for {region} updated: {token[:30]}...")
            return token
        else:
            print(f"[JWT] No token in response for {region}: {data}")
    except Exception as e:
        print(f"[JWT] Error for {region}: {e}")
    return None

def ensure_jwt_token_sync(region):
    if not jwt_tokens.get(region):
        return get_jwt_token_sync(region)
    return jwt_tokens[region]

def jwt_token_updater(region):
    while True:
        time.sleep(300)
        get_jwt_token_sync(region)

def start_updater_once(region):
    if not updater_started.get(region):
        updater_started[region] = True
        threading.Thread(target=jwt_token_updater, args=(region,), daemon=True).start()

# ✅ CRITICAL FIX: Module level — runs with Gunicorn too
print("[STARTUP] Fetching JWT tokens for all regions...")
for _r in ["IND", "BD", "PK"]:
    get_jwt_token_sync(_r)
    start_updater_once(_r)
print("[STARTUP] Done.")

# ---------------- API ENDPOINTS ----------------
def get_api_endpoint(region):
    endpoints = {
        "IND": "https://client.ind.freefiremobile.com/GetPlayerPersonalShow",
        "BD":  "https://clientbp.ggblueshark.com/GetPlayerPersonalShow",
        "PK":  "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
    }
    return endpoints.get(region, endpoints["IND"])

# ---------------- AES ENCRYPTION ----------------
default_key = "Yg&tc%DEuh6%Zc^8"
default_iv  = "6oyZDr22E3ychjM%"

def encrypt_aes(hex_data, key, iv):
    key = key.encode()[:16]
    iv  = iv.encode()[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(bytes.fromhex(hex_data), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return binascii.hexlify(encrypted_data).decode()

# ---------------- API CALL ----------------
def apis(idd, region):
    token = ensure_jwt_token_sync(region)
    if not token:
        raise Exception(f"Failed to get JWT token for region {region}")

    endpoint = get_api_endpoint(region)
    headers = {
        'User-Agent':     'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
        'Connection':     'Keep-Alive',
        'Expect':         '100-continue',
        'Authorization':  f'Bearer {token}',
        'X-Unity-Version':'2018.4.11f1',
        'X-GA':           'v1 1',
        'ReleaseVersion': 'OB53',
        'Content-Type':   'application/x-www-form-urlencoded',
    }
    try:
        data = bytes.fromhex(idd)
        response = requests.post(endpoint, headers=headers, data=data, timeout=15)
        response.raise_for_status()
        return response.content.hex()
    except requests.exceptions.RequestException as e:
        print(f"[API] Request to {endpoint} failed: {e}")
        raise

# ---------------- FLASK ROUTES ----------------
@app.route('/info', methods=['GET'])
def get_player_info():
    try:
        uid    = request.args.get('uid')
        region = request.args.get('region', 'IND').upper()

        if not uid:
            return jsonify({"error": "UID parameter is required"}), 400

        supported_regions = ["IND", "BD", "PK"]
        if region not in supported_regions:
            return jsonify({
                "error": f"Region '{region}' not supported. Only {', '.join(supported_regions)} are supported."
            }), 400

        start_updater_once(region)

        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena  = 1
        protobuf_data = message.SerializeToString()
        hex_data = binascii.hexlify(protobuf_data).decode()

        encrypted_hex = encrypt_aes(hex_data, default_key, default_iv)

        api_response = apis(encrypted_hex, region)
        if not api_response:
            return jsonify({"error": "Empty response from API"}), 400

        message = AccountPersonalShowInfo()
        message.ParseFromString(bytes.fromhex(api_response))
        result = MessageToDict(message)
        result['Owners']            = ['SENKU CODEX']
        result['Supported_Regions'] = ['IND', 'BD', 'PK']
        return jsonify(result)

    except ValueError:
        return jsonify({"error": "Invalid UID format"}), 400
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": f"Failure to process the data: {str(e)}"}), 500

@app.route('/token-status', methods=['GET'])
def token_status():
    """Debug: check which tokens are loaded"""
    return jsonify({
        r: "OK" if jwt_tokens.get(r) else "MISSING"
        for r in ["IND", "BD", "PK"]
    })

@app.route('/favicon.ico')
def favicon():
    return '', 404

@app.route('/')
def index():
    return jsonify({
        "message":           "Free Fire Account Info API - SENKU CODEX",
        "endpoint":          "/info?uid=PLAYER_UID&region=REGION",
        "supported_regions": ["IND", "BD", "PK"],
        "example":           "/info?uid=12345678&region=IND"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

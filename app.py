from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii, requests, threading, time
from flask import Flask, jsonify, request
from data_pb2 import AccountPersonalShowInfo
from google.protobuf.json_format import MessageToDict
import uid_generator_pb2

app = Flask(__name__)
jwt_tokens = {"IND": None, "BD": None, "PK": None}
updater_started = {"IND": False, "BD": False, "PK": False}
JWT_ENDPOINTS = {
    "IND": "https://raihan-access-to-jwt.vercel.app/token?uid=4344656844&password=RAIHANHACKER01",
    "BD":  "https://raihan-access-to-jwt.vercel.app/token?uid=4363457346&password=SENKU_692491",
    "PK":  "https://raihan-access-to-jwt.vercel.app/token?uid=4363456802&password=SENKU_692458",
}

def get_jwt_token_sync(region):
    try:
        r = requests.get(JWT_ENDPOINTS.get(region, JWT_ENDPOINTS["IND"]), timeout=15)
        data = r.json()
        token = data.get("token") if data.get("success") else None
        if token:
            jwt_tokens[region] = token
            print(f"[JWT] {region} OK")
            return token
    except Exception as e:
        print(f"[JWT] {region} ERROR: {e}")
    return None

def ensure_token(region):
    return jwt_tokens.get(region) or get_jwt_token_sync(region)

def updater(region):
    while True:
        time.sleep(300)
        get_jwt_token_sync(region)

def start_updater(region):
    if not updater_started.get(region):
        updater_started[region] = True
        threading.Thread(target=updater, args=(region,), daemon=True).start()

print("[STARTUP] Fetching JWT tokens for all regions...")
for _r in ["IND","BD","PK"]:
    get_jwt_token_sync(_r)
    start_updater(_r)
print("[STARTUP] Done.")

API_ENDPOINTS = {
    "IND": "https://client.ind.freefiremobile.com/GetPlayerPersonalShow",
    "BD":  "https://clientbp.ggblueshark.com/GetPlayerPersonalShow",
    "PK":  "https://clientbp.ggpolarbear.com/GetPlayerPersonalShow",
}
default_key = "Yg&tc%DEuh6%Zc^8"
default_iv  = "6oyZDr22E3ychjM%"

def encrypt_aes(hex_data):
    k = default_key.encode()[:16]
    iv = default_iv.encode()[:16]
    cipher = AES.new(k, AES.MODE_CBC, iv)
    return cipher.encrypt(__import__('Crypto.Util.Padding',fromlist=['pad']).pad(bytes.fromhex(hex_data),16)).hex()

def encrypt_data(hex_data):
    from Crypto.Util.Padding import pad as _pad
    k = default_key.encode()[:16]
    iv = default_iv.encode()[:16]
    cipher = AES.new(k, AES.MODE_CBC, iv)
    return cipher.encrypt(_pad(bytes.fromhex(hex_data), 16)).hex()

@app.route('/info')
def get_player_info():
    try:
        uid = request.args.get('uid')
        region = request.args.get('region','IND').upper()
        if not uid:
            return jsonify({"error":"UID required"}), 400
        if region not in ["IND","BD","PK"]:
            return jsonify({"error":f"Region {region} not supported"}), 400
        token = ensure_token(region)
        if not token:
            return jsonify({"error":f"Failed to get JWT token for region {region}"}), 500
        msg = uid_generator_pb2.uid_generator()
        msg.saturn_ = int(uid)
        msg.garena = 1
        hex_data = msg.SerializeToString().hex()
        enc = encrypt_data(hex_data)
        headers = {
            'User-Agent':'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
            'Authorization':f'Bearer {token}',
            'X-Unity-Version':'2018.4.11f1',
            'X-GA':'v1 1','ReleaseVersion':'OB53',
            'Content-Type':'application/x-www-form-urlencoded',
        }
        resp = requests.post(API_ENDPOINTS[region], headers=headers, data=bytes.fromhex(enc), timeout=15)
        resp.raise_for_status()
        result_msg = AccountPersonalShowInfo()
        result_msg.ParseFromString(resp.content)
        result = MessageToDict(result_msg)
        result['Owners'] = ['SENKU CODEX']
        result['Supported_Regions'] = ['IND','BD','PK']
        return jsonify(result)
    except Exception as e:
        return jsonify({"error":f"Failure to process the data: {str(e)}"}), 500

@app.route('/token-status')
def token_status():
    return jsonify({r:"OK" if jwt_tokens.get(r) else "MISSING" for r in ["IND","BD","PK"]})

@app.route('/')
def index():
    return jsonify({"endpoint":"/info?uid=UID&region=BD","regions":["IND","BD","PK"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

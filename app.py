import os
import re
import base64
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

WAEC_BASE_URL = "https://ghana.waecdirect.org"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def get_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    })
    return session

def embed_qr_code(session, html):
    qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png)["\']', html)
    if qr_match:
        qr_url = f"{WAEC_BASE_URL}/{qr_match.group(1)}"
        try:
            img_res = session.get(qr_url, timeout=10)
            if img_res.status_code == 200:
                b64 = base64.b64encode(img_res.content).decode('utf-8')
                html = html.replace(qr_match.group(1), f"data:image/png;base64,{b64}")
        except:
            pass
    return html

def fix_paths(html):
    replacements = [
        ('src="/', f'src="{WAEC_BASE_URL}/'),
        ('href="/', f'href="{WAEC_BASE_URL}/'),
        ('src="./', f'src="{WAEC_BASE_URL}/'),
        ('href="./', f'href="{WAEC_BASE_URL}/'),
    ]
    for old, new in replacements:
        html = html.replace(old, new)
    return html

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

@app.route('/fetch', methods=['POST'])
def fetch():
    session = get_session()
    
    data = request.form.to_dict()
    
    payload = {
        "candid": data.get("candid", ""),
        "examtype": data.get("examtype", ""),
        "examyear": data.get("examyear", ""),
        "serial": data.get("serial", ""),
        "pin": data.get("pin", ""),
        "ccandid": data.get("candid", ""),
        "cexamyear": data.get("examyear", ""),
        "referpage": "index.htm",
        "submit": "Submit"
    }
    
    try:
        session.get(f"{WAEC_BASE_URL}/index.htm", timeout=15)
        response = session.post(f"{WAEC_BASE_URL}/results.asp", data=payload, timeout=45)
        response.encoding = 'utf-8'
        html = response.text
        
        html = fix_paths(html)
        html = embed_qr_code(session, html)
        
        if "Candidate Name" in html or "Results" in html:
            return jsonify({"success": True, "html": html})
        else:
            return jsonify({"success": False, "error": "No result found"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/check', methods=['POST'])
def check():
    return fetch()

@app.route('/fetch_and_return', methods=['POST'])
def fetch_and_return():
    return fetch()

@app.route('/', methods=['GET'])
def index():
    return jsonify({"service": "WAEC Bridge", "status": "running"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

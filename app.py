import os
import re
import base64
import requests
from flask import Flask, request, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Crucial for cross-domain requests from WordPress

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = request.form.to_dict()
    
    # WAEC internal structure requires duplicated fields for verification
    payload = {
        "candid": data.get("candid"),
        "ccandid": data.get("candid"),
        "examyear": data.get("examyear"),
        "cexamyear": data.get("examyear"),
        "examtype": data.get("examtype"),
        "cexamtype": data.get("examtype"),
        "serial": data.get("serial"),
        "pin": data.get("pin"),
        "referpage": "index.htm",
        "submit": "Submit"
    }

    try:
        # Get cookies
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=10)

        # Post data
        response = session.post("https://ghana.waecdirect.org/results.asp", data=payload, headers=headers, timeout=30)
        html = response.text

        # Inject Base URL so images/styles load from WAEC
        html = '<base href="https://ghana.waecdirect.org/">' + html

        # Base64 QR Code Fix
        qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png|QRCode\.ashx[^"\']+)["\']', html)
        if qr_match:
            qr_url = f"https://ghana.waecdirect.org/{qr_match.group(1)}"
            try:
                img_res = session.get(qr_url, headers=headers, timeout=5)
                if img_res.status_code == 200:
                    b64 = base64.b64encode(img_res.content).decode('utf-8')
                    html = html.replace(qr_match.group(1), f"data:image/png;base64,{b64}")
            except: pass

        return Response(html, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    # Ensure it listens on the port provided by Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

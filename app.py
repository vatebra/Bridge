import os
import re
import base64
from flask import Flask, request, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Get data from your WordPress AceOdds form
    data = request.form.to_dict()
    
    # EXACT PAYLOAD MAPPING: 
    # WAEC uses 'candid' for the input name but 'ccandid' for the processing logic
    payload = {
        "candid": data.get("candid"),
        "ccandid": data.get("candid"),
        "examyear": data.get("examyear"),
        "cexamyear": data.get("examyear"),
        "examtype": data.get("examtype", "01"),
        "serial": data.get("serial"),
        "pin": data.get("pin"),
        "referpage": "index.htm",
        "submit": "Submit"
    }

    try:
        # Step 1: Initialize cookies
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)

        # Step 2: Post data
        waec_url = "https://ghana.waecdirect.org/results.asp"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        
        # Ensure we handle the encoding for Ghanaian characters if any
        response.encoding = 'utf-8'
        html = response.text

        # --- FIXES ---

        # 1. Inject Base URL to fix the destination/branding issue
        html = '<base href="https://ghana.waecdirect.org/">' + html

        # 2. Permanent QR Code Fix
        qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png|QRCode\.ashx[^"\']+)["\']', html)
        if qr_match:
            qr_relative_url = qr_match.group(1)
            qr_full_url = f"https://ghana.waecdirect.org/{qr_relative_url}"
            try:
                img_res = session.get(qr_full_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    b64_img = base64.b64encode(img_res.content).decode('utf-8')
                    html = html.replace(qr_relative_url, f"data:image/png;base64,{b64_img}")
            except:
                pass

        return Response(html, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

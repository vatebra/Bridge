import os
import re
import base64
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/fetch_and_return', methods=['POST'])
def fetch_and_return():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
    }
    
    data = request.form.to_dict()
    payload = {
        **data,
        "ccandid": data.get("candid"),
        "cexamyear": data.get("examyear"),
        "referpage": "index.htm",
        "submit": "Submit"
    }
    
    try:
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)
        response = session.post("https://ghana.waecdirect.org/results.asp", data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text
        
        # Embed QR code as base64
        qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png)["\']', html)
        if qr_match:
            qr_url = f"https://ghana.waecdirect.org/{qr_match.group(1)}"
            try:
                img_res = session.get(qr_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    b64 = base64.b64encode(img_res.content).decode('utf-8')
                    html = html.replace(qr_match.group(1), f"data:image/png;base64,{b64}")
            except:
                pass
        
        if 'Candidate Name' in html:
            return jsonify({'success': True, 'html': html})
        else:
            return jsonify({'success': False, 'error': 'Invalid result'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

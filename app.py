import os
import re
import base64
from flask import Flask, request, Response
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/check', methods=['POST', 'OPTIONS'])
def proxy_waec():
    if request.method == 'OPTIONS':
        return Response('', headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        })
    
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9"
    }

    data = request.form.to_dict()
    
    payload = {
        'candid': data.get('candid', ''),
        'examyear': data.get('examyear', ''),
        'examtype': data.get('examtype', ''),
        'serial': data.get('serial', ''),
        'pin': data.get('pin', ''),
        'ccandid': data.get('candid', ''),
        'cexamyear': data.get('examyear', ''),
        'referpage': 'index.htm',
        'submit': 'Submit'
    }

    try:
        # Get session cookie
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)
        
        # Post to get results
        response = session.post("https://ghana.waecdirect.org/results.asp", data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # Check for error
        if "Invalid" in html or "login again" in html.lower():
            return Response("Invalid credentials. Please check your Index Number, Serial, and PIN.", status=400)

        # Embed QR code as base64
        qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png)["\']', html)
        
        if qr_match:
            qr_relative_url = qr_match.group(1)
            qr_full_url = f"https://ghana.waecdirect.org/{qr_relative_url}"
            
            try:
                img_res = session.get(qr_full_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    b64_img = base64.b64encode(img_res.content).decode('utf-8')
                    data_uri = f"data:image/png;base64,{b64_img}"
                    html = html.replace(qr_relative_url, data_uri)
            except Exception:
                pass

        return Response(html, mimetype='text/html', headers={'Access-Control-Allow-Origin': '*'})

    except Exception as e:
        return Response(f"Bridge Error: {str(e)}", status=500)

@app.route('/')
@app.route('/health')
def health():
    return {"status": "healthy", "message": "WAEC Proxy is running", "endpoint": "/check"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

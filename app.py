import os
import re
import base64
import requests
from flask import Flask, request, Response
from urllib.parse import urljoin

app = Flask(__name__)

# The base URL for WAEC Ghana
BASE_URL = "https://ghana.waecdirect.org/"

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": f"{BASE_URL}index.htm",
        "Origin": BASE_URL[:-1],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    # Gather data from your WordPress form
    data = request.form.to_dict()
    
    # Payload using WAEC's internal field names
    payload = {
        "IDNo": data.get("candid"),
        "ExamYear": data.get("examyear"),
        "ExamType": data.get("examtype"),
        "SerialNo": data.get("serial"),
        "PIN": data.get("pin"),
        "submit": "Submit"
    }

    try:
        # Step 1: Session Handshake (Required for ASP.NET session state)
        session.get(f"{BASE_URL}index.htm", headers=headers, timeout=15)

        # Step 2: Post to the results endpoint
        waec_url = urljoin(BASE_URL, "results.asp")
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # Step 3: ASSET HARDENING (Fixing broken images/styles)
        
        # 1. Fix the QR Code (Convert to Base64 so it's permanent)
        qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png)["\']', html)
        if qr_match:
            qr_rel = qr_match.group(1)
            try:
                qr_res = session.get(urljoin(BASE_URL, qr_rel), headers=headers)
                if qr_res.status_code == 200:
                    b64 = base64.b64encode(qr_res.content).decode()
                    html = html.replace(qr_rel, f"data:image/png;base64,{b64}")
            except: pass

        # 2. Fix Signatures & Logos (Convert relative paths to absolute)
        # This ensures images like /images/logo.gif actually load
        html = html.replace('src="images/', f'src="{BASE_URL}images/')
        html = html.replace('src="img/', f'src="{BASE_URL}img/')
        
        # 3. Fix Internal CSS Links
        html = html.replace('href="', f'href="{BASE_URL}')

        # Step 4: Inject a "Print" button for student convenience
        print_script = """
        <div style="text-align:center; margin:20px; no-print">
            <button onclick="window.print()" style="padding:10px 20px; cursor:pointer; background:#93c5fd; border:none; border-radius:5px;">Print Result</button>
        </div>
        <style> @media print { .no-print { display:none; } } </style>
        """
        html = html.replace('</body>', f'{print_script}</body>')

        return Response(html, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

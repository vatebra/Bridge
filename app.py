import os
import re
import base64
import requests
from flask import Flask, request, Response
from flask_cors import CORS
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app)

# The base URL for WAEC Ghana
BASE_URL = "https://ghana.waecdirect.org/"

@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "healthy", "message": "WAEC Bridge is running"}

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
        "Referer": f"{BASE_URL}index.htm",
        "Origin": BASE_URL[:-1],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    # Gather data from your WordPress form
    data = request.form.to_dict()
    
    # IMPORTANT: Use WAEC's EXACT field names as shown in their HTML
    payload = {
        "candid": data.get("candid", ""),        # NOT IDNo
        "examyear": data.get("examyear", ""),    # NOT ExamYear
        "examtype": data.get("examtype", ""),    # NOT ExamType
        "serial": data.get("serial", ""),        # NOT SerialNo
        "pin": data.get("pin", ""),              # NOT PIN
        "ccandid": data.get("candid", ""),       # Confirmation fields
        "cexamyear": data.get("examyear", ""),   # Confirmation fields
        "cday": data.get("cday", ""),            # Date of Birth day
        "cmonth": data.get("cmonth", ""),        # Date of Birth month
        "cyear": data.get("cyear", ""),          # Date of Birth year
        "referpage": "index.htm",
        "submit": "Submit"
    }
    
    # Remove empty fields to avoid sending unnecessary data
    payload = {k: v for k, v in payload.items() if v != ""}

    try:
        print(f"Connecting to WAEC...")
        print(f"Payload: {payload}")
        
        # Step 1: Session Handshake (Required for ASP.NET session state)
        session.get(f"{BASE_URL}index.htm", headers=headers, timeout=15)

        # Step 2: Post to the results endpoint
        waec_url = urljoin(BASE_URL, "results.asp")
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text
        print(f"Response status: {response.status_code}")
        print(f"Response length: {len(html)}")

        # Check for WAEC error messages
        if "Invalid" in html or "not valid" in html.lower():
            # Extract the error message
            error_match = re.search(r'<div[^>]*class="error"[^>]*>(.*?)</div>', html, re.IGNORECASE)
            if error_match:
                error_msg = error_match.group(1)
            else:
                error_msg = "Invalid credentials. Please check your Index Number, Exam Type, Year, Serial, and PIN."
            return Response(error_msg, status=400)

        # Step 3: ASSET HARDENING (Fixing broken images/styles)
        
        # Fix the QR Code (Convert to Base64 so it's permanent)
        qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png)["\']', html)
        if qr_match:
            qr_rel = qr_match.group(1)
            try:
                qr_res = session.get(urljoin(BASE_URL, qr_rel), headers=headers, timeout=10)
                if qr_res.status_code == 200:
                    b64 = base64.b64encode(qr_res.content).decode()
                    html = html.replace(qr_rel, f"data:image/png;base64,{b64}")
                    print("QR code embedded successfully")
            except Exception as e:
                print(f"QR error: {e}")

        # Fix relative image paths
        html = html.replace('src="images/', f'src="{BASE_URL}images/')
        html = html.replace('src="img/', f'src="{BASE_URL}img/')
        html = html.replace('src="/images/', f'src="{BASE_URL}images/')
        
        # Fix CSS links
        html = html.replace('href="include/', f'href="{BASE_URL}include/')

        # Step 4: Inject a "Print" button for student convenience
        print_script = """
        <div style="text-align:center; margin:20px; no-print">
            <button onclick="window.print()" style="padding:10px 20px; cursor:pointer; background:#003300; color:white; border:none; border-radius:5px;">Print Result</button>
        </div>
        <style> @media print { .no-print { display:none; } } </style>
        """
        
        # Add base tag for proper relative URL resolution
        base_tag = '<base href="' + BASE_URL + '">'
        if '<head>' in html.lower():
            html = html.replace('<head>', '<head>' + base_tag, 1)
        else:
            html = base_tag + html
        
        html = html.replace('</body>', f'{print_script}</body>')

        return Response(html, mimetype='text/html', headers={'Access-Control-Allow-Origin': '*'})

    except requests.exceptions.Timeout:
        return Response("Connection to WAEC timed out. Please try again.", status=504)
    except requests.exceptions.ConnectionError as e:
        return Response(f"Connection error: {str(e)}", status=503)
    except Exception as e:
        print(f"Error: {e}")
        return Response(f"Bridge Error: {str(e)}", status=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting WAEC Bridge on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

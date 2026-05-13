import os
import re
import base64
from flask import Flask, request, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
# Enable CORS so your WordPress site can communicate with this bridge
CORS(app)

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    
    # Authenticity headers to mimic a real browser session
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    # Get data from the WordPress form
    data = request.form.to_dict()
    
    # Construct the payload required by WAEC's results.asp
    payload = {
        **data,
        "ccandid": data.get("candid"),
        "cexamyear": data.get("examyear"),
        "referpage": "index.htm",
        "submit": "Submit"
    }

    try:
        # Step 1: Establish a session cookie by visiting the home page
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)

        # Step 2: Post the credentials to fetch the results
        waec_url = "https://ghana.waecdirect.org/results.asp"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # --- BRANDING & AUTHENTICITY FIXES ---

        # FIX 1: URL Destination Masking
        # Inject the <base> tag so internal links/styles point to WAEC, not your site
        base_tag = '<base href="https://ghana.waecdirect.org/">'
        html = base_tag + html

        # FIX 2: PERMANENT QR CODE
        # Find the QR code source and convert it to Base64 so it doesn't expire
        qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png|QRCode\.ashx[^"\']+)["\']', html)
        
        if qr_match:
            qr_relative_url = qr_match.group(1)
            qr_full_url = f"https://ghana.waecdirect.org/{qr_relative_url}"
            
            try:
                # Download the image and encode it
                img_res = session.get(qr_full_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    b64_img = base64.b64encode(img_res.content).decode('utf-8')
                    data_uri = f"data:image/png;base64,{b64_img}"
                    html = html.replace(qr_relative_url, data_uri)
            except Exception:
                # Fallback: if QR download fails, the <base> tag still helps it load
                pass 

        return Response(html, mimetype='text/html')

    except Exception as e:
        # Returns a clean error message to your WordPress frontend
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    # Ensure the app binds to the port provided by Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

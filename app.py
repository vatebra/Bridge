import os
import re
import base64
import random
from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    
    # Sophisticated browser identity rotation to ensure smooth tracking
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Referer": "https://eresults.waecgh.org/",
        "Origin": "https://eresults.waecgh.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }

    # Extract clean parameters from incoming WordPress POST request
    data = request.form.to_dict()
    index_num = data.get("index_number")
    
    # Map incoming clean keys to the exact form requirements from eresults HTML
    payload = {
        "form-indexnum": index_num,
        "form-cindexnum": index_num,                  # Programmatic mirroring loophole
        "form-examtype": data.get("exam_type"),        # Code strings: BECE, WASS, etc.
        "form-examyear": data.get("exam_year"),
        "form-csn": data.get("serial"),
        "form-pin": data.get("pin"),
        "g-recaptcha-response": data.get("captcha_token")  # Pass frontend resolved token
    }

    try:
        # Step 1: Establish Cookie State against the new portal
        session.get("https://eresults.waecgh.org/", headers=headers, timeout=15)

        # Step 2: Post to the precise search router endpoint
        waec_url = "https://eresults.waecgh.org/Home/searcheresult"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # Step 3: HARDEN THE QR CODE (The Loophole Fix)
        # Keeps original matching logic to look for the image path and bake it into Base64
        qr_match = re.search(r'src=["\'](assets/img/[^"\']+\.png)["\']|src=["\'](qrcode2/[^"\']+\.png)["\']', html)
        
        if qr_match:
            # Capture whichever matching group successfully trapped the image path
            qr_relative_url = qr_match.group(1) or qr_match.group(2)
            qr_full_url = f"https://eresults.waecgh.org/{qr_relative_url}"
            
            try:
                # Download the actual image bytes mid-air
                img_res = session.get(qr_full_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    # Convert image to Base64 data URI
                    b64_img = base64.b64encode(img_res.content).decode('utf-8')
                    data_uri = f"data:image/png;base64,{b64_img}"
                    
                    # Replace dynamic source reference with permanent string
                    html = html.replace(qr_relative_url, data_uri)
            except Exception:
                pass # If dynamic download slips, output original markup safely

        # Return the optimized, modified HTML payload to WordPress
        return Response(html, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

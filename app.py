import os
import re
import base64
import random
from flask import Flask, request, Response
import requests

app = Flask(__name__)

# SECURITY PARITY: YOUR PRODUCTION GOOGLE RECAPTCHA SECRET KEY
RECAPTCHA_SECRET_KEY = "6LeH1ugsAAAAALZCHqjuHEP44kSGqAv4F9f_Cf-g"

@app.route('/check', methods=['POST'])
def proxy_waec():
    # Extract structural arguments from your WordPress AJAX client
    data = request.form.to_dict()
    captcha_token = data.get("captcha_token")
    
    # STEP 1: VERIFY TOKEN ENVELOPE AGAINST GOOGLE SECURITY ROUTERS
    if not captcha_token:
        return "Security Check Failed: Missing Captcha Token.", 400
        
    try:
        verify_res = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": RECAPTCHA_SECRET_KEY,
                "response": captcha_token
            },
            timeout=10
        ).json()
        
        # Drop execution sequence immediately if verification fails
        if not verify_res.get("success"):
            return "Security Check Failed: Invalid Captcha Verification.", 400
            
    except Exception as e:
        return f"Security Gateway Error: Unable to verify Captcha ({str(e)})", 500

    # STEP 2: ORCHESTRATE SESSION CONTEXT AGAINST THE PORTAL HOST
    session = requests.Session()
    
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

    index_num = data.get("index_number")
    
    # Remap custom inputs to mirror structural DOM expectations exactly
    payload = {
        "form-indexnum": index_num,
        "form-cindexnum": index_num,                  # Cloning loophole shortcut
        "form-examtype": data.get("exam_type"),        
        "form-examyear": data.get("exam_year"),
        "form-csn": data.get("serial"),
        "form-pin": data.get("pin"),
        "g-recaptcha-response": captcha_token         
    }

    try:
        # Establish structural session boundaries and trace tracking cookies
        session.get("https://eresults.waecgh.org/", headers=headers, timeout=15)

        # Dispatch search parameters to processing core controller
        waec_url = "https://eresults.waecgh.org/Home/searcheresult"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # STEP 3: CONVERT RELATIVE ASSET REFERENCES TO ABSOLUTE WAEC CDN LINKS
        html = html.replace('href="assets/', 'href="https://eresults.waecgh.org/assets/')
        html = html.replace('href="/assets/', 'href="https://eresults.waecgh.org/assets/')
        html = html.replace('src="assets/', 'src="https://eresults.waecgh.org/assets/')
        html = html.replace('src="/assets/', 'src="https://eresults.waecgh.org/assets/')

        # STEP 4: INTERCEPT AND HARDEN RESPONSIVE QR CODE SLOTS INTO BASE64 IMAGES
        qr_match = re.search(r'src=["\'](assets/img/[^"\']+\.png)["\']|src=["\'](qrcode2/[^"\']+\.png)["\']', html)
        
        if qr_match:
            qr_relative_url = qr_match.group(1) or qr_match.group(2)
            
            if "https://" not in qr_relative_url:
                qr_full_url = f"https://eresults.waecgh.org/{qr_relative_url.replace('https://eresults.waecgh.org/', '')}"
            else:
                qr_full_url = qr_relative_url
            
            try:
                img_res = session.get(qr_full_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    b64_img = base64.b64encode(img_res.content).decode('utf-8')
                    data_uri = f"data:image/png;base64,{b64_img}"
                    html = html.replace(qr_relative_url, data_uri)
            except Exception:
                pass 

        # Return pristine, stylized results markup directly to client
        return Response(html, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

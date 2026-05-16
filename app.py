import os
import re
import base64
import random
from flask import Flask, request, Response
import requests

app = Flask(__name__)

RECAPTCHA_SECRET_KEY = "6LeH1ugsAAAAALZCHqjuHEP44kSGqAv4F9f_Cf-g"

@app.route('/check', methods=['POST'])
def proxy_waec():
    data = request.form.to_dict()
    captcha_token = data.get("captcha_token")
    
    # Verify local captcha first
    if not captcha_token:
        return "Local Error: Missing Captcha Token.", 400
    try:
        verify_res = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": captcha_token},
            timeout=10
        ).json()
        if not verify_res.get("success"):
            return "Local Error: Captcha validation failed against your secret key.", 400
    except Exception as e:
        return f"Local Error: reCAPTCHA verification crashed ({str(e)})", 500

    # Build the WAEC session
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": "https://eresults.waecgh.org",
        "Referer": "https://eresults.waecgh.org/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    index_num = data.get("index_number")
    payload = {
        "form-indexnum": index_num,
        "form-cindexnum": index_num,
        "form-examtype": data.get("exam_type"),        
        "form-examyear": data.get("exam_year"),
        "form-csn": data.get("serial"),
        "form-pin": data.get("pin"),
        "g-recaptcha-response": "" # Sending blank to avoid domain match mismatch on WAEC side
    }

    try:
        # Establish session cookies
        session.get("https://eresults.waecgh.org/", headers=headers, timeout=15)

        # Hit the live database endpoint
        waec_url = "https://eresults.waecgh.org/Home/searcheresult"
        response = session.post(waec_url, data=payload, headers=headers, timeout=30)
        
        # Capture the raw content type and response encoding
        response.encoding = 'utf-8'
        
        # CRITICAL DIAGNOSTIC: If it is an error status code, pass the EXACT HTML text along with its raw code
        if response.status_code != 200:
            return Response(
                f"<h3>RAW WAEC GATEWAY ERROR (HTTP CODE {response.status_code})</h3><hr><pre>{response.text}</pre>", 
                status=response.status_code, 
                mimetype='text/html'
            )

        html = response.text

        # Fix any relative assets so if they returned an error page layout it renders visually
        html = html.replace('href="assets/', 'href="https://eresults.waecgh.org/assets/')
        html = html.replace('href="/assets/', 'href="https://eresults.waecgh.org/assets/')
        html = html.replace('src="assets/', 'src="https://eresults.waecgh.org/assets/')
        html = html.replace('src="/assets/', 'src="https://eresults.waecgh.org/assets/')

        return Response(html, mimetype='text/html')

    except Exception as e:
        # If the network connection physically dropped before getting a response, output the raw Python exception details
        return Response(f"<h3>RAW PYTHON SCRIPT EXCEPTION</h3><hr><p>{str(e)}</p>", status=500, mimetype='text/html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

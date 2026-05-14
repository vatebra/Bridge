import os
import re
import base64
import requests
from flask import Flask, request, Response
from bs4 import BeautifulSoup

app = Flask(__name__)

# Using a dictionary to act as a 'Session Vault'
session_vault = {}

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    data = request.form.to_dict()
    
    # Unique ID for the student's specific result
    student_id = f"{data.get('candid')}_{data.get('examyear')}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org"
    }

    try:
        # 1. THE "ANYTIME" REPLAY CHECK
        # If we already have a 'frozen' state for this student, try to use it first
        if student_id in session_vault:
            frozen_state = session_vault[student_id]
            viewstate_val = frozen_state['viewstate']
            session.cookies.update(frozen_state['cookies'])
        else:
            # 2. FRESH HANDSHAKE
            # If it's a new check, get a fresh ViewState from the homepage
            init_res = session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)
            soup = BeautifulSoup(init_res.text, 'html.parser')
            viewstate_val = soup.find("input", {"id": "__VIEWSTATE"})['value']

        payload = {
            "__VIEWSTATE": viewstate_val,
            **data,
            "ccandid": data.get("candid"),
            "cexamyear": data.get("examyear"),
            "referpage": "index.htm",
            "submit": "Submit"
        }

        # 3. RETRIEVE RESULT
        waec_url = "https://ghana.waecdirect.org/results.asp"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # 4. FREEZE FOR LATER
        # If the result is successful, save the ViewState to allow 'Anytime' access
        if "Result Details" in html:
            res_soup = BeautifulSoup(html, 'html.parser')
            current_vs = res_soup.find("input", {"id": "__VIEWSTATE"})
            if current_vs:
                session_vault[student_id] = {
                    'viewstate': current_vs['value'],
                    'cookies': session.cookies.get_dict()
                }

        # 5. HARDEN QR CODE (Base64)
        qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png)["\']', html)
        if qr_match:
            qr_relative_url = qr_match.group(1)
            qr_full_url = f"https://ghana.waecdirect.org/{qr_relative_url}"
            try:
                img_res = session.get(qr_full_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    b64_img = base64.b64encode(img_res.content).decode('utf-8')
                    html = html.replace(qr_relative_url, f"data:image/png;base64,{b64_img}")
            except: pass

        return Response(html, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

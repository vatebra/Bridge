import os
import re
import base64
import requests
from flask import Flask, request, Response
from bs4 import BeautifulSoup

app = Flask(__name__)

# Simple in-memory storage for frozen sessions
# In production, use a database or Redis
frozen_sessions = {}

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    data = request.form.to_dict()
    
    # Use Index Number + Year + PIN as a unique key for freezing
    session_key = f"{data.get('candid')}_{data.get('examyear')}_{data.get('pin')}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    try:
        # --- FREEZING LOGIC START ---
        # Check if we have a "frozen" ViewState and Cookies for this specific student
        if session_key in frozen_sessions:
            frozen_data = frozen_sessions[session_key]
            viewstate_val = frozen_data['viewstate']
            session.cookies.update(frozen_data['cookies'])
        else:
            # Step 1: Establish fresh Session & Capture initial ViewState
            init_res = session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)
            soup = BeautifulSoup(init_res.text, 'html.parser')
            vs_input = soup.find("input", {"id": "__VIEWSTATE"})
            viewstate_val = vs_input['value'] if vs_input else ""
        # --- FREEZING LOGIC END ---

        payload = {
            "__VIEWSTATE": viewstate_val,
            **data,
            "ccandid": data.get("candid"),
            "cexamyear": data.get("examyear"),
            "referpage": "index.htm",
            "submit": "Submit"
        }

        # Step 2: Post to get results
        waec_url = "https://ghana.waecdirect.org/results.asp"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # --- CAPTURE SUCCESSFUL STATE ---
        # If results are found, "freeze" this viewstate for the next 20 mins
        if "Result Details" in html and session_key not in frozen_sessions:
            soup_result = BeautifulSoup(html, 'html.parser')
            new_vs = soup_result.find("input", {"id": "__VIEWSTATE"})
            if new_vs:
                frozen_sessions[session_key] = {
                    'viewstate': new_vs['value'],
                    'cookies': session.cookies.get_dict()
                }

        # Step 3: HARDEN THE QR CODE (Loophole Fix remains the same)
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

        return Response(html, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

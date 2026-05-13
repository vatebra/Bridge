import os
import re
import base64
from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
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
        # Step 1: Establish Session
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)

        # Step 2: Post to get results
        waec_url = "https://ghana.waecdirect.org/results.asp"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # Step 3: Replace your domain with WAEC official URL (Fixes the top right link)
        my_domain = "waecghresults.com"
        waec_official_url = "https://ghana.waecdirect.org/displayresults.asp"
        
        html = html.replace(f"https://{my_domain}", waec_official_url)
        html = html.replace(f"http://{my_domain}", waec_official_url)
        html = html.replace(f"//{my_domain}", waec_official_url)

        # Step 4: HARDEN THE QR CODE (The Loophole Fix)
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

        # Return the modified HTML to WordPress
        return Response(html, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

import os
from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    
    # 1. ENHANCED HEADERS (The Spoof)
    # We use the exact headers a real browser sends when clicking "Submit"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://ghana.waecdirect.org/index.htm", # Start referer
        "Origin": "https://ghana.waecdirect.org",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    data = request.form.to_dict()
    
    # Standard WAEC form payload
    payload = {
        **data,
        "ccandid": data.get("candid"),
        "cexamyear": data.get("examyear"),
        "referpage": "index.htm",
        "submit": "Submit"
    }

    try:
        # 2. INITIALIZE SESSION
        # This grabs the required ASP cookies (like ASPSESSIONID)
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)

        # 3. THE ACTUAL POST
        # We update the referer to itself just before posting (common ASP trick)
        headers["Referer"] = "https://ghana.waecdirect.org/index.htm"
        
        waec_url = "https://ghana.waecdirect.org/results.asp"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)

        # Ensure the response is treated as UTF-8 to prevent character bugs
        response.encoding = 'utf-8'

        return Response(response.text, mimetype='text/html')

    except requests.exceptions.Timeout:
        return "WAEC Server timed out. Please try again.", 504
    except Exception as e:
        return f"Python Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

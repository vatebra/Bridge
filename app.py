import os
from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/check', methods=['POST'])
def proxy_waec():
    # Using Session to maintain cookies for the QR handler
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Upgrade-Insecure-Requests": "1"
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
        # Step 1: Hit the index page to get session cookies
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)

        # Step 2: Post the result request
        waec_url = "https://ghana.waecdirect.org/results.asp"
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        
        # Ensure we return valid UTF-8
        response.encoding = 'utf-8'
        
        # Return result to WordPress
        return Response(response.text, mimetype='text/html')

    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

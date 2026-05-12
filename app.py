from flask import Flask, request, Response
from flask_cors import CORS
import requests

app = Flask(__name__)

# 1. ALLOW CORS: This prevents the "Connection Error" in the browser.
# For maximum security, replace '*' with your actual domain: 'https://aceodds.gh'
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/bridge', methods=['POST'])
def bridge():
    """
    Acts as a transparent proxy. The user's browser sends WAEC credentials 
    to this bridge, and the bridge fetches the result from WAEC.
    """
    waec_url = "https://ghana.waecdirect.org/DisplayResults.aspx"
    
    # Get the form data (candid, examyear, examtype, serial, pin) from the browser
    payload = request.form.to_dict()
    
    # Headers to mimic a real person using a browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://ghana.waecdirect.org/Default.aspx',
        'Origin': 'https://ghana.waecdirect.org',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    try:
        # Step 1: Bridge makes the request to WAEC
        response = requests.post(
            waec_url, 
            data=payload, 
            headers=headers, 
            timeout=45, # High timeout for slow WAEC servers
            allow_redirects=True
        )
        
        # Step 2: Send the raw HTML back to the user's browser
        return Response(
            response.text, 
            status=response.status_code, 
            mimetype='text/html'
        )

    except requests.exceptions.Timeout:
        return "WAEC Server took too long to respond.", 504
    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

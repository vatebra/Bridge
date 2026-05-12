from flask import Flask, request, Response
from flask_cors import CORS # Must install via pip install flask-cors
import requests

app = Flask(__name__)
# This line fixes the 'NetworkError' by allowing your browser to talk to the bridge
CORS(app) 

@app.route('/bridge', methods=['POST'])
def bridge():
    waec_url = "https://ghana.waecdirect.org/DisplayResults.aspx"
    payload = request.form.to_dict()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://ghana.waecdirect.org/Default.aspx',
        'Origin': 'https://ghana.waecdirect.org'
    }

    try:
        # High timeout for slow WAEC Ghana servers
        response = requests.post(waec_url, data=payload, headers=headers, timeout=60)
        return Response(response.text, mimetype='text/html')
    except Exception as e:
        return f"Bridge Connection Failed: {str(e)}", 500

if __name__ == "__main__":
    app.run()

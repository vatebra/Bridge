from flask import Flask, request, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
# Allows your WordPress domain to communicate with this bridge
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
        # Fetch the result from WAEC
        response = requests.post(waec_url, data=payload, headers=headers, timeout=45)
        return Response(response.text, mimetype='text/html')
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run()

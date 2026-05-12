from flask import Flask, request, Response
from flask_cors import CORS
import requests

app = Flask(__name__)
# Allows your browser to communicate with this bridge without security blocks
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
        # Fetch the result from WAEC with a high timeout for slow servers
        response = requests.post(waec_url, data=payload, headers=headers, timeout=60)
        
        if response.status_code != 200:
            return f"WAEC Server Error: {response.status_code}", 500
            
        return Response(response.text, mimetype='text/html')
    except Exception as e:
        return f"Bridge Connection Failed: {str(e)}", 500

if __name__ == "__main__":
    app.run()

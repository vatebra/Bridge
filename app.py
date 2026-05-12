from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/bridge', methods=['POST'])
def bridge():
    waec_url = "https://ghana.waecdirect.org/DisplayResults.aspx"
    
    # Forward the user's form data to WAEC
    payload = request.form.to_dict()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://ghana.waecdirect.org/Default.aspx'
    }

    try:
        response = requests.post(waec_url, data=payload, headers=headers, timeout=30)
        # We send the raw HTML back to the user's browser
        return Response(response.text, mimetype='text/html')
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run()

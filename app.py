import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
# Enable CORS so your WordPress domain can talk to this API
CORS(app, resources={r"/*": {"origins": "*"}})

# --- DATABASE CONFIGURATION ---
DB_CONFIG = {
    'host': 'your_db_host',
    'user': 'your_db_user',
    'password': 'your_db_password',
    'database': 'your_db_name'
}

def sync_to_database(candid, year, type, name, html):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        query = """
            INSERT INTO wppk_waec_results 
            (index_number, exam_year, exam_type, candidate_name, result_data, checked_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE 
            candidate_name = %s, result_data = %s, checked_at = NOW()
        """
        cursor.execute(query, (candid, year, type, name, html, name, html))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database Sync Error: {e}")

@app.route('/fetch_result', methods=['POST'])
def fetch_result():
    data = request.json
    payload = {
        'candid': data.get('candid'),
        'examyear': data.get('examyear'),
        'examtype': data.get('examtype'),
        'serial': data.get('serial'),
        'pin': data.get('pin'),
        'submit': 'Submit'
    }

    session = requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://ghana.waecdirect.org/'
    }

    try:
        # Step 1: Handshake to get cookies
        session.get('https://ghana.waecdirect.org/', headers=headers, timeout=10)

        # Step 2: Post data to WAEC
        response = session.post('https://ghana.waecdirect.org/results.aspx', data=payload, headers=headers, timeout=25)

        if "Candidate Name" in response.text:
            # Parse Name
            soup = BeautifulSoup(response.text, 'html.parser')
            name_cell = soup.find(lambda tag: tag.name == "td" and "Candidate Name" in tag.text)
            cand_name = name_cell.find_next_sibling("td").text.strip() if name_cell else "Unknown"

            # Step 3: Save to DB
            sync_to_database(payload['candid'], payload['examyear'], payload['examtype'], cand_name, response.text)

            res = make_response(jsonify({"success": True, "html": response.text}))
            return res
        
        return jsonify({"success": False, "error": "Invalid Details or PIN already used."}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

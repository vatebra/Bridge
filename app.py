import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Allows AceOdds to communicate with this bridge

# --- DATABASE CONFIGURATION ---
db_config = {
    'host': 'your_db_host',
    'user': 'your_db_user',
    'password': 'your_db_password',
    'database': 'your_database_name'
}

def save_to_db(candid, examyear, examtype, name, raw_html):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = """INSERT INTO wppk_waec_results 
                   (index_number, exam_year, exam_type, candidate_name, result_data) 
                   VALUES (%s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE result_data = %s"""
        cursor.execute(query, (candid, examyear, examtype, name, raw_html, raw_html))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")

@app.route('/check', methods=['POST'])
def check_waec():
    # 1. Get data from your WordPress Form
    candid = request.form.get('candid')
    examyear = request.form.get('examyear')
    examtype = request.form.get('examtype')
    serial = request.form.get('serial')
    pin = request.form.get('pin')

    session = requests.Session()
    
    # 2. STEP ONE: Perform the Handshake
    # We hit the homepage first to get the ASPSESSIONID cookie
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
    }
    session.get('https://ghana.waecdirect.org/', headers=headers)

    # 3. STEP TWO: Submit the Data
    payload = {
        'candid': candid,
        'examyear': examyear,
        'examtype': examtype,
        'serial': serial,
        'pin': pin,
        'submit': 'Submit'
    }
    
    # We send the request to the official results page
    response = session.post('https://ghana.waecdirect.org/results.asp', data=payload, headers=headers)

    # 4. STEP THREE: Process the Response
    if "Candidate Name" in response.text:
        # Extract Name for the DB
        soup = BeautifulSoup(response.text, 'html.parser')
        name_tag = soup.find(text="Candidate Name")
        candidate_name = "Unknown"
        if name_tag:
            # Assumes name is in the next <td>
            candidate_name = name_tag.find_next('td').get_text(strip=True)

        # Save to AceOdds Database
        save_to_db(candid, examyear, examtype, candidate_name, response.text)
        
        return jsonify({
            "status": "success",
            "html": response.text
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Invalid details or WAEC server busy."
        }), 400

if __name__ == '__main__':
    app.run(debug=True)

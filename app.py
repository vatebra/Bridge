import os
import re
import base64
import json
from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/check', methods=['POST'])
def proxy_waec():
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
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
        # Step 1: Establish Session - Get cookies
        print("Fetching WAEC homepage...")
        session.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15)

        # Step 2: Post to get results
        waec_url = "https://ghana.waecdirect.org/results.asp"
        print("Submitting result request...")
        response = session.post(waec_url, data=payload, headers=headers, timeout=45)
        response.encoding = 'utf-8'
        html = response.text

        # Check if request was successful
        if "Invalid" in html or "error" in html.lower():
            print("WAEC returned an error")
            return Response(html, mimetype='text/html', status=400)

        # Step 3: Extract the QR code data from the JavaScript
        print("Looking for QR code AJAX call...")
        
        # Pattern to extract the txt and chk values from the AJAX call
        txt_pattern = r"data:\s*\{\s*'txt':\s*'([^']+)'"
        chk_pattern = r"'chk':\s*'([^']+)'"
        
        txt_match = re.search(txt_pattern, html)
        chk_match = re.search(chk_pattern, html)
        
        if txt_match and chk_match:
            qrcode_data = {
                'txt': txt_match.group(1),
                'chk': chk_match.group(1)
            }
            print(f"Found QR data - txt length: {len(qrcode_data['txt'])}, chk: {qrcode_data['chk']}")
            
            # Step 4: Make the QR code request server-side
            qr_url = "https://ghana.waecdirect.org/QRCode.ashx"
            print("Requesting QR code from WAEC...")
            
            qr_response = session.post(
                qr_url, 
                data=qrcode_data,
                headers={
                    **headers,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest"
                },
                timeout=10
            )
            
            if qr_response.status_code == 200:
                try:
                    qr_json = qr_response.json()
                    print(f"QR Response Status: {qr_json.get('Status')}")
                    
                    if qr_json.get('Status') == 1:
                        qr_html = qr_json.get('Msg', '')
                        print(f"QR HTML received: {qr_html[:100]}...")
                        
                        # Extract the image source from the QR HTML
                        img_src_match = re.search(r'src="([^"]+)"', qr_html)
                        if img_src_match:
                            img_src = img_src_match.group(1)
                            print(f"QR Image source: {img_src[:100]}...")
                            
                            # If it's a data URL, use it directly
                            if img_src.startswith('data:image'):
                                # Replace the empty span with the QR code image
                                html = html.replace(
                                    '<span id="qrCode"></span>',
                                    f'<span id="qrCode">{qr_html}</span>'
                                )
                                print("✅ QR code embedded successfully (data URL)")
                            else:
                                # Download the image and convert to base64
                                try:
                                    if img_src.startswith('/'):
                                        img_url = f"https://ghana.waecdirect.org{img_src}"
                                    else:
                                        img_url = img_src
                                    
                                    print(f"Downloading QR image from: {img_url}")
                                    img_response = session.get(img_url, headers=headers, timeout=10)
                                    
                                    if img_response.status_code == 200:
                                        b64_img = base64.b64encode(img_response.content).decode('utf-8')
                                        content_type = img_response.headers.get('Content-Type', 'image/png')
                                        data_uri = f"data:{content_type};base64,{b64_img}"
                                        
                                        # Replace with embedded image
                                        html = html.replace(
                                            '<span id="qrCode"></span>',
                                            f'<span id="qrCode"><img src="{data_uri}" border="0" /></span>'
                                        )
                                        print("✅ QR code embedded successfully (downloaded image)")
                                    else:
                                        print(f"Failed to download QR image: {img_response.status_code}")
                                except Exception as e:
                                    print(f"Error downloading QR image: {e}")
                    else:
                        print(f"QR API returned status {qr_json.get('Status')}: {qr_json.get('Msg')}")
                except json.JSONDecodeError as e:
                    print(f"Failed to parse QR response as JSON: {e}")
            else:
                print(f"QR request failed with status: {qr_response.status_code}")
        else:
            print("Could not find QR code data in HTML")
            print("Searching for patterns...")
            if re.search(r'QRCode\.ashx', html):
                print("Found QRCode.ashx reference but couldn't extract data")
        
        # Step 5: Remove the AJAX script to prevent it from running again
        # Find and remove or comment out the QR code AJAX script
        ajax_script_pattern = r'<script type="text/javascript">\s*jQuery\(document\)\.ready[^<]+</script>'
        html = re.sub(ajax_script_pattern, '<!-- QR code AJAX script removed - already embedded server-side -->', html, flags=re.DOTALL)
        
        # Step 6: Fix any relative paths
        html = html.replace('src="images/', 'src="https://ghana.waecdirect.org/images/')
        html = html.replace('href="include/', 'href="https://ghana.waecdirect.org/include/')
        
        print("Returning final HTML with embedded QR code")
        return Response(html, mimetype='text/html')

    except requests.exceptions.Timeout:
        print("Request timed out")
        return Response("Request timed out. Please try again.", 504)
    except requests.exceptions.ConnectionError:
        print("Connection error to WAEC")
        return Response("Cannot connect to WAEC. Please try again later.", 503)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response(f"Bridge Error: {str(e)}", 500)

@app.route('/health', methods=['GET'])
def health_check():
    return Response("OK", 200)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

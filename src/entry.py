import re
import base64
from fastapi import FastAPI, Request, Response, Form
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "WAEC Bridge is live"}

@app.post("/check")
async def proxy_waec(request: Request):
    # Extract form data manually from the request
    form_data = await request.form()
    data = dict(form_data)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    payload = {
        **data,
        "ccandid": data.get("candid"),
        "cexamyear": data.get("examyear"),
        "referpage": "index.htm",
        "submit": "Submit"
    }

    # Using httpx.AsyncClient to handle the session automatically
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        try:
            # Step 1: Establish Session
            await client.get("https://ghana.waecdirect.org/index.htm", timeout=15.0)

            # Step 2: Post to get results
            waec_url = "https://ghana.waecdirect.org/results.asp"
            response = await client.post(waec_url, data=payload, timeout=45.0)
            html = response.text

            # Step 3: HARDEN THE QR CODE
            qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png)["\']', html)
            
            if qr_match:
                qr_relative_url = qr_match.group(1)
                qr_full_url = f"https://ghana.waecdirect.org/{qr_relative_url}"
                
                try:
                    # Download the actual image bytes
                    img_res = await client.get(qr_full_url, timeout=10.0)
                    if img_res.status_code == 200:
                        # Convert image to Base64
                        b64_img = base64.b64encode(img_res.content).decode('utf-8')
                        data_uri = f"data:image/png;base64,{b64_img}"
                        
                        # Replace dynamic URL with the permanent Base64 string
                        html = html.replace(qr_relative_url, data_uri)
                except Exception:
                    pass 

            return HTMLResponse(content=html)

        except Exception as e:
            return HTMLResponse(content=f"Bridge Error: {str(e)}", status_code=500)

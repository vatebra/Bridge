import re
import base64
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

@app.post("/check", response_class=HTMLResponse)
async def proxy_waec(
    candid: str = Form(...),
    examyear: str = Form(...),
    examtype: str = Form(...),
    pin: str = Form(...),
    serial: str = Form(...)
):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://ghana.waecdirect.org/index.htm",
        "Origin": "https://ghana.waecdirect.org"
    }

    payload = {
        "candid": candid,
        "examyear": examyear,
        "examtype": examtype,
        "pin": pin,
        "serial": serial,
        "ccandid": candid,
        "cexamyear": examyear,
        "referpage": "index.htm",
        "submit": "Submit"
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            await client.get("https://ghana.waecdirect.org/index.htm", headers=headers, timeout=15.0)
            waec_url = "https://ghana.waecdirect.org/results.asp"
            response = await client.post(waec_url, data=payload, headers=headers, timeout=30.0)
            html = response.text

            qr_match = re.search(r'src=["\'](qrcode2/[^"\']+\.png)["\']', html)
            if qr_match:
                qr_relative_url = qr_match.group(1)
                qr_full_url = f"https://ghana.waecdirect.org/{qr_relative_url}"
                
                img_res = await client.get(qr_full_url, headers=headers, timeout=10.0)
                if img_res.status_code == 200:
                    b64_img = base64.b64encode(img_res.content).decode('utf-8')
                    data_uri = f"data:image/png;base64,{b64_img}"
                    html = html.replace(qr_relative_url, data_uri)

            return HTMLResponse(content=html, status_code=200)

        except Exception as e:
            return HTMLResponse(content=f"Edge Bridge Error: {str(e)}", status_code=500)

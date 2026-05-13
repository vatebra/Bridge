import os
import asyncio
import re
from flask import Flask, request, Response
from flask_cors import CORS
from playwright.async_api import async_playwright

app = Flask(__name__)
CORS(app) 

async def fetch_waec_manual_stealth(payload):
    async with async_playwright() as p:
        # We manually pass flags to make the browser look "real"
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-blink-features=AutomationControlled" # This hides the "bot" flag
            ]
        )
        
        # We set a high-quality residential-style fingerprint
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()

        try:
            # Step 1: Visit home
            await page.goto("https://ghana.waecdirect.org/index.htm", wait_until="networkidle", timeout=60000)

            # Step 2: Fill form
            await page.fill('input[name="candid"]', payload.get("candid", ""))
            await page.select_option('select[name="examyear"]', payload.get("examyear", ""))
            await page.select_option('select[name="examtype"]', payload.get("examtype", "01"))
            await page.fill('input[name="serial"]', payload.get("serial", ""))
            await page.fill('input[name="pin"]', payload.get("pin", ""))

            # Step 3: Submit and wait
            await page.click('input[id="Submit"]')
            await page.wait_for_load_state("networkidle", timeout=60000)

            # Step 4: Inject Base URL so the link shows WAEC destination
            html = await page.content()
            base_tag = '<base href="https://ghana.waecdirect.org/">'
            
            # QR Code Fix
            qr_uri = await page.evaluate("""() => {
                const img = document.querySelector('img[src*="qrcode2"], img[src*="QRCode"]');
                if (!img) return null;
                const canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                return canvas.toDataURL('image/png');
            }""")

            if qr_uri:
                html = re.sub(r'src=["\'](qrcode2/[^"\']+\.png|QRCode\.ashx[^"\']+)["\']', f'src="{qr_uri}"', html)

            return base_tag + html
        finally:
            await browser.close()

@app.route('/check', methods=['POST'])
def proxy_waec():
    data = request.form.to_dict()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        html = loop.run_until_complete(fetch_waec_manual_stealth(data))
        loop.close()
        return Response(html, mimetype='text/html')
    except Exception as e:
        return f"Bridge Error: {type(e).__name__} - {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

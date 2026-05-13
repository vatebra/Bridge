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
        # Launch with flags for Render/Linux and hide automation
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-blink-features=AutomationControlled"
            ]
        )
        
        # Set a standard desktop fingerprint
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        
        page = await context.new_page()

        try:
            # Step 1: Visit home - Use 'domcontentloaded' to avoid waiting for slow tracking pixels
            print("Navigating to WAEC...")
            await page.goto("https://ghana.waecdirect.org/index.htm", wait_until="domcontentloaded", timeout=90000)

            # Step 2: Explicitly wait for the input field to be ready
            # This fixes the "Page.fill: Timeout" error
            print("Waiting for form fields...")
            await page.wait_for_selector('input[name="candid"]', state="visible", timeout=60000)

            # Step 3: Fill form
            await page.fill('input[name="candid"]', payload.get("candid", ""))
            await page.select_option('select[name="examyear"]', payload.get("examyear", ""))
            await page.select_option('select[name="examtype"]', payload.get("examtype", "01"))
            await page.fill('input[name="serial"]', payload.get("serial", ""))
            await page.fill('input[name="pin"]', payload.get("pin", ""))

            # Step 4: Submit and wait for the results page
            print("Submitting form...")
            await page.click('input[id="Submit"]')
            
            # Wait for the results content to load
            await page.wait_for_load_state("networkidle", timeout=90000)

            # Step 5: Inject Base URL and fix QR Code
            html = await page.content()
            base_tag = '<base href="https://ghana.waecdirect.org/">'
            
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
        except Exception as e:
            # Re-raise the exception to be caught by the Flask route
            raise e
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
        # Logs the specific error type (e.g., TimeoutError)
        return f"Bridge Error: {type(e).__name__} - {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

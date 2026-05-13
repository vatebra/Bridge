import os
import asyncio
import re
from flask import Flask, request, Response
from flask_cors import CORS
from playwright.async_api import async_playwright
import playwright_stealth

app = Flask(__name__)
# Enable CORS for your WordPress domain
CORS(app) 

async def fetch_waec_stealth(payload):
    async with async_playwright() as p:
        # Launch with required flags for Linux/Render environments
        browser = await p.chromium.launch(
            headless=True, 
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # FIX: Corrected Stealth Initialization
        # This checks if the specific function exists to avoid 'module object not callable'
        if hasattr(playwright_stealth, 'stealth_async'):
            await playwright_stealth.stealth_async(page)
        elif hasattr(playwright_stealth, 'stealth'):
            # Fallback for versions where 'stealth' works for both
            await playwright_stealth.stealth(page)

        try:
            # Step 1: Visit home to establish session cookies
            await page.goto("https://ghana.waecdirect.org/index.htm", wait_until="networkidle", timeout=60000)

            # Step 2: Fill the form using provided payload
            await page.fill('input[name="candid"]', payload.get("candid", ""))
            await page.select_option('select[name="examyear"]', payload.get("examyear", ""))
            await page.select_option('select[name="examtype"]', payload.get("examtype", "01"))
            await page.fill('input[name="serial"]', payload.get("serial", ""))
            await page.fill('input[name="pin"]', payload.get("pin", ""))

            # Step 3: Click Submit and wait for the result page to load
            await page.click('input[id="Submit"]')
            await page.wait_for_load_state("networkidle", timeout=60000)

            # Step 4: Handle QR Code (Convert to Base64 to make it permanent)
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

            html = await page.content()
            if qr_uri:
                # Replace the temporary WAEC image source with our permanent Base64 string
                html = re.sub(r'src=["\'](qrcode2/[^"\']+\.png|QRCode\.ashx[^"\']+)["\']', f'src="{qr_uri}"', html)

            return html
        except Exception as e:
            return f"Scraping Error: {str(e)}"
        finally:
            await browser.close()

@app.route('/check', methods=['POST'])
def proxy_waec():
    data = request.form.to_dict()
    try:
        # Create a fresh event loop for each request to prevent event loop issues in Flask
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        html = loop.run_until_complete(fetch_waec_stealth(data))
        loop.close()
        return Response(html, mimetype='text/html')
    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    # Render binds to the PORT environment variable (default 10000)
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

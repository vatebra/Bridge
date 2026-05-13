import os
import asyncio
import re
from flask import Flask, request, Response
from flask_cors import CORS
from playwright.async_api import async_playwright
import playwright_stealth

app = Flask(__name__)
# Replace '*' with your actual domain for better security
CORS(app) 

async def fetch_waec_stealth(payload):
    async with async_playwright() as p:
        # Added --no-sandbox and other flags necessary for Render/Linux
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
        
        # FIX: Bulletproof Stealth Initialization
        # Some versions use 'stealth_async', others use 'stealth'. This checks for both.
        if hasattr(playwright_stealth, 'stealth_async'):
            await playwright_stealth.stealth_async(page)
        else:
            from playwright_stealth import stealth
            await stealth(page)

        try:
            # Step 1: Visit home to get real session cookies
            await page.goto("https://ghana.waecdirect.org/index.htm", wait_until="networkidle", timeout=60000)

            # Step 2: Fill the form
            await page.fill('input[name="candid"]', payload.get("candid", ""))
            await page.select_option('select[name="examyear"]', payload.get("examyear", ""))
            await page.select_option('select[name="examtype"]', payload.get("examtype", "01"))
            await page.fill('input[name="serial"]', payload.get("serial", ""))
            await page.fill('input[name="pin"]', payload.get("pin", ""))

            # Step 3: Click and wait for results
            # Note: WAEC uses a traditional form submit, wait_for_load_state is appropriate
            await page.click('input[id="Submit"]')
            await page.wait_for_load_state("networkidle", timeout=60000)

            # Step 4: Handle QR Code (Convert to Base64)
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
                # Regex fix for multiple possible QR source patterns
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
        # Use a more robust loop handling for Flask
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        html = loop.run_until_complete(fetch_waec_stealth(data))
        loop.close()
        return Response(html, mimetype='text/html')
    except Exception as e:
        return f"Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

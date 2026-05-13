import os
import asyncio
from flask import Flask, request, Response
from flask_cors import CORS
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

app = Flask(__name__)
# Enable CORS so your WordPress site can access this bridge
CORS(app)

async def get_waec_result_stealth(payload):
    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Apply stealth fingerprints
        await stealth_async(page)

        try:
            # Step 1: Establish real session
            await page.goto("https://ghana.waecdirect.org/index.htm", wait_until="networkidle")

            # Step 2: Fill the form
            await page.fill('input[name="candid"]', payload.get("candid", ""))
            await page.select_option('select[name="examyear"]', payload.get("examyear", ""))
            await page.select_option('select[name="examtype"]', payload.get("examtype", "01"))
            await page.fill('input[name="serial"]', payload.get("serial", ""))
            await page.fill('input[name="pin"]', payload.get("pin", ""))

            # Step 3: Click and wait for navigation
            # This avoids the "Administrator Exception" by acting like a real click
            await asyncio.gather(
                page.click('input[id="Submit"]'),
                page.wait_for_load_state("networkidle")
            )

            # Step 4: Handle the QR Code inside the browser (Base64 conversion)
            # This ensures the QR code is permanent in your returned HTML
            qr_base64 = await page.evaluate("""() => {
                const img = document.querySelector('img[src*="qrcode2"], img[src*="QRCode"]');
                if (!img) return null;
                const canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                return canvas.toDataURL('image/png');
            }""")

            html_content = await page.content()

            if qr_base64:
                # Replace the dynamic link with the hardcoded Base64 image
                import re
                html_content = re.sub(r'src=["\'](qrcode2/[^"\']+\.png|QRCode\.ashx[^"\']+)["\']', f'src="{qr_base64}"', html_content)

            return html_content

        finally:
            await browser.close()

@app.route('/check', methods=['POST', 'OPTIONS'])
def proxy_waec():
    if request.method == 'OPTIONS':
        return Response(status=200)

    data = request.form.to_dict()
    try:
        # Run the async browser task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        html = loop.run_until_complete(get_waec_result_stealth(data))
        
        return Response(html, mimetype='text/html')
    except Exception as e:
        return f"Stealth Bridge Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

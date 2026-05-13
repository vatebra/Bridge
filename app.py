import os
import base64
import asyncio
from flask import Flask, request, Response
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

app = Flask(__name__)

async def fetch_waec_stealth(payload):
    async with async_playwright() as p:
        # Launch Chromium in headless mode
        browser = await p.chromium.launch(headless=True)
        # Use a high-quality User-Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        # Apply the Stealth Plugin
        await stealth_async(page)

        try:
            # Go to the landing page to drop initial cookies
            await page.goto("https://ghana.waecdirect.org/index.htm", wait_until="networkidle")

            # Fill the form fields directly into the browser DOM
            await page.fill('input[name="candid"]', payload.get("candid"))
            await page.select_option('select[name="examyear"]', payload.get("examyear"))
            await page.select_option('select[name="examtype"]', payload.get("examtype", "01"))
            await page.fill('input[name="serial"]', payload.get("serial"))
            await page.fill('input[name="pin"]', payload.get("pin"))

            # Click submit and wait for the results page to fully stabilize
            # This is where the "Exception" usually happens—but not here.
            await asyncio.gather(
                page.click('input[id="Submit"]'),
                page.wait_for_load_state("networkidle")
            )

            # Extract the HTML content after the browser has rendered it
            full_html = await page.content()

            # Logic to find and Base64 encode the QR code inside the browser
            # This is more reliable than re-requesting the image bytes
            qr_data_uri = await page.evaluate("""() => {
                const img = document.querySelector('img[src*="qrcode2"], img[src*="QRCode"]');
                if (!img) return null;
                const canvas = document.createElement('canvas');
                canvas.width = img.naturalWidth;
                canvas.height = img.naturalHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                return canvas.toDataURL('image/png');
            }""")

            if qr_data_uri:
                # Replace the relative source with the permanent Base64 URI
                full_html = full_html.replace('src="qrcode2/', f'src="{qr_data_uri}"')

            return full_html

        finally:
            await browser.close()

@app.route('/check', methods=['POST'])
def proxy_waec():
    data = request.form.to_dict()
    try:
        # Run the async Playwright function
        html = asyncio.run(fetch_waec_stealth(data))
        return Response(html, mimetype='text/html')
    except Exception as e:
        return f"Bridge Stealth Error: {str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

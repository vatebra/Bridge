import os
import asyncio
import re
from flask import Flask, request, Response
from flask_cors import CORS
from playwright.async_api import async_playwright

# SPECIFIC IMPORT: This avoids the "module" naming conflict
from playwright_stealth import stealth_async, stealth

app = Flask(__name__)
CORS(app) 

async def fetch_waec_stealth(payload):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # FINAL STEALTH FIX: Try one, then the other directly
        try:
            await stealth_async(page)
        except (NameError, TypeError, AttributeError):
            try:
                await stealth(page)
            except Exception as e:
                print(f"Stealth could not be applied: {e}")

        try:
            # Your navigation logic
            await page.goto("https://ghana.waecdirect.org/index.htm", wait_until="networkidle", timeout=60000)
            
            # Fill form...
            await page.fill('input[name="candid"]', payload.get("candid", ""))
            await page.select_option('select[name="examyear"]', payload.get("examyear", ""))
            await page.select_option('select[name="examtype"]', payload.get("examtype", "01"))
            await page.fill('input[name="serial"]', payload.get("serial", ""))
            await page.fill('input[name="pin"]', payload.get("pin", ""))

            await page.click('input[id="Submit"]')
            await page.wait_for_load_state("networkidle", timeout=60000)

            # QR Code and HTML logic...
            html = await page.content()
            return html
        finally:
            await browser.close()

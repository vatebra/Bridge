// src/index.js - Cloudflare Worker for WAEC Result Proxy

export default {
  async fetch(request) {
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    const url = new URL(request.url);
    
    // Handle root path - show status
    if (url.pathname === '/' && request.method === 'GET') {
      return new Response(JSON.stringify({ status: 'WAEC Proxy is running', endpoint: '/check' }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    // Only accept POST requests to /check
    if (url.pathname !== '/check') {
      return new Response(JSON.stringify({ error: 'Not found. Use POST /check' }), { 
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed. Use POST' }), { 
        status: 405,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    try {
      // Get form data from request
      const formData = await request.formData();
      const data = {};
      for (const [key, value] of formData.entries()) {
        data[key] = value;
      }

      // Build payload for WAEC
      const payload = {
        ...data,
        ccandid: data.candid || '',
        cexamyear: data.examyear || '',
        referpage: 'index.htm',
        submit: 'Submit'
      };

      // Convert payload to URL encoded string
      const encodedPayload = new URLSearchParams(payload).toString();

      // Headers for WAEC request
      const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://ghana.waecdirect.org/index.htm',
        'Origin': 'https://ghana.waecdirect.org',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded'
      };

      // Step 1: Visit index page to establish session and get cookies
      const indexResponse = await fetch('https://ghana.waecdirect.org/index.htm', {
        method: 'GET',
        headers: {
          'User-Agent': headers['User-Agent'],
          'Accept': headers['Accept']
        }
      });

      // Get cookies from index response
      let cookieString = '';
      const setCookie = indexResponse.headers.get('set-cookie');
      if (setCookie) {
        const cookieMatch = setCookie.match(/([^=]+)=([^;]+)/);
        if (cookieMatch) {
          cookieString = `${cookieMatch[1]}=${cookieMatch[2]}`;
        }
      }

      // Step 2: Post to results.asp with cookies
      const resultHeaders = { ...headers };
      if (cookieString) {
        resultHeaders['Cookie'] = cookieString;
      }

      const waecResponse = await fetch('https://ghana.waecdirect.org/results.asp', {
        method: 'POST',
        headers: resultHeaders,
        body: encodedPayload
      });

      let html = await waecResponse.text();

      // Step 3: Handle QR code - embed as base64
      const qrMatch = html.match(/src=["'](qrcode2\/[^"']+\.png)["']/);
      
      if (qrMatch) {
        const qrRelativeUrl = qrMatch[1];
        const qrFullUrl = `https://ghana.waecdirect.org/${qrRelativeUrl}`;
        
        try {
          const imgResponse = await fetch(qrFullUrl, {
            headers: {
              'User-Agent': headers['User-Agent'],
              'Referer': 'https://ghana.waecdirect.org/'
            }
          });
          
          if (imgResponse.ok) {
            const imgBuffer = await imgResponse.arrayBuffer();
            const base64Img = btoa(String.fromCharCode(...new Uint8Array(imgBuffer)));
            const dataUri = `data:image/png;base64,${base64Img}`;
            html = html.replace(qrRelativeUrl, dataUri);
          }
        } catch (err) {
          console.error('QR download error:', err);
        }
      }

      // Return the modified HTML
      return new Response(html, {
        status: 200,
        headers: {
          'Content-Type': 'text/html; charset=utf-8',
          'Access-Control-Allow-Origin': '*'
        }
      });

    } catch (error) {
      return new Response(JSON.stringify({ error: `Bridge Error: ${error.message}` }), { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};

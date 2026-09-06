"""
One-click Public Tunnel for KisanGo WhatsApp Bot using Cloudflare.
Automatically downloads cloudflared and establishes a secure public tunnel to localhost:8000.

Usage:
    python tunnel.py
"""

import os
import sys
import time
import urllib.request
import subprocess
import re
import threading

CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
CLOUDFLARED_EXE = "cloudflared.exe"

def download_cloudflared():
    if not os.path.exists(CLOUDFLARED_EXE):
        print("[INFO] Cloudflare tunnel executable not found.")
        print("[INFO] Downloading cloudflared.exe (this may take a moment)...")
        try:
            urllib.request.urlretrieve(CLOUDFLARED_URL, CLOUDFLARED_EXE)
            print("[INFO] Download complete!")
        except Exception as e:
            print(f"❌ Error downloading cloudflared: {e}")
            sys.exit(1)

def start_tunnel():
    print("\n" + "=" * 60)
    print(" 🌐 KisanGo WhatsApp Bot - Cloudflare Public Tunnel")
    print("=" * 60 + "\n")

    download_cloudflared()

    print("[INFO] Starting tunnel to http://localhost:8000 ...\n")
    
    # Launch cloudflared
    # Cloudflare logs to stderr
    process = subprocess.Popen(
        [CLOUDFLARED_EXE, "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    url_found = False

    def read_stderr():
        nonlocal url_found
        url_pattern = re.compile(r"(https://[a-zA-Z0-9-]+\.trycloudflare\.com)")
        
        while True:
            line = process.stderr.readline()
            if not line:
                break
            
            # Print important status logs if needed, but mostly we look for the URL
            match = url_pattern.search(line)
            if match and not url_found:
                url_found = True
                public_url = match.group(1)
                
                print("\n" + "✅ " * 15)
                print("🎉 YOUR PUBLIC LINK IS ACTIVE!")
                print("✅ " * 15 + "\n")
                print(f"👉 Base URL: {public_url}\n")
                print("📋 COPY AND PASTE INTO YOUR WHATSAPP SETTINGS:")
                print("─" * 60)
                print("1️⃣ For Meta WhatsApp Cloud API (developers.facebook.com):")
                print(f"   Callback URL : {public_url}/webhook")
                print(f"   Verify Token : agridoc_verify_token")
                print("─" * 60)
                print("\n⏳ Tunnel is running! (Press Ctrl + C to stop)\n")

    # Start a thread to read stderr so it doesn't block
    t = threading.Thread(target=read_stderr, daemon=True)
    t.start()

    try:
        # Keep main thread alive
        while process.poll() is None:
            time.sleep(1)
        
        if process.returncode != 0:
            print(f"\n❌ Cloudflare tunnel exited with code {process.returncode}")
            
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down tunnel...")
        process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    start_tunnel()

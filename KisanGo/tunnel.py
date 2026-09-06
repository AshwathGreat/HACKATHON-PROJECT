"""
One-click Public Tunnel for KisanGo WhatsApp Bot.
Uses pyngrok to safely establish an SSL public tunnel to localhost:8000.

Usage:
    python tunnel.py
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

try:
    from pyngrok import ngrok, conf
except ImportError:
    print("Installing pyngrok...")
    os.system("pip install pyngrok")
    from pyngrok import ngrok, conf

def start_tunnel():
    print("\n" + "=" * 60)
    print(" 🌐 KisanGo WhatsApp Bot - One-Click Public Tunnel")
    print("=" * 60 + "\n")

    # Check if authtoken is configured
    token = os.getenv("NGROK_AUTHTOKEN", "").strip()
    
    # Try reading token from user if not set
    config = conf.get_default()
    if not config.auth_token and not token:
        print("💡 Enter your free ngrok authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken")
        user_token = input("Paste token here (or press Enter if already configured): ").strip()
        if user_token:
            ngrok.set_auth_token(user_token)
    elif token:
        ngrok.set_auth_token(token)

    try:
        print("[INFO] Starting tunnel to http://localhost:8000 ...")
        tunnel = ngrok.connect(8000, bind_tls=True)
        public_url = tunnel.public_url

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

        # Keep running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Shutting down tunnel...")
        ngrok.disconnect(public_url)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting tunnel: {e}")
        print("\n💡 Tip: Get your free authtoken at https://dashboard.ngrok.com/get-started/your-authtoken and run again.")

if __name__ == "__main__":
    start_tunnel()

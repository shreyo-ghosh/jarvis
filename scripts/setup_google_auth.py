#!/usr/bin/env python3
"""
setup_google_auth.py — Run once on your laptop to get Gmail + Calendar OAuth token.
Then the token is pushed to SSM automatically by deploy.sh (if GMAIL_TOKEN_JSON is set in .env).

Usage:
  pip install google-auth-oauthlib
  python scripts/setup_google_auth.py
"""

import json
import os
import sys

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/calendar"
]


def main():
    print("\n=== Google Auth Setup for Jarvis ===\n")

    creds_path = (
        input("Path to credentials.json [./credentials.json]: ").strip()
        or "./credentials.json"
    )

    if not os.path.exists(creds_path):
        print(f"\n❌ File not found: {creds_path}")
        print("\nTo get credentials.json:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. New Project → 'JarvisAgent'")
        print("  3. Enable: Gmail API + Google Calendar API")
        print("  4. APIs & Services → OAuth consent screen → External")
        print("     Add your Gmail as a test user")
        print("     Add scopes: Gmail + Calendar")
        print("  5. Credentials → OAuth 2.0 Client ID → Desktop app → Download JSON")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("❌ Run: pip install google-auth-oauthlib")
        sys.exit(1)

    print("\nOpening browser for Google login...")
    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0)

    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes)
    }
    token_json = json.dumps(token_data)

    print("\n✅ Authentication successful!\n")
    print("=" * 70)
    print("Add this to your .env file as GMAIL_TOKEN_JSON=<value>")
    print("Then re-run ./scripts/deploy.sh — it will push it to SSM automatically.")
    print("=" * 70)
    print(f'\nGMAIL_TOKEN_JSON={token_json}\n')

    # Optionally write to .env automatically
    write = input("Auto-append to .env? [y/N]: ").strip().lower()
    if write == "y":
        with open(".env", "a") as f:
            f.write(f'\nGMAIL_TOKEN_JSON={token_json}\n')
        print("✅ Written to .env")
    else:
        print("Copy the GMAIL_TOKEN_JSON line above into your .env manually.")


if __name__ == "__main__":
    main()

"""
scripts/setup_google_auth.py
Run this ONCE locally to generate a Google OAuth token for Gmail + Calendar access.
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "google_token.json")


def main():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"credentials.json not found at {CREDENTIALS_PATH}")
        print("Download it from Google Cloud Console -> APIs & Services -> Credentials")
        return
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())
    print(f"Token saved to {TOKEN_PATH}")
    print("Next: run ./scripts/push_google_secrets.sh then cd terraform && terraform apply")


if __name__ == "__main__":
    main()

"""Decode CI signing material without printing any secret values."""
import base64
import binascii
import os
from pathlib import Path
import re


def main():
    names = (
        "ANDROID_KEYSTORE_BASE64", "ANDROID_KEYSTORE_PATH",
        "ANDROID_KEYSTORE_PASSWORD", "ANDROID_KEY_ALIAS", "ANDROID_KEY_PASSWORD",
        "ANDROID_SIGNING_CERT_SHA256",
    )
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise SystemExit("Release signing configuration missing: " + ", ".join(missing))
    fingerprint = os.environ["ANDROID_SIGNING_CERT_SHA256"].replace(":", "").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", fingerprint):
        raise SystemExit("ANDROID_SIGNING_CERT_SHA256 must be the public certificate SHA-256.")
    try:
        data = base64.b64decode("".join(os.environ["ANDROID_KEYSTORE_BASE64"].split()), validate=True)
    except (ValueError, binascii.Error):
        raise SystemExit("ANDROID_KEYSTORE_BASE64 is not valid Base64.") from None
    if not data:
        raise SystemExit("Decoded release keystore is empty.")
    path = Path(os.environ["ANDROID_KEYSTORE_PATH"])
    with path.open("xb") as handle:
        handle.write(data)
    path.chmod(0o600)
    print("Release signing material prepared; no secret values logged.")


if __name__ == "__main__":
    main()

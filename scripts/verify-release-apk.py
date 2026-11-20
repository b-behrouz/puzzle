"""Verify the signature, pinned certificate, identity and bundled assets before upload."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    apk, certificate, output = map(Path, sys.argv[1:])
    tools = Path(os.environ["ANDROID_HOME"]) / "build-tools" / "35.0.0"
    suffix = ".bat" if os.name == "nt" else ""
    verification = run(str(tools / ("apksigner" + suffix)), "verify", "--verbose", "--print-certs", str(apk))
    signers = re.findall(r"^Signer #\d+ certificate SHA-256 digest: ([a-fA-F0-9]{64})$", verification, re.M)
    expected = os.environ["ANDROID_SIGNING_CERT_SHA256"].replace(":", "").strip().lower()
    original = hashlib.sha256(certificate.read_bytes()).hexdigest()
    require(original == expected, "Keystore certificate does not match the owner's pinned SHA-256.")
    require([value.lower() for value in signers] == [expected], "APK signer does not match the original release certificate.")
    require("Android Debug" not in verification, "Debug certificate is forbidden for release.")
    aapt = str(tools / ("aapt.exe" if os.name == "nt" else "aapt"))
    badging = run(aapt, "dump", "badging", str(apk))
    require("package: name='com.example.puzzlepreview'" in badging, "Unexpected package identifier.")
    require("application-debuggable" not in badging, "Release APK must not be debuggable.")
    with zipfile.ZipFile(apk) as archive:
        files = archive.namelist()
        forbidden = [name for name in files if name.lower().endswith((".jks", ".keystore", ".p12", ".pfx", ".key"))
                     or Path(name).name.lower() in ("keystore.properties", "signing.properties", ".env")]
        require(not forbidden, "Signing or secret files found inside APK.")
        require(archive.read("assets/public/index.html") == Path("puzzle-fantasy-mobile.html").read_bytes(),
                "Bundled game differs from the original web game.")
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    (output / "app-release.apk.sha256").write_text(f"{digest}  app-release.apk\n", encoding="utf-8")
    metadata = "\n".join(line for line in badging.splitlines() if line.startswith(
        ("package:", "sdkVersion:", "targetSdkVersion:", "application-label:", "uses-permission:")))
    report = (f"Release signature verified.\nCertificate SHA-256: {expected}\nAPK SHA-256: {digest}\n"
              f"{metadata}\nOriginal game assets: byte-for-byte match.\n"
              "No signing files found in APK.\nDevice installation and offline gameplay: NOT tested by this workflow.\n\n"
              + verification)
    (output / "release-verification.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()

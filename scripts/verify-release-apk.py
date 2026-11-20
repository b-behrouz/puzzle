"""Verify the signature, pinned certificate, identity and bundled assets before upload."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile


def run(*args):
    return subprocess.check_output(args, text=True, encoding="utf-8", stderr=subprocess.STDOUT)


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
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
    identity = json.loads(Path("capacitor.config.json").read_text(encoding="utf-8"))
    gradle = Path("android/app/build.gradle").read_text(encoding="utf-8")
    package = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging, re.M)
    require(package is not None and package[1] == identity["appId"], "Unexpected package identifier.")
    version_code = re.search(r"\bversionCode\s+(\d+)", gradle)
    version_name = re.search(r'\bversionName\s+"([^"]+)"', gradle)
    require(version_code is not None and version_name is not None, "Could not read the expected Android version.")
    require(package[2] == version_code[1] and package[3] == version_name[1], "APK version differs from Gradle configuration.")
    label = re.search(r"^application-label:'([^']+)'$", badging, re.M)
    require(label is not None and label[1] == identity["appName"], "APK display name differs from the approved name.")
    require("application-debuggable" not in badging, "Release APK must not be debuggable.")
    secret_needles = []
    for name in ("ANDROID_KEYSTORE_PASSWORD", "ANDROID_KEY_PASSWORD", "ANDROID_KEYSTORE_BASE64"):
        value = os.environ.get(name)
        if value:
            secret_needles.extend((value.encode("utf-8"), value.encode("utf-16le")))
    if os.environ.get("ANDROID_KEYSTORE_BASE64"):
        secret_needles.append(base64.b64decode("".join(os.environ["ANDROID_KEYSTORE_BASE64"].split()), validate=True))
    with zipfile.ZipFile(apk) as archive:
        files = archive.namelist()
        forbidden = [name for name in files if name.lower().endswith((".jks", ".keystore", ".p12", ".pfx", ".key"))
                     or Path(name).name.lower() in ("keystore.properties", "signing.properties", ".env")]
        require(not forbidden, "Signing or secret files found inside APK.")
        for name in files:
            contents = archive.read(name)
            require(not any(needle and needle in contents for needle in secret_needles),
                    "Signing secret material found inside APK.")
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

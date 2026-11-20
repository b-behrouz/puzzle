"""Exercise fail-closed release gates using fixtures, never a real private key."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = load_script('prepare-release-signing')
verify = load_script('verify-release-apk')


class SigningGates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cert = self.root / 'certificate.der'
        self.cert.write_bytes(b'public certificate fixture, not a private key')
        self.pin = hashlib.sha256(self.cert.read_bytes()).hexdigest()
        self.apk = self.root / 'app-release.apk'
        self.output = self.root / 'public'
        self.game = b'<html>embedded fixture</html>'
        self.key = self.root / 'fixture.jks'
        self.env = {
            'ANDROID_HOME': str(self.root),
            'ANDROID_KEYSTORE_PATH': str(self.key),
            'ANDROID_KEYSTORE_BASE64': base64.b64encode(b'not a real key').decode(),
            'ANDROID_KEYSTORE_PASSWORD': 'test fixture only',
            'ANDROID_KEY_ALIAS': 'fixture',
            'ANDROID_KEY_PASSWORD': 'test fixture only',
            'ANDROID_SIGNING_CERT_SHA256': self.pin,
        }
        self.signature = f'Verifies\nSigner #1 certificate SHA-256 digest: {self.pin}\n'
        self.badging = "package: name='ir.bbehrouz.tikechin' versionCode='1' versionName='1.0'\nsdkVersion:'24'\ntargetSdkVersion:'36'\napplication-label:'تکه‌چین'\n"

    def write_apk(self, game=None, extra=None, extra_data=b'forbidden fixture'):
        with zipfile.ZipFile(self.apk, 'w') as archive:
            archive.writestr('assets/public/index.html', self.game if game is None else game)
            if extra:
                archive.writestr(extra, extra_data)

    def verify_fixture(self, signature=None, badging=None):
        (self.root / 'puzzle-fantasy-mobile.html').write_bytes(self.game)
        (self.root / 'capacitor.config.json').write_text(json.dumps({
            'appId': 'ir.bbehrouz.tikechin', 'appName': 'تکه‌چین'
        }), encoding='utf-8')
        (self.root / 'android' / 'app').mkdir(parents=True, exist_ok=True)
        (self.root / 'android' / 'app' / 'build.gradle').write_text(
            'versionCode 1\nversionName "1.0"\n', encoding='utf-8')
        previous = Path.cwd()
        os.chdir(self.root)
        try:
            with patch.dict(os.environ, self.env, clear=True), patch.object(sys, 'argv', [
                    'verify', str(self.apk), str(self.cert), str(self.output)]), patch.object(
                    verify, 'run', side_effect=[self.signature if signature is None else signature,
                                                self.badging if badging is None else badging]):
                verify.main()
        finally:
            os.chdir(previous)

    def test_missing_secret_stops_before_writing_key(self):
        del self.env['ANDROID_KEY_PASSWORD']
        with patch.dict(os.environ, self.env, clear=True), self.assertRaises(SystemExit):
            prepare.main()
        self.assertFalse(self.key.exists())

    def test_invalid_base64_stops(self):
        self.env['ANDROID_KEYSTORE_BASE64'] = 'invalid!'
        with patch.dict(os.environ, self.env, clear=True), self.assertRaises(SystemExit):
            prepare.main()
        self.assertFalse(self.key.exists())

    def test_missing_or_invalid_pin_stops(self):
        self.env['ANDROID_SIGNING_CERT_SHA256'] = 'invalid'
        with patch.dict(os.environ, self.env, clear=True), self.assertRaises(SystemExit):
            prepare.main()
        self.assertFalse(self.key.exists())

    def test_existing_key_is_never_overwritten(self):
        self.key.write_bytes(b'existing')
        with patch.dict(os.environ, self.env, clear=True), self.assertRaises(FileExistsError):
            prepare.main()
        self.assertEqual(self.key.read_bytes(), b'existing')

    def test_wrong_owner_pin_stops(self):
        self.write_apk()
        self.env['ANDROID_SIGNING_CERT_SHA256'] = '0' * 64
        with self.assertRaises(SystemExit):
            self.verify_fixture()
        self.assertFalse(self.output.exists())

    def test_wrong_apk_signer_stops(self):
        self.write_apk()
        with self.assertRaises(SystemExit):
            self.verify_fixture(signature='Signer #1 certificate SHA-256 digest: ' + '0' * 64)
        self.assertFalse(self.output.exists())

    def test_additional_signer_stops(self):
        self.write_apk()
        with self.assertRaises(SystemExit):
            self.verify_fixture(signature=self.signature + f'Signer #2 certificate SHA-256 digest: {self.pin}\n')

    def test_debug_certificate_stops(self):
        self.write_apk()
        with self.assertRaises(SystemExit):
            self.verify_fixture(signature=self.signature + 'Signer #1 certificate DN: CN=Android Debug\n')

    def test_debuggable_apk_stops(self):
        self.write_apk()
        with self.assertRaises(SystemExit):
            self.verify_fixture(badging=self.badging + 'application-debuggable\n')

    def test_wrong_package_stops(self):
        self.write_apk()
        with self.assertRaises(SystemExit):
            self.verify_fixture(badging=self.badging.replace('ir.bbehrouz.tikechin', 'com.other.app'))

    def test_wrong_app_name_stops(self):
        self.write_apk()
        with self.assertRaises(SystemExit):
            self.verify_fixture(badging=self.badging.replace("application-label:'تکه‌چین'", "application-label:'Other'"))

    def test_wrong_version_stops(self):
        self.write_apk()
        with self.assertRaises(SystemExit):
            self.verify_fixture(badging=self.badging.replace("versionCode='1'", "versionCode='2'"))

    def test_changed_game_stops(self):
        self.write_apk(game=b'changed game')
        with self.assertRaises(SystemExit):
            self.verify_fixture()
        self.assertFalse(self.output.exists())

    def test_private_key_in_apk_stops(self):
        self.write_apk(extra='assets/tikechin-release.jks')
        with self.assertRaises(SystemExit):
            self.verify_fixture()
        self.assertFalse(self.output.exists())

    def test_password_under_an_innocent_filename_stops(self):
        self.write_apk(extra='assets/settings.txt', extra_data=self.env['ANDROID_KEY_PASSWORD'].encode('utf-8'))
        with self.assertRaises(SystemExit):
            self.verify_fixture()
        self.assertFalse(self.output.exists())

    def test_disguised_keystore_bytes_stop(self):
        self.write_apk(extra='assets/settings.bin', extra_data=base64.b64decode(self.env['ANDROID_KEYSTORE_BASE64']))
        with self.assertRaises(SystemExit):
            self.verify_fixture()
        self.assertFalse(self.output.exists())

    def test_verified_fixture_writes_public_hash_only(self):
        self.write_apk()
        self.verify_fixture()
        expected = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        self.assertIn(expected, (self.output / 'app-release.apk.sha256').read_text())
        self.assertEqual({p.name for p in self.output.iterdir()}, {'app-release.apk.sha256', 'release-verification.txt'})


if __name__ == '__main__':
    unittest.main()

from pathlib import Path
import re


def test_setup_nginx_script_creates_fallback_certificate_when_missing():
    script = Path("deploy/setup-nginx.sh").read_text()

    assert "openssl req -x509" in script
    variables = dict(re.findall(r'^([A-Z_]+)="([^"\n]*)"', script, re.MULTILINE))
    cert_path = variables["CERT_PATH"].replace("${CERT_DIR}", variables["CERT_DIR"])
    key_path = variables["KEY_PATH"].replace("${CERT_DIR}", variables["CERT_DIR"])
    assert cert_path == "/etc/letsencrypt/live/singularitynear.com/fullchain.pem"
    assert key_path == "/etc/letsencrypt/live/singularitynear.com/privkey.pem"

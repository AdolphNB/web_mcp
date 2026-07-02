from pathlib import Path


def test_setup_nginx_script_creates_fallback_certificate_when_missing():
    script = Path("deploy/setup-nginx.sh").read_text()

    assert "openssl req -x509" in script
    assert "/etc/letsencrypt/live/singularitynear.com/fullchain.pem" in script
    assert "/etc/letsencrypt/live/singularitynear.com/privkey.pem" in script

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


def test_deploy_never_executes_dotenv_and_keeps_lockfile():
    script = Path("deploy.sh").read_text()
    assert not re.search(r"^\s*(source|\.)\s+['\"]?\.env", script, re.MULTILINE)
    assert "--exclude='uv.lock'" not in script
    assert "sync --locked --no-dev" in script
    assert script.index("--check-certificate") < script.index('supervisorctl stop "$PROJECT_NAME"')
    assert script.index('supervisorctl stop "$PROJECT_NAME"') < script.index("scripts/prepare_sqlite.py")
    assert script.index("scripts/prepare_sqlite.py") < script.index("scripts/migrate.py migrate")
    assert 'chown -R $DEPLOY_USER:$DEPLOY_USER "$PROJECT_DIR"' not in script


def test_self_signed_certificate_requires_explicit_opt_in():
    script = Path("deploy/setup-nginx.sh").read_text()
    guard = script.index('${ALLOW_SELF_SIGNED_CERT:-0}')
    assert guard < script.index("openssl req -x509")
    assert 'exit 1' in script[guard:script.index("openssl req -x509")]
    assert "-verify_hostname singularitynear.com" in script
    assert "-verify_hostname www.singularitynear.com" in script

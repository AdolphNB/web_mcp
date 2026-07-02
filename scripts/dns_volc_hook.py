#!/usr/bin/env python3
"""
acme.sh DNS API hook for 火山引擎 (Volcengine) DNS
Usage:
  python3 dns_volc_hook.py add   <domain> <txt_value>
  python3 dns_volc_hook.py remove <domain> <txt_value>

Env vars required:
  VOLC_ACCESS_KEY  - 火山引擎 Access Key ID
  VOLC_SECRET_KEY  - 火山引擎 Secret Access Key
"""

import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime
from urllib.parse import quote

import httpx

# Volcengine DNS API settings
SERVICE = "dns"
REGION = "cn-beijing"
HOST = "open.volcengineapi.com"
ENDPOINT = f"https://{HOST}"
API_VERSION = "2018-08-01"


def sign_request(method: str, uri: str, query: dict, body: str,
                 access_key: str, secret_key: str) -> dict:
    """Create Volcengine API v4 signature headers."""
    now = datetime.utcnow()
    date_short = now.strftime("%Y%m%d")
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")

    # Build query string
    query_parts = sorted(query.items(), key=lambda x: x[0])
    query_string = "&".join(f"{quote(k)}={quote(str(v))}" for k, v in query_parts) if query_parts else ""

    # Build canonical request
    payload_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    headers_to_sign = {
        "host": HOST,
        "x-content-sha256": payload_hash,
        "x-date": timestamp,
    }
    signed_headers = ";".join(sorted(headers_to_sign.keys()))
    canonical_headers = "".join(f"{k}:{v}\n" for k, v in sorted(headers_to_sign.items()))
    canonical_request = f"{method}\n{uri}\n{query_string}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

    # Build string to sign
    credential_scope = f"{date_short}/{REGION}/{SERVICE}/request"
    hashed_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = f"HMAC-SHA256\n{timestamp}\n{credential_scope}\n{hashed_request}"

    # Calculate signature
    def hmac_sha256(key, data):
        return hmac.new(key, data.encode("utf-8"), hashlib.sha256).digest()

    k_date = hmac_sha256(secret_key.encode("utf-8"), date_short)
    k_region = hmac_sha256(k_date, REGION)
    k_service = hmac_sha256(k_region, SERVICE)
    k_signing = hmac_sha256(k_service, "request")
    signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization = (
        f"HMAC-SHA256 Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    return {
        "Host": HOST,
        "X-Date": timestamp,
        "X-Content-Sha256": payload_hash,
        "Authorization": authorization,
        "Content-Type": "application/json",
    }


def api_call(action: str, params: dict, access_key: str, secret_key: str) -> dict:
    """Make a Volcengine API call."""
    method = "GET" if action in ("ListRecords", "ListZones") else "POST"
    query = {
        "Action": action,
        "Version": API_VERSION,
    }
    # For GET requests, merge params into query string
    if method == "GET":
        query.update(params)
        body = ""
    else:
        body = json.dumps(params)

    headers = sign_request(method, "/", query, body, access_key, secret_key)

    url = ENDPOINT + "/?" + "&".join(f"{quote(str(k))}={quote(str(v))}" for k, v in query.items())

    r = httpx.request(
        method=method,
        url=url,
        headers=headers,
        content=body if method == "POST" else None,
    )
    result = r.json()
    if "ResponseMetadata" in result and "Error" in result["ResponseMetadata"]:
        err = result["ResponseMetadata"]["Error"]
        raise RuntimeError(f"API Error: {err.get('Code', 'Unknown')} - {err.get('Message', 'Unknown')}")
    return result


def get_zone_id(domain: str, access_key: str, secret_key: str) -> str:
    """Find zone ID by domain name."""
    root_domain = ".".join(domain.split(".")[-2:])
    page = 1
    while True:
        result = api_call("ListZones", {"PageNumber": page, "PageSize": 100}, access_key, secret_key)
        zones = result.get("Result", {}).get("Zones", [])
        for zone in zones:
            if zone["ZoneName"] == root_domain:
                return zone["ZID"]
        total = result.get("Result", {}).get("TotalCount", 0)
        if page * 100 >= total:
            break
        page += 1
    raise RuntimeError(f"Zone not found for domain: {root_domain}")


def list_records(zid: str, host: str, record_type: str, access_key: str, secret_key: str) -> list:
    """List DNS records matching host and type."""
    records = []
    page = 1
    while True:
        result = api_call("ListRecords", {
            "ZID": int(zid),
            "PageNumber": page,
            "PageSize": 100,
            "SearchMode": "EXPECT_VAL",
            "Host": host,
            "Type": record_type,
        }, access_key, secret_key)
        records.extend(result.get("Result", {}).get("Records", []))
        total = result.get("Result", {}).get("TotalCount", 0)
        if page * 100 >= total:
            break
        page += 1
    return records


def add_record(zid: str, host: str, value: str, access_key: str, secret_key: str):
    """Add a TXT record (or update if exists)."""
    existing = list_records(zid, host, "TXT", access_key, secret_key)
    for rec in existing:
        if rec["Value"] == value:
            print(f"TXT record already exists: {host} -> {value}")
            return
        # Update existing record with different value
        api_call("UpdateRecord", {
            "RecordID": rec["RecordID"],
            "Host": host,
            "Type": "TXT",
            "Value": value,
            "TTL": 600,
            "Line": "default",
        }, access_key, secret_key)
        print(f"TXT record updated: {host} -> {value}")
        return

    # Create new record
    api_call("CreateRecord", {
        "ZID": int(zid),
        "Host": host,
        "Type": "TXT",
        "Value": value,
        "TTL": 600,
        "Line": "default",
    }, access_key, secret_key)
    print(f"TXT record created: {host} -> {value}")


def remove_record(zid: str, host: str, value: str, access_key: str, secret_key: str):
    """Remove a TXT record."""
    existing = list_records(zid, host, "TXT", access_key, secret_key)
    for rec in existing:
        if rec["Value"] == value:
            api_call("DeleteRecord", {"RecordID": rec["RecordID"]}, access_key, secret_key)
            print(f"TXT record deleted: {host}")
            return
    print(f"TXT record not found for deletion: {host}")


def wait_dns_propagation(host: str, value: str, timeout: int = 120):
    """Wait for DNS propagation."""
    import subprocess
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["dig", "+short", "TXT", host],
                capture_output=True, text=True
            )
            if value in result.stdout:
                print(f"DNS propagation confirmed for {host}")
                return True
        except Exception:
            pass
        time.sleep(5)
    print(f"Warning: DNS propagation timeout for {host}, continuing anyway...")
    return False


def main():
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} add|remove <full_acme_domain> <txt_value>")
        sys.exit(1)

    action = sys.argv[1]
    full_domain = sys.argv[2]  # e.g. _acme-challenge.singularitynear.com
    txt_value = sys.argv[3]

    access_key = os.environ.get("VOLC_ACCESS_KEY")
    secret_key = os.environ.get("VOLC_SECRET_KEY")

    if not access_key or not secret_key:
        print("Error: Set VOLC_ACCESS_KEY and VOLC_SECRET_KEY environment variables")
        sys.exit(1)

    # Extract root domain (last 2 parts) for zone lookup
    parts = full_domain.split(".")
    root_domain = ".".join(parts[-2:])  # e.g. singularitynear.com
    # Extract host prefix for DNS record (everything except root domain)
    host_prefix = ".".join(parts[:-2])  # e.g. _acme-challenge

    zid = get_zone_id(root_domain, access_key, secret_key)
    print(f"Zone ID for {root_domain}: {zid}")

    if action == "add":
        add_record(zid, host_prefix, txt_value, access_key, secret_key)
        wait_dns_propagation(full_domain, txt_value)
    elif action == "remove":
        remove_record(zid, host_prefix, txt_value, access_key, secret_key)
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)


if __name__ == "__main__":
    main()

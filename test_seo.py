"""
Simple test for SEO endpoints
"""
import requests
import sys

base_url = "http://localhost:8000"

tests = [
    ("GET", "/sitemap.xml", "application/xml"),
    ("GET", "/robots.txt", "text/plain"),
]

print("Testing SEO endpoints...")
print("=" * 50)

for method, endpoint, expected_type in tests:
    url = f"{base_url}{endpoint}"
    print(f"\n{method} {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code == 200:
            print(f"  ✓ Success")
            
            content_type = response.headers.get('Content-Type', '')
            if expected_type in content_type:
                print(f"  ✓ Correct content type")
            else:
                print(f"  ✗ Wrong content type (expected: {expected_type})")
        else:
            print(f"  ✗ Failed")
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Connection refused (server not running)")
        print(f"\n  Start server with: uvicorn main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n" + "=" * 50)

#!/usr/bin/env python3
"""Quick smoke test for Foxit PDF Services + eSign APIs."""

import os
import sys
import asyncio
import httpx

# --- Config ---
PDF_BASE = "https://na1.fusion.foxit.com/pdf-services"
ESIGN_BASE = "https://na1.foxitesign.foxit.com"

PDF_CLIENT_ID = os.environ.get("FOXIT_CLOUD_API_CLIENT_ID", "")
PDF_CLIENT_SECRET = os.environ.get("FOXIT_CLOUD_API_CLIENT_SECRET", "")
ESIGN_CLIENT_ID = os.environ.get("FOXIT_ESIGN_CLIENT_ID", "")
ESIGN_CLIENT_SECRET = os.environ.get("FOXIT_ESIGN_CLIENT_SECRET", "")


async def test_pdf_services():
    """Test PDF Services API reachability and auth."""
    print("=" * 50)
    print("  FOXIT PDF SERVICES TEST")
    print("=" * 50)

    if not PDF_CLIENT_ID or not PDF_CLIENT_SECRET:
        print("  SKIP: FOXIT_CLOUD_API_CLIENT_ID/SECRET not set")
        print("  Register at: https://developer-api.foxit.com")
        return False

    print(f"  Client ID: {PDF_CLIENT_ID[:8]}...")
    print(f"  Base URL:  {PDF_BASE}")

    # Test 1: Upload a minimal PDF
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n190\n%%EOF"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test upload
        print("\n  [1] Upload document...")
        try:
            resp = await client.post(
                f"{PDF_BASE}/api/documents/upload",
                params={"client_id": PDF_CLIENT_ID, "client_secret": PDF_CLIENT_SECRET},
                files={"file": ("test.pdf", minimal_pdf, "application/pdf")},
            )
            print(f"      Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                doc_id = data.get("documentId", "")
                print(f"      Document ID: {doc_id}")
                print("      PASS: Upload works")
            else:
                print(f"      Response: {resp.text[:200]}")
                print("      FAIL: Upload returned non-200")
                return False
        except Exception as e:
            print(f"      ERROR: {e}")
            return False

        # Test merge (needs 2 docs, so upload a second one)
        print("\n  [2] Upload second document for merge test...")
        try:
            resp2 = await client.post(
                f"{PDF_BASE}/api/documents/upload",
                params={"client_id": PDF_CLIENT_ID, "client_secret": PDF_CLIENT_SECRET},
                files={"file": ("test2.pdf", minimal_pdf, "application/pdf")},
            )
            if resp2.status_code == 200:
                doc_id2 = resp2.json().get("documentId", "")
                print(f"      Document ID: {doc_id2}")
            else:
                doc_id2 = None
                print(f"      Upload2 failed: {resp2.status_code}")
        except Exception:
            doc_id2 = None

        if doc_id and doc_id2:
            print("\n  [3] Merge documents...")
            try:
                resp3 = await client.post(
                    f"{PDF_BASE}/api/documents/enhance/pdf-combine",
                    params={"client_id": PDF_CLIENT_ID, "client_secret": PDF_CLIENT_SECRET},
                    json={
                        "documents": [
                            {"documentId": doc_id},
                            {"documentId": doc_id2},
                        ]
                    },
                )
                print(f"      Status: {resp3.status_code}")
                if resp3.status_code == 200:
                    task_id = resp3.json().get("taskId", "")
                    print(f"      Task ID: {task_id}")
                    print("      PASS: Merge submitted")
                else:
                    print(f"      Response: {resp3.text[:200]}")
            except Exception as e:
                print(f"      ERROR: {e}")

        # Test compress
        if doc_id:
            print("\n  [4] Compress document...")
            try:
                resp4 = await client.post(
                    f"{PDF_BASE}/api/documents/modify/pdf-compress",
                    params={"client_id": PDF_CLIENT_ID, "client_secret": PDF_CLIENT_SECRET},
                    json={"documentId": doc_id, "compressionLevel": "medium"},
                )
                print(f"      Status: {resp4.status_code}")
                if resp4.status_code == 200:
                    print(f"      Task ID: {resp4.json().get('taskId', '')}")
                    print("      PASS: Compress submitted")
                else:
                    print(f"      Response: {resp4.text[:200]}")
            except Exception as e:
                print(f"      ERROR: {e}")

    print("\n  PDF Services: DONE")
    return True


async def test_esign():
    """Test eSign API reachability and auth."""
    print("\n" + "=" * 50)
    print("  FOXIT ESIGN TEST")
    print("=" * 50)

    if not ESIGN_CLIENT_ID or not ESIGN_CLIENT_SECRET:
        print("  SKIP: FOXIT_ESIGN_CLIENT_ID/SECRET not set")
        print("  Register at: https://developer-api.foxit.com")
        return False

    print(f"  Client ID: {ESIGN_CLIENT_ID[:8]}...")
    print(f"  Base URL:  {ESIGN_BASE}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test OAuth2 token
        print("\n  [1] Get OAuth2 token...")
        try:
            resp = await client.post(
                f"{ESIGN_BASE}/api/oauth2/access_token",
                data={
                    "client_id": ESIGN_CLIENT_ID,
                    "client_secret": ESIGN_CLIENT_SECRET,
                    "grant_type": "client_credentials",
                    "scope": "read-write",
                },
            )
            print(f"      Status: {resp.status_code}")
            if resp.status_code == 200:
                token = resp.json().get("access_token", "")
                print(f"      Token: {token[:20]}..." if token else "      Token: none")
                print("      PASS: OAuth2 works")
            else:
                print(f"      Response: {resp.text[:200]}")
                print("      FAIL: OAuth2 returned non-200")
                return False
        except Exception as e:
            print(f"      ERROR: {e}")
            return False

    print("\n  eSign: DONE")
    return True


async def main():
    print("Foxit API Smoke Test")
    print(f"PDF Services: {PDF_BASE}")
    print(f"eSign: {ESIGN_BASE}")
    print()

    pdf_ok = await test_pdf_services()
    esign_ok = await test_esign()

    print("\n" + "=" * 50)
    print("  SUMMARY")
    print("=" * 50)
    print(f"  PDF Services: {'PASS' if pdf_ok else 'SKIP/FAIL'}")
    print(f"  eSign:        {'PASS' if esign_ok else 'SKIP/FAIL'}")
    print()

    if not pdf_ok and not esign_ok:
        print("  No API keys set. Register at:")
        print("  https://developer-api.foxit.com")
        print()
        print("  Developer tier: 500 credits/year FREE")
        print("  Failed requests do NOT consume credits")


if __name__ == "__main__":
    asyncio.run(main())

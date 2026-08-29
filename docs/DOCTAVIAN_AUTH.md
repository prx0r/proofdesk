# Doctavian Auth Cheat Sheet

**Goal:** a Bearer token with the scopes needed for document generation delivery.
**Why the portal token fails:** it authenticates fine, but Storage delivery copies output via your Google account and needs Drive scope — the portal login doesn't grant it.

---

## Option 1 — One-click link (fastest)

Open this in your browser, log in with `tradesprior@gmail.com`, approve ALL permissions (including Google Drive):

```
https://demo.api.doctavian.com/public/v1/auth/google/authorize?client_id=11e71170-3499-43f3-b878-7df343f43d37&redirect_uri=https%3A%2F%2Foauth.pstmn.io%2Fv1%2Fcallback&response_type=code&scope=api%3A%2F%2F40728276-52a7-4932-bf32-76737f1fd01a%2F.default+offline_access+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive.file&code_challenge=XMPRLDAUYTvzowIJKcrAx5qZmyemEU3eckOA94nseqE&code_challenge_method=S256
```

After approving you land on a page that may show an error — that's fine.
**Copy the full URL from the address bar** (starts `https://oauth.pstmn.io/v1/callback?...`) and paste it back to me.

⚠️ The `code_challenge` is tied to a verifier saved at `/tmp/opencode/pkce_verifier.txt` — don't regenerate or this exact URL stops working.

## Option 2 — Postman app

1. Install https://www.postman.com/downloads/
2. Import the collection JSON from Doctavian's email (or `/tmp/opencode/doctavian-demo.postman_collection.json`)
3. Collection → **Authorization** tab → **Get New Access Token** → sign in with Google → approve all
4. Copy the access token

## Option 3 — Email Doctavian

To: hello@doctavian.com — mention Team Trades, demo env, and that generate fails with `COPY_FILE_GOOGLEDRIVE_FAILED / insufficient authentication scopes`; ask for a service token.

---

## Headers for every API call (once you have the token)

```http
Authorization: Bearer <NEW_TOKEN>
X-Api-Key: edff22dbcc244bd0b709d7e632ce12e5
Content-Type: application/json
```

Optional but harmless:
```http
X-Subscription-Key: badc239580c949cd8e9f14946fa20cef
X-Origin: https://demo.portal.doctavian.com
```

**Do NOT send** `X-Client-Authorization` / `X-Service-Authorization` — those are for Salesforce/OneDrive integrations; sending a wrong-format one causes `X_CLIENT_AUTH_ERROR`.

## Where the token goes

Paste it here and I'll set:
```
DOCTAVIAN_BEARER_TOKEN=<token>   # in .env.keys + export
```

Then generation runs real end-to-end: upload template → upload data → generate → download PDF.

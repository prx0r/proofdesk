# Nutrient DWS — Error Handling (Complete Reference)

Source: https://www.nutrient.io/guides/dws-data-extraction/errors/

---

## Error Response Format

```json
{
  "status": 400,
  "requestId": "req_err_001",
  "errorMessage": "The request is malformed",
  "errorDetails": {
    "source": "request",
    "code": "invalid_request",
    "failingPaths": [{ "path": "$.file", "details": "unsupported format" }]
  }
}
```

## HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad request | Check schema, file format, parameters |
| 401 | Unauthorized | Check Bearer token format (`pdf_live_...`) |
| 402 | Payment required | Insufficient credits |
| 408 | Request timeout | Retry |
| 413 | Payload too large | Max 150 MB per request |
| 422 | Unprocessable entity | URL rejected or couldn't download |
| 429 | Rate limit | Exponential backoff |
| 500 | Server error | Retry, include requestId in support contact |
| 503 | Service unavailable | Retry later |

## Common Errors

### Schema validation (400)
```json
{
  "status": 400,
  "errorDetails": {
    "failingPaths": [{ "path": "$.schema", "details": "root type must be object" }]
  }
}
```
Causes: missing schema, wrong root type, unsupported keywords (`$ref`, `allOf`, etc.)

### URL rejected (422)
```json
{
  "status": 422,
  "errorDetails": {
    "failingPaths": [{ "path": "$.url", "details": "URL is not allowed" }]
  }
}
```
Limits: 50 MB download, 30s timeout. Upload directly for larger files.

### Insufficient credits (402)
Different shape for extract vs parse:
```json
{ "error": "insufficient_credits", "message": "...", "credits_available": "0" }
```
Branch on HTTP 402, not body shape.

## Python Error Handling

```python
response = requests.post(...)
result = response.json()

if result.get("status") != 200:
    print(f"Error {result['status']}: {result['errorMessage']}")
    print(f"Request ID: {result['requestId']}")
    if "errorDetails" in result:
        for path in result["errorDetails"].get("failingPaths", []):
            print(f"  {path['path']}: {path['details']}")
```

## Support

Include `requestId` when contacting support: support@nutrient.io

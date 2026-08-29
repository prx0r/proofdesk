#!/bin/bash
export FOXIT_CLOUD_API_HOST="https://na1.fusion.foxit.com/pdf-services"
export FOXIT_CLOUD_API_CLIENT_ID="foxit_NMF8DBAuqsOSvgCd"
export FOXIT_CLOUD_API_CLIENT_SECRET="emQSc6Pb0OTwmMZKI135f8Ki0NqW4a9U"
exec /home/box/Documents/patala/.venv/bin/python3 -c "
import sys
sys.path.insert(0, '/home/box/Documents/patala/proofdesk/vendor/foxit-pdf-api-mcp-server/python/foxit-pdf-api-mcp-server/src')
from foxit_pdf_api_mcp_server.main import main
sys.argv = ['foxit-pdf-api-mcp-server']
main()"

#!/bin/bash
# Test script for MCP JWT authentication

echo "Testing MCP JWT Authentication"
echo "==============================="
echo ""
echo "1. First, copy the MCP Default JWT token from the UI"
echo "   (Go to https://control.thinkube.com/tokens and click Show on MCP Default)"
echo ""
echo "2. Paste the JWT token here (it should start with 'eyJ'):"
read -p "JWT Token: " JWT_TOKEN
echo ""

# Test basic connectivity
echo "Testing JWT authentication with MCP SSE endpoint..."
RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $JWT_TOKEN" https://control.thinkube.com/api/mcp/sse 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ JWT authentication successful! (HTTP $HTTP_CODE)"
else
    echo "❌ JWT authentication failed (HTTP $HTTP_CODE)"
    echo "Response: $BODY"
fi

echo ""
echo "Testing JWT with services endpoint..."
RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $JWT_TOKEN" https://control.thinkube.com/api/v1/services 2>&1)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Services endpoint accessible with JWT! (HTTP $HTTP_CODE)"
else
    echo "❌ Services endpoint failed (HTTP $HTTP_CODE)"
fi

echo ""
echo "To use this JWT with MCP/Claude, update .mcp.json:"
echo "  \"Authorization\": \"Bearer $JWT_TOKEN\""
echo ""
echo "Would you like to update .mcp.json now? (y/n)"
read -p "Update? " UPDATE

if [ "$UPDATE" = "y" ]; then
    # Backup current config
    cp .mcp.json .mcp.json.backup

    # Update with JWT
    cat > .mcp.json <<EOF
{
    "mcpServers": {
        "thinkube-control": {
            "type": "http",
            "url": "https://control.thinkube.com/api/mcp/mcp/",
            "headers": {
                "Authorization": "Bearer $JWT_TOKEN"
            }
        }
    }
}
EOF
    echo "✅ Updated .mcp.json with JWT token"
    echo "   Backup saved as .mcp.json.backup"
fi
#!/usr/bin/env bash
# verify-hardening.sh — MagicLamp PR #33 post-deploy verification helper.
# Usage: bash verify-hardening.sh VPS_IP magiclamp.ae
# Exit codes: 0 = pass, 1 = warnings, 2 = fail.

set -u

VPS_IP="${1:-VPS_IP}"
DOMAIN="${2:-magiclamp.ae}"
FAILS=0
WARNS=0

pass(){ echo "[PASS] $1"; }
fail(){ echo "[FAIL] $1"; FAILS=$((FAILS+1)); }
warn(){ echo "[WARN] $1"; WARNS=$((WARNS+1)); }
info(){ echo "[INFO] $1"; }

info "MagicLamp PR #33 verification: VPS_IP=$VPS_IP DOMAIN=$DOMAIN"

info "1/8 Check published container ports"
PUBLISHED=$(docker ps --format '{{.Names}}|{{.Ports}}' | grep -E '0\.0\.0\.0:|:::' || true)
NON_PROXY=$(echo "$PUBLISHED" | grep -viE 'nginx|proxy' || true)
if [ -z "$NON_PROXY" ]; then
  pass "Only reverse proxy appears to publish host ports."
else
  fail "A non-proxy container appears to publish host ports:"
  echo "$NON_PROXY"
fi

info "2/8 Check local model runtime is not public"
CODE=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "http://$VPS_IP:11434" 2>/dev/null || echo '000')
if [ "$CODE" = "000" ]; then
  pass "Local model runtime is not reachable on the public address."
else
  fail "Local model runtime responded publicly with HTTP $CODE."
fi

info "3/8 Check production docs route"
CODE=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/docs" 2>/dev/null || echo '000')
if [ "$CODE" = "404" ] || [ "$CODE" = "403" ]; then
  pass "Docs route is blocked/protected."
else
  fail "Docs route returned HTTP $CODE; expected blocked/protected."
fi

info "4/8 Check OpenAPI route"
CODE=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/openapi.json" 2>/dev/null || echo '000')
if [ "$CODE" = "404" ] || [ "$CODE" = "403" ]; then
  pass "OpenAPI route is blocked/protected."
else
  fail "OpenAPI route returned HTTP $CODE; expected blocked/protected."
fi

info "5/8 Check CORS rejects untrusted origin"
HDR=$(curl -sS --max-time 10 -I -H 'Origin: https://example.invalid' "https://$DOMAIN/api/health" 2>/dev/null | grep -i '^access-control-allow-origin:' || true)
if [ -z "$HDR" ]; then
  pass "No CORS allow-origin header for untrusted origin."
elif echo "$HDR" | grep -qiE 'allow-origin:\s*\*|example\.invalid'; then
  fail "CORS allowed untrusted origin: $HDR"
else
  pass "CORS header does not allow the untrusted origin: $HDR"
fi

info "6/8 Check N8N is not public"
CODE1=$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "http://$VPS_IP:5678" 2>/dev/null || echo '000')
CODE2=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/n8n/" 2>/dev/null || echo '000')
if [ "$CODE1" = "000" ] && { [ "$CODE2" = "404" ] || [ "$CODE2" = "403" ] || [ "$CODE2" = "000" ]; }; then
  pass "N8N is not publicly reachable through common paths."
else
  fail "N8N may be public: direct=$CODE1 route=$CODE2"
fi

info "7/8 Check health endpoint"
CODE=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/health" 2>/dev/null || echo '000')
if [ "$CODE" = "200" ]; then
  pass "Health endpoint returns 200."
else
  warn "Health endpoint returned HTTP $CODE. Check route/domain/TLS before merge."
fi

info "8/8 Check compose static risk markers"
if docker compose config >/tmp/magiclamp-compose-check.txt 2>/tmp/magiclamp-compose-check.err; then
  if grep -q 'network_mode: host' /tmp/magiclamp-compose-check.txt; then
    fail "Compose config contains host networking."
  else
    pass "Compose config generated and host networking not detected."
  fi
else
  fail "docker compose config failed."
  cat /tmp/magiclamp-compose-check.err || true
fi

if [ "$FAILS" -gt 0 ]; then
  echo "RESULT=RED failures=$FAILS warnings=$WARNS"
  exit 2
fi

if [ "$WARNS" -gt 0 ]; then
  echo "RESULT=AMBER warnings=$WARNS"
  exit 1
fi

echo "RESULT=GREEN"
exit 0

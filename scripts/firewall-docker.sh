#!/usr/bin/env bash
# =============================================================================
# Stratum AI - Restrict Docker-published ports to Cloudflare
# =============================================================================
# ufw does NOT protect Docker-published ports. Docker writes its own iptables
# rules into the DOCKER chain in the nat/filter tables, and those are consulted
# before ufw's INPUT rules — so `ufw deny` on 443 has no effect while
# `ports: - "443:443"` is in the compose file. The origin stays open to the
# whole internet and ufw reports "active", which is the worst combination:
# protection that is believed rather than real.
#
# DOCKER-USER is the chain Docker guarantees to evaluate first and never
# rewrites, so it is the supported place to filter container traffic.
#
# Idempotent: flushes its own rules before re-adding.
#
#   ./scripts/firewall-docker.sh            # apply
#   ./scripts/firewall-docker.sh --status   # show current rules
# =============================================================================

set -euo pipefail

WAN_IF="${WAN_IF:-$(ip route get 1.1.1.1 2>/dev/null | awk '{print $5; exit}')}"
[ -n "$WAN_IF" ] || { echo "ERROR: could not determine WAN interface" >&2; exit 1; }

if [ "${1:-}" = "--status" ]; then
    echo "== DOCKER-USER (IPv4) =="; iptables  -L DOCKER-USER -n --line-numbers
    echo "== DOCKER-USER (IPv6) =="; ip6tables -L DOCKER-USER -n --line-numbers
    exit 0
fi

echo "WAN interface: $WAN_IF"

v4="$(curl -fsSL https://www.cloudflare.com/ips-v4)"
v6="$(curl -fsSL https://www.cloudflare.com/ips-v6)"
count=$(printf '%s\n%s\n' "$v4" "$v6" | grep -c '/' || echo 0)

# A truncated download must never be applied: an empty allow-list plus a DROP
# rule takes the site off the internet.
if [ "$count" -lt 10 ]; then
    echo "ERROR: only $count Cloudflare ranges fetched — refusing to apply" >&2
    exit 1
fi

iptables  -F DOCKER-USER 2>/dev/null || true
ip6tables -F DOCKER-USER 2>/dev/null || true

# Rules are appended in order: established first (so replies to our own
# outbound traffic survive), then the Cloudflare allow-list, then a final DROP
# for 80/443 only. Other published ports are untouched by this script.
iptables  -A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
ip6tables -A DOCKER-USER -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN

for cidr in $v4; do
    iptables -A DOCKER-USER -i "$WAN_IF" -s "$cidr" -p tcp -m multiport --dports 80,443 -j RETURN
done
for cidr in $v6; do
    ip6tables -A DOCKER-USER -i "$WAN_IF" -s "$cidr" -p tcp -m multiport --dports 80,443 -j RETURN
done

iptables  -A DOCKER-USER -i "$WAN_IF" -p tcp -m multiport --dports 80,443 -j DROP
ip6tables -A DOCKER-USER -i "$WAN_IF" -p tcp -m multiport --dports 80,443 -j DROP

iptables  -A DOCKER-USER -j RETURN
ip6tables -A DOCKER-USER -j RETURN

echo "applied: $count Cloudflare ranges may reach 80/443; all other sources dropped"

# iptables rules do not survive a reboot on their own.
if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save >/dev/null 2>&1 && echo "saved via netfilter-persistent"
else
    echo "NOTE: install iptables-persistent so these survive a reboot:"
    echo "      apt-get install -y iptables-persistent"
fi

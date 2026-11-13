"""Web server with its own domain (docs/DEPLOY.md): public URL reporting + guards on the deploy files, so a later edit
cannot publish the API port or open more than the TradingView webhook without the edge login."""

from pathlib import Path

import yaml

from app.api.routes import tunnel_view

ROOT = Path(__file__).resolve().parents[3]


class _Tunnel:
    class state:  # mimics tunnel.TunnelManager.state
        @staticmethod
        def as_dict():
            return {"mode": "ngrok", "public_url": "https://me.ngrok-free.app", "permanent": True, "error": ""}


def test_tunnel_view_prefers_a_running_tunnel_then_the_server_domain():
    assert tunnel_view(_Tunnel(), "https://app.example.com")["mode"] == "ngrok"
    assert tunnel_view(None, "https://app.example.com/") == {
        "mode": "server",
        "public_url": "https://app.example.com",
        "permanent": True,
        "error": "",
    }
    assert tunnel_view(None, "")["mode"] == "none"
    assert tunnel_view(None, "http://app.example.com")["mode"] == "none"  # TradingView needs HTTPS


def test_only_caddy_publishes_ports_and_the_api_trusts_only_that_proxy():
    c = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text())
    s = c["services"]
    assert [n for n, v in s.items() if v.get("ports")] == ["caddy"]
    assert sorted(s["caddy"]["ports"]) == ["443:443", "443:443/udp", "80:80"]
    env = s["api"]["environment"]
    assert env["PAYTIENCE_COOKIE_SECURE"] == "true" and env["PAYTIENCE_FORWARDED_ALLOW_IPS"] == "*"
    assert env["PAYTIENCE_ALLOW_LIVE"].endswith(":-false}")  # PAPER unless the user opts in (§1.5)


def test_caddy_opens_only_the_webhook_post_without_the_edge_login():
    cf = (ROOT / "docker" / "Caddyfile").read_text()
    lines = [x.strip() for x in cf.splitlines() if x.strip() and not x.strip().startswith("#")]
    handles = [x for x in lines if x.startswith("handle")]
    assert handles == ["handle @webhook {", "handle {"]
    webhook = cf[cf.index("@webhook {") : cf.index("handle @webhook")]
    assert "method POST" in webhook and "path /api/webhook/tradingview" in webhook
    catch_all = cf[cf.index("\thandle {") :]
    assert catch_all.index("basic_auth") < catch_all.index("reverse_proxy")


def test_image_trusts_forwarded_headers_only_when_told():
    df = (ROOT / "docker" / "api.Dockerfile").read_text()
    assert '--forwarded-allow-ips \\"${PAYTIENCE_FORWARDED_ALLOW_IPS:-127.0.0.1}\\"' in df

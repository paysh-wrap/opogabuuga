from tests.conftest import PASSWORD


def test_health_public(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["app"] == "paytience" and r.json()["mode"] == "PAPER"
    assert r.headers["x-frame-options"] == "DENY"


def test_protected_routes_need_login(client):
    for path in ("/api/rules", "/api/connections", "/api/auth/me"):
        assert client.get(path).status_code == 401


def test_successful_logins_never_lock_out(client):
    for _ in range(8):
        assert client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD}).status_code == 200


def test_login_bad_password_and_rate_limit(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "admin", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD}).status_code == 429


def test_login_sets_httponly_cookie_and_csrf_enforced(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    assert r.status_code == 200
    assert "httponly" in r.headers.get_list("set-cookie")[0].lower()
    assert client.get("/api/auth/me").json()["username"] == "admin"
    # mutating request without CSRF header → 403
    assert client.put("/api/connections/discord", json={"values": {}}).status_code == 403
    client.headers["x-csrf-token"] = "wrong"
    assert client.put("/api/connections/discord", json={"values": {}}).status_code == 403


def test_rules_endpoint(authed):
    body = authed.get("/api/rules").json()
    assert body["rules"]["internal"]["windows"][0] == ["06:45", "11:30"]
    assert "eval.lock_trigger" in body["verify_paths"]
    assert body["rules"]["instruments"]["MNQ"]["tick"] == "0.25"  # Decimal serialized exactly


def test_logout(authed):
    assert authed.post("/api/auth/logout").status_code == 200
    assert authed.get("/api/auth/me").status_code == 401


def test_audit_records_login(client):
    from app.audit import verify_chain
    from app.models import AuditLog

    client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
    client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
    with client.app.state.sessionmaker() as s:
        actions = [a.action for a in s.query(AuditLog).order_by(AuditLog.id)]
        assert actions == ["auth.login_failed", "auth.login"]
        assert verify_chain(s) == (True, None)

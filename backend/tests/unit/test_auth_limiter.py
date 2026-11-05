from app.auth import RateLimiter


def test_window_slides():
    r = RateLimiter(2, 60)
    r.fail("ip", now=0)
    r.fail("ip", now=10)
    assert r.blocked("ip", now=30)
    assert not r.blocked("ip", now=61)  # first failure expired
    assert not r.blocked("other", now=30)  # per-client

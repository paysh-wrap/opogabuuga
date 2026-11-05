from app.monitor.reconcile import reconcile


def test_reconcile_kinds():
    exp = {("A", "MNQ"): 2, ("B", "MNQ"): 1}
    act = {("A", "MNQ"): 2, ("B", "MNQ"): 3, ("C", "MES"): -1}
    assert [(m.account, m.kind) for m in reconcile(exp, act)] == [("B", "SIZE"), ("C", "UNEXPECTED")]
    assert [m.kind for m in reconcile({("A", "MNQ"): 1}, {})] == ["MISSING"]
    assert reconcile(exp, exp) == []

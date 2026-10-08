from agent_day4.allocation import _asserted, _FEE_FREE

def test_acknowledged_fee_instead_of_waiver_is_not_denial():
    assert not list(_asserted(_FEE_FREE, "Pay the fixed exit fee instead of a waived fee"))
    assert list(_asserted(_FEE_FREE, "The exit fee is waived"))
    assert list(_asserted(_FEE_FREE, "No exit fee is payable instead of normal payment"))


def test_eliminated_dependency_with_payable_exit_fee_is_not_avoided_termination():
    from agent_day4.business import _AVOID_EXIT
    assert not _AVOID_EXIT.search("Dependence is eliminated and an exit fee applies")
    assert _AVOID_EXIT.search("This avoids termination of supplier A")
    assert list(_asserted(_FEE_FREE, "This avoids the exit fee"))

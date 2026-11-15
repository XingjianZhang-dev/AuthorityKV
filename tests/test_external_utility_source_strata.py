from scripts.summarize_external_utility_runs import source_hashes_are_valid


def test_registered_multiple_source_strata_are_accepted_exactly() -> None:
    assert source_hashes_are_valid(["b", "a", "a"], ["a", "b"])


def test_unregistered_or_missing_source_strata_fail() -> None:
    assert not source_hashes_are_valid(["a", "b"], [])
    assert not source_hashes_are_valid(["a"], ["a", "b"])
    assert not source_hashes_are_valid(["a", "b", "c"], ["a", "b"])


def test_legacy_single_source_rule_remains_fail_closed() -> None:
    assert source_hashes_are_valid(["a", "a"], [])
    assert not source_hashes_are_valid([], [])

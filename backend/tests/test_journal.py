from app.engine.journal import Journal


def test_replay_nested_machine_changes_and_removed_dictionary_key():
    journal = Journal()
    original = {"current_week": 1, "started": True, "kpis": {"produced": 0},
                "production_lines": [{"id": "LINE-01", "machines": [{"id": "L1-M1", "state": "marche"}]}],
                "packing_queue": {"SKU-01": 3}}
    journal.capture(original, "decision")
    import copy
    changed = copy.deepcopy(original)
    changed["current_week"] = 2
    changed["production_lines"][0]["machines"][0]["state"] = "panne"
    changed["packing_queue"] = {}
    journal.capture(changed)
    assert journal.state == changed
    assert any(event["element"] == "L1-M1" and event["new_state"] == "panne" for event in journal.events)
    unchanged = list(journal.events)
    journal.capture(changed)
    assert journal.events == unchanged
    assert original["production_lines"][0]["machines"][0]["state"] == "marche"


def test_identical_decisions_produce_identical_journal_without_wallclock_time():
    a, b = Journal(), Journal()
    for journal in (a, b):
        journal.capture({"current_week": 1, "started": True, "kpis": {"produced": 0}}, "decision")
        journal.refusal(1, "stock.minimum", 10, "Interdit")
    assert a.events == b.events

from app.engine.journal import Journal
from app.engine.kpis import customer_indicators


def test_customer_service_uses_delivered_orders_and_retains_pruned_history():
    journal = Journal()
    journal.capture({"current_week": 1, "started": True, "kpis": {"otif": 94}, "customer_orders": []}, "decision")
    assert customer_indicators(journal)["otif"] is None
    delivered = {"id": "CC-1", "status": "livrée", "quantity": 100, "on_time": True}
    late = {"id": "CC-2", "status": "en retard", "quantity": 100, "on_time": None}
    journal.capture({"current_week": 2, "started": True, "kpis": {"otif": 50}, "customer_orders": [delivered, late]})
    rates = customer_indicators(journal)
    assert rates["otif"] == 100  # open late orders are not in the OTIF denominator
    assert rates["service_rate"] == 50
    journal.capture({"current_week": 3, "started": True, "kpis": {"otif": 0}, "customer_orders": []})
    rates = customer_indicators(journal)
    assert rates["otif"] == 100
    assert rates["service_rate"] == 50
    assert rates["history"][-1]["otif"] == 100

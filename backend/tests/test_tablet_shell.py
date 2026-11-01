from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_tablet_shell_is_served_without_replacing_the_game():
    response = client.get("/tablet")
    assert response.status_code == 200
    assert "G-MIX — Tablette de pilotage" in response.text
    assert '/static/tablet/app.js' in response.text
    assert client.get("/tablet/").status_code == 200
    assert client.get("/").status_code == 200


def test_tablet_assets_and_legacy_api_remain_available():
    for asset in ("styles.css", "app.js", "mock-api.js"):
        response = client.get(f"/static/tablet/{asset}")
        assert response.status_code == 200
        assert response.content
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/state").status_code == 200


def test_permission_notification_uses_the_required_four_second_delay():
    script = client.get("/static/tablet/app.js").text
    assert 'role="alert"' in client.get("/tablet").text
    assert "window.setTimeout(() => { toast.hidden = true; }, 4000)" in script

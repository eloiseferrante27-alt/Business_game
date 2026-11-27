"""`.env.example` ne contient aucune clé réelle : les variables de secret y sont vides ou factices."""

from pathlib import Path

ENV = Path(__file__).resolve().parents[2] / ".env.example"
SECRETS = ("OPENAI_API_KEY", "OLLAMA_API_KEY")


def test_env_example_secrets_are_empty() -> None:
    values = dict(
        line.split("=", 1) for line in ENV.read_text(encoding="utf-8").splitlines() if "=" in line and line[0] != "#"
    )
    for name in SECRETS:
        assert values.get(name, "").strip() == "", f"{name} doit rester vide dans .env.example"
    assert values["LLM_PROVIDER"].strip() in ("", "ollama")  # défaut : tout en local

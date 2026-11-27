"""Relecture T4 (ADR 0013) : spec ancienne repassée par recompile_layout, plafond du décor, budget de génération."""

import copy
import json
import time

import pytest

from gmix.game import layout
from gmix.game.generation import autopilot_check, generate
from gmix.game.spec import GameParams, SimSpec, load_pack

PACK = load_pack("usine")


def _spec(seed: int, suppliers: int | None = None) -> dict:
    params = GameParams(pack="usine", theme="industrie", modules=["pilotage", "production", "maintenance"], seed=seed,
                        weeks=6, suppliers=suppliers)  # fmt: skip
    return generate(params)


@pytest.mark.parametrize("seed", range(1, 25))
def test_a_published_spec_without_decor_survives_recompile_with_a_bigger_hall(seed: int) -> None:
    spec = _spec(seed, suppliers=8)
    old = copy.deepcopy(spec)
    old["world"].pop("decor")
    old["world"]["size"] = list(PACK["world"]["size"])  # spec d'avant T4 : hall du pack, pas de décor
    new, rejected = layout.recompile_layout(old, PACK, [])
    assert rejected == []
    SimSpec.model_validate(new)
    assert layout.check_placement(new, PACK) == []
    assert len(new["world"]["decor"]["items"]) <= 45
    assert new["world"]["size"] == spec["world"]["size"]  # même graine : même hall


def test_a_recompiled_old_spec_stays_playable() -> None:
    spec = _spec(3, suppliers=8)
    spec["world"].pop("decor")
    spec["world"]["size"] = list(PACK["world"]["size"])
    new, _ = layout.recompile_layout(spec, PACK, [])
    assert autopilot_check(new)["playable"]


def test_decor_never_exceeds_the_cap_and_a_spec_without_seed_gets_the_pack_hall() -> None:
    for seed in range(40):
        spec = _spec(seed % 12 + 1, suppliers=8)
        spec = spec | {"seed": seed}
        assert len(layout.place_world(spec, PACK)["world"]["decor"]["items"]) <= 45
    no_seed = {k: v for k, v in _spec(1).items() if k != "seed"}
    assert layout.place_world(no_seed, PACK)["world"]["size"] == list(PACK["world"]["size"])


def test_a_decor_over_the_cap_is_refused_by_the_contract() -> None:
    spec = _spec(1)
    item = spec["world"]["decor"]["items"][0]
    spec["world"]["decor"]["items"] = [item] * 46
    with pytest.raises(ValueError):
        SimSpec.model_validate(spec)


def test_generation_time_is_measured_and_bounded() -> None:
    _spec(1, suppliers=8)  # chauffe : chargement des packs
    start = time.perf_counter()
    spec = _spec(2, suppliers=8)
    elapsed = time.perf_counter() - start
    print(f"generation 8 fournisseurs : {elapsed:.2f} s")  # noqa: T201
    assert elapsed < 5 and json.dumps(spec)

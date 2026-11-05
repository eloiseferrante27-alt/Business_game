"""python -m app.generator <domaine> --seed N [--products K] [--machines M] [--id ID] [--check] (depuis backend/)."""

import argparse
import sys

from . import WorldError, generate, list_domains, save, validate
from ..scenario import load_scenario


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m app.generator", description="Génère un monde de business game jouable.")
    parser.add_argument("domain", nargs="?", default="supply_chain", choices=list_domains())
    parser.add_argument("--seed", type=int, default=0, help="graine : même graine => même monde")
    parser.add_argument("--products", type=int, help="nombre de produits (sinon tiré dans le pack)")
    parser.add_argument("--machines", type=int, help="machines par ligne (sinon tiré dans le pack)")
    parser.add_argument("--id", help="identifiant du scénario (défaut : <domaine>-<graine>)")
    parser.add_argument("--check", action="store_true", help="générer et valider sans écrire de fichier")
    parser.add_argument("--validate", metavar="SCENARIO", help="valider un scénario existant de backend/app/scenarios/")
    args = parser.parse_args(argv)

    if args.validate:
        issues = validate(load_scenario(args.validate))
        print("\n".join(issues) or f"{args.validate} : valide.")
        return 1 if issues else 0

    params = {key: value for key in ("products", "machines") if (value := getattr(args, key)) is not None}
    try:
        world = generate(args.domain, args.seed, args.id, **params)
    except (WorldError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"{world['name']}\n{world['description']}")
    if not args.check:
        print(f"Écrit : {save(world)}  -> jouable avec scenario_id = {world['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

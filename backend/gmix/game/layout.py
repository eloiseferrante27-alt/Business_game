"""Placeur déterministe de l'usine sur grilles (ADR 0009).

Fonctions pures : une spec (dict) et un pack en entrée, un dictionnaire en sortie, aucun hasard, aucune entrée-sortie.
Trois niveaux de grille : la carte (cellules de 60 m, sites et routes), le site (0,5 m) et le bloc (grille locale
d'un département, motifs `edge`, `rows`, `line`, `single`). Repères : nord = -z, sud = +z, est = +x, ouest = -x ;
rotation 0 = face au sud (modèles Godot orientés +Z), 90 = est, 180 = nord, 270 = ouest.

Dans un bloc, on raisonne dans un repère abstrait (U le long du mur du fond, V du fond vers l'allée de devant) que
`_Frame.rect` ramène aux colonnes et lignes réelles.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from functools import lru_cache
from typing import Any

from gmix.assets_catalog import AssetCatalog, load_assets_catalog

ROT = {"sud": 0, "est": 90, "nord": 180, "ouest": 270}
UPLUS = {"sud": "est", "nord": "est", "est": "sud", "ouest": "sud"}  # sens des U croissants selon l'avant
FRONT_VEC = {"sud": (0, 1), "nord": (0, -1), "est": (1, 0), "ouest": (-1, 0)}  # (colonne, ligne)
ROT_VEC = {0: (0, 1), 90: (1, 0), 180: (0, -1), 270: (-1, 0)}
EDITABLE_ROLES = {"decor", "affichage"}
FIXED_MOVE = {"porte", "batiment"}  # fixés par le réseau : ni déplacés ni retirés
MAX_EDITS = 200
# Bande de part et d'autre d'un chemin protégé, où un poste exige une barrière. Valeur de calibrage (statut
# « calibre ») : INRS ED 949 ne chiffre que la séparation chariots/piétons, à faire relire par game-designer.
PROTECT_M = 1.5
EPS = 1e-9

Cell = tuple[int, int]


class LayoutError(ValueError):
    """Le plan demandé ne tient pas dans les blocs du pack."""


# --- outils géométriques ----------------------------------------------------------------------------------------


@lru_cache
def _footprints() -> dict[str, tuple[float, float]]:
    return {a.id: (a.footprint.w, a.footprint.d) for a in load_assets_catalog().assets}


def _fp(asset: str) -> tuple[float, float]:
    try:
        return _footprints()[asset]
    except KeyError:
        raise LayoutError(f"asset inconnu du catalogue : {asset}") from None


def _cells(asset: str, cell_m: float) -> tuple[int, int]:
    w, d = _fp(asset)
    return max(1, math.ceil(w / cell_m - EPS)), max(1, math.ceil(d / cell_m - EPS))


def _edge_cell(c: int, r: int, w: int, h: int, dc: int, dr: int) -> Cell:
    """Première cellule hors de l'emprise, au milieu du côté tourné vers (dc, dr)."""
    return (c + w if dc > 0 else c - 1 if dc < 0 else c + w // 2, r + h if dr > 0 else r - 1 if dr < 0 else r + h // 2)


class _Frame:
    def __init__(self, front: str, cols: int, rows: int) -> None:
        self.front, self.cols, self.rows = front, cols, rows
        self.un, self.vn = (cols, rows) if front in ("sud", "nord") else (rows, cols)

    def rect(self, u: int, v: int, wu: int, wv: int) -> tuple[int, int, int, int]:
        """Rectangle abstrait -> (colonne, ligne, largeur, hauteur) de la grille réelle."""
        if self.front == "sud":
            return u, v, wu, wv
        if self.front == "nord":
            return u, self.rows - v - wv, wu, wv
        if self.front == "est":
            return v, u, wv, wu
        return self.cols - v - wv, u, wv, wu


class _Dept:
    """Un bloc en cours de remplissage : grille, occupation (masques binaires par ligne), objets."""

    def __init__(self, dep: dict[str, Any], block: dict[str, Any], front: str, origin: tuple[float, float],
                 cell_m: float, cols: int, rows: int) -> None:  # fmt: skip
        self.id, self.label, self.external = dep["id"], dep["label"], bool(dep.get("external"))
        self.block, self.front, self.cell_m, self.cols, self.rows = dep.get("block"), front, cell_m, cols, rows
        self.ox, self.oz = origin
        self.frame = _Frame(front, cols, rows)
        self.band = int(block.get("front_aisle_cells", 0))
        self.row_aisle = int(block.get("row_aisle_cells", 0))
        self.palette = {a: _cells(a, cell_m) for a in block.get("decor", [])}
        self.occ = [0] * rows
        self.blk = [0] * rows
        self.aisles: set[Cell] = set()
        self.fronts: dict[Cell, str] = {}  # cellule devant un poste -> id du poste
        self.objects: list[dict[str, Any]] = []
        self.counts: Counter[str] = Counter()
        self.unplaced: list[str] = []

    # occupation
    def fits(self, c: int, r: int, w: int, h: int, halo: int = 1, rot: int | None = None) -> bool:
        if c < 0 or r < 0 or c + w > self.cols or r + h > self.rows:
            return False
        m = ((1 << w) - 1) << c
        for rr in range(r, r + h):
            if (self.occ[rr] | self.blk[rr]) & m:
                return False
        if halo:
            c0, c1 = max(c - halo, 0), min(c + w + halo, self.cols)
            hm = ((1 << (c1 - c0)) - 1) << c0
            for rr in range(max(r - halo, 0), min(r + h + halo, self.rows)):
                if self.occ[rr] & hm:
                    return False
        if rot is not None:  # poste : la cellule de devant existe et n'est pas occupée par un objet
            fc, fr = _edge_cell(c, r, w, h, *ROT_VEC[rot])
            if not (0 <= fc < self.cols and 0 <= fr < self.rows) or self.occ[fr] >> fc & 1:
                return False
        return True

    def mark(self, rows: list[int], c: int, r: int, w: int, h: int, on: bool = True) -> None:
        m = ((1 << w) - 1) << c
        for rr in range(r, r + h):
            rows[rr] = rows[rr] | m if on else rows[rr] & ~m

    def add_aisle(self, u: int, v: int, wu: int, wv: int) -> None:
        wu, wv = min(wu, self.frame.un - u), min(wv, self.frame.vn - v)
        if wu <= 0 or wv <= 0:
            return
        c, r, w, h = self.frame.rect(u, v, wu, wv)
        self.mark(self.blk, c, r, w, h)
        self.aisles.update((cc, rr) for cc in range(c, c + w) for rr in range(r, r + h))

    def is_free(self, c: int, r: int) -> bool:
        return 0 <= c < self.cols and 0 <= r < self.rows and not self.occ[r] >> c & 1

    def center(self, c: float, r: float, w: float = 1, h: float = 1) -> list[float]:
        return [round(self.ox + (c + w / 2) * self.cell_m, 3), round(self.oz + (r + h / 2) * self.cell_m, 3)]

    def add_object(self, item: dict[str, Any], c: int, r: int, w: int, h: int, rot: int, role: str | None = None,
                   shift: float = 0.0, obj_id: str | None = None) -> dict[str, Any]:  # fmt: skip
        role = role or item["role"]
        n = self.counts[role]
        self.counts[role] += 1
        x, z = self.center(c, r, w, h)
        if shift:  # recul vers le mur du fond (porte posée sur le mur)
            dc, dr = ROT_VEC[rot % 360]
            x, z = round(x - dc * shift, 3), round(z - dr * shift, 3)
        obj = {
            "asset": item["asset"], "position": [x, z], "rotation": float(rot % 360), "label": item.get("label"),
            "ref": item.get("ref"), "id": obj_id or f"{self.id}.{role}.{n}", "department_id": self.id, "role": role,
            "cell": [c, r], "cells": [w, h],
        }  # fmt: skip
        self.objects.append(obj)
        self.mark(self.occ, c, r, w, h)
        if role == "poste":
            self.fronts[_edge_cell(c, r, w, h, *ROT_VEC[rot % 360])] = obj["id"]
            fc, fr = _edge_cell(c, r, w, h, *ROT_VEC[rot % 360])
            if 0 <= fc < self.cols and 0 <= fr < self.rows:
                self.mark(self.blk, fc, fr, 1, 1)
        return obj

    def reserved(self) -> list[Cell]:
        return sorted(self.aisles | {c for c in self.fronts if 0 <= c[0] < self.cols and 0 <= c[1] < self.rows})


# --- éléments d'un département ----------------------------------------------------------------------------------


def _expand(dep: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Éléments du pack développés en objets à poser (quantités, références, machines de la spec)."""
    factory = spec.get("factory") or {}
    line_ids = [line["id"] for line in spec.get("lines", [])]
    machines = sorted(
        factory.get("machines", []),
        key=lambda m: (line_ids.index(m["line_id"]) if m["line_id"] in line_ids else len(line_ids), m["rank"]),
    )
    components = [b["component_id"] for b in factory.get("bom", [])]
    items: list[dict[str, Any]] = []
    for e in dep.get("elements", []):
        per, role = e.get("per"), e["role"]
        base = {k: e[k] for k in ("asset", "label", "role") if k in e} | {"ref": e.get("ref"), "per": per}
        if per == "machine":
            for m in machines:
                it = dict(base, machine_id=m["id"], line_id=m["line_id"], rank=m["rank"])
                if role == "machine":
                    it |= {"asset": m["asset"], "label": m["name"], "ref": f"machine:{m['id']}"}
                elif role == "tampon":
                    it["ref"] = f"buffer:{m['id']}"
                items.append(it)
        elif per == "line":
            items += [dict(base, line_id=lid, ref=f"line:{lid}") for lid in line_ids]
        elif per == "places":
            capacity = factory.get("logistics", {}).get(dep.get("capacity"), 0)
            for i in range(math.ceil(capacity / e["places"])):
                ref = f"mp:{components[i % len(components)]}" if e.get("ref") == "mp" and components else e.get("ref")
                items.append(dict(base, ref=ref))
        else:
            items += [dict(base) for _ in range(int(e.get("count", 1)))]
    return items


def _order(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Porte d'abord, postes en dernier (leur cellule de devant doit rester libre), le reste dans l'ordre du pack."""
    rank = {"porte": 0, "poste": 2}
    return sorted(items, key=lambda it: rank.get(it["role"], 1))  # tri stable


def _scan(d: _Dept, wu: int, wv: int, halo: int, rot: int | None) -> tuple[int, int, int, int] | None:
    fr = d.frame
    for v in range(fr.vn - wv + 1):
        for u in range(fr.un - wu + 1):
            c, r, w, h = fr.rect(u, v, wu, wv)
            if d.fits(c, r, w, h, halo, rot):
                return c, r, w, h
    return None


def _first_fit(d: _Dept, items: list[dict[str, Any]]) -> None:
    for it in _order(items):
        cw, cd = _cells(it["asset"], d.cell_m)
        rot = ROT[d.front]
        shapes = [(cw, cd)] + ([(cd, cw)] if it["asset"] == "prop_floor_zone" else [])
        found = None
        for halo in (1, 0):  # shortcut: sans marge si rien ne tient avec, à revoir si les blocs se remplissent
            for wu, wv in shapes:
                found = _scan(d, wu, wv, halo, rot if it["role"] == "poste" else None)
                if found:
                    break
            if found:
                break
        if found:
            shift = _fp(it["asset"])[1] / 2 if it["role"] == "porte" else 0.0
            d.add_object(it, *found, rot, shift=shift)
        elif it["role"] == "tampon" and not it.get("ref"):
            d.unplaced.append(f"bloc {d.id} : {it['label']} ne tient pas dans la zone")
        else:
            raise LayoutError(f"bloc {d.id} : {it['label']} ne tient pas dans la zone")


# --- motifs de bloc ---------------------------------------------------------------------------------------------


def _pattern_edge(d: _Dept, items: list[dict[str, Any]]) -> None:
    fr = d.frame
    d.add_aisle(0, fr.vn - d.band, fr.un, d.band)
    for it in [i for i in items if i["role"] == "porte"]:  # porte au fond, centrée
        cw, cd = _cells(it["asset"], d.cell_m)
        c, r, w, h = fr.rect((fr.un - cw) // 2, 0, cw, cd)
        d.add_object(it, c, r, w, h, ROT[d.front], shift=_fp(it["asset"])[1] / 2)
    _first_fit(d, [i for i in items if i["role"] != "porte"])


def _pattern_rows(d: _Dept, items: list[dict[str, Any]]) -> None:
    fr = d.frame
    d.add_aisle(0, fr.vn - d.band, fr.un, d.band)
    racks = [i for i in items if i.get("per") == "places"]
    if racks:
        cw, cd = _cells(racks[0]["asset"], d.cell_m)
        wu, wv = cd, cw  # racks perpendiculaires à l'allée de devant
        usable = fr.vn - d.band
        if wv > usable:
            raise LayoutError(f"bloc {d.id} : un rack ({wv} cellules) dépasse la zone de rangées ({usable})")
        per_col = usable // wv
        cols = math.ceil(len(racks) / per_col)
        pitch = wu + d.row_aisle
        if pitch * (cols - 1) + wu > fr.un:
            raise LayoutError(f"bloc {d.id} : {len(racks)} racks ne tiennent pas dans la zone")
        for i, it in enumerate(racks):
            j, s = divmod(i, per_col)
            rot = (ROT[UPLUS[d.front]] + 180 * (j % 2)) % 360  # chaque rangée regarde l'allée de cariste
            d.add_object(it, *fr.rect(pitch * j, s * wv, wu, wv), rot)
        for j in range(0, cols - 1, 2):
            d.add_aisle(pitch * j + wu, 0, d.row_aisle, fr.vn)
    _first_fit(d, [i for i in items if i.get("per") != "places"])


def _pattern_line(d: _Dept, items: list[dict[str, Any]]) -> None:
    fr = d.frame
    by_line: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        if it.get("per") == "machine":
            by_line.setdefault(it["line_id"], []).append(it)
    rot_plus = ROT[UPLUS[d.front]]
    pitch = 0
    k = 0
    for lid, group in by_line.items():
        machines = sorted((i for i in group if i["role"] == "machine"), key=lambda i: i["rank"])
        tables = {i["machine_id"]: i for i in group if i["role"] == "tampon"}
        shapes = [(_cells(m["asset"], d.cell_m), tables.get(m["machine_id"])) for m in machines]
        height = max((s[0][0] for s in shapes), default=0)  # largeur de la machine = hauteur de la ligne
        pitch = height + d.row_aisle
        v0 = 1 + k * pitch
        u = 0
        for m, ((mw, md), table) in zip(machines, shapes, strict=True):
            parts = [(m, md, mw)] + ([(table, *_cells(table["asset"], d.cell_m)[::-1])] if table else [])
            for it, wu, wv in parts:
                c, r, w, h = fr.rect(u, v0, wu, wv)
                if not d.fits(c, r, w, h, 0):
                    raise LayoutError(f"bloc {d.id} : la ligne {lid} ne tient pas ({len(machines)} machines)")
                d.add_object(it, c, r, w, h, rot_plus)
                u += wu
        for it in [i for i in items if i.get("per") == "line" and i["line_id"] == lid]:
            c, r, w, h = fr.rect(u + 1, v0, 1, 1)
            if not d.fits(c, r, w, h, 0):
                raise LayoutError(f"bloc {d.id} : l'andon de la ligne {lid} ne tient pas")
            d.add_object(it, c, r, w, h, ROT[d.front])
        d.add_aisle(0, v0 + height, fr.un, d.row_aisle)
        k += 1
    rest = [i for i in items if i.get("per") not in ("machine", "line")]
    for it in [i for i in rest if i["role"] == "affichage"]:  # tableau au fond, à l'extrémité droite
        cw, cd = _cells(it["asset"], d.cell_m)
        c, r, w, h = fr.rect(fr.un - cw, 0, cw, cd)
        if d.fits(c, r, w, h, 0):
            d.add_object(it, c, r, w, h, ROT[d.front])
            rest.remove(it)
    _first_fit(d, rest)


def _pattern_single(d: _Dept, items: list[dict[str, Any]], building: str | None) -> None:
    if building:
        bw, bd = _cells(building, d.cell_m)
        c, r = (d.cols - bw) // 2, (d.rows - bd) // 2
        d.add_object({"asset": building, "label": d.label, "ref": None}, c, r, bw, bd, ROT["nord"], role="batiment")
        margin = 3
        c0, r0 = max(c - margin, 0), max(r - margin, 0)
        d.mark(d.blk, c0, r0, min(bw + 2 * margin, d.cols - c0), min(bd + 2 * margin, d.rows - r0))
    _first_fit(d, items)


# --- réseau : sites, liens, délais ------------------------------------------------------------------------------


def lead_days(prep_days: float, km: float, speed_kmh: float, driving_h_per_day: float) -> int:
    """Délai d'un fournisseur : préparation + trajet (km / vitesse / heures de conduite par jour), borné 1 à 8."""
    return max(1, min(8, int(prep_days) + math.ceil(km / speed_kmh / driving_h_per_day - EPS)))


def site_label(name: str, site: dict[str, Any]) -> str:
    kind = str(site["kind"]).capitalize()
    return f"{kind} {site['supplier_profile']}" if site.get("supplier_profile") else kind


def chosen_class(spec: dict[str, Any], pack: dict[str, Any], name: str) -> str:
    site = pack["network"]["sites"][name]
    chosen = (spec.get("params", {}).get("network") or {}).get(name)
    return chosen if chosen in site["distances"] else site["default"]


def site_lead_days(spec: dict[str, Any], pack: dict[str, Any], name: str) -> int:
    """Délai (jours) du site `name` avec la classe de distance choisie ; défauts du pack : 1, 3 et 5 jours."""
    net, site = pack["network"], pack["network"]["sites"][name]
    km = net["distance_classes"][chosen_class(spec, pack, name)]["km"]
    speed = net["link_types"][site["link"]]["speed_kmh"]
    return lead_days(site.get("prep_days", 0), km, speed, net["driving_h_per_day"])


def _build_network(spec: dict[str, Any], pack: dict[str, Any], hall: list[float], dock_x: float):
    """Sites et liens de la carte : l'usine d'abord, puis chaque site à sa colonne au sud du hall."""
    net = pack["network"]
    cell, off = net["map"]["cell_m"], net["map"]["road_offset_m"]
    hpd = net["driving_h_per_day"]
    supplier_of: dict[str, str] = {}
    for o in spec.get("offers", []):
        supplier_of.setdefault(o["profile"], o["supplier_id"])
    referenced = {d["site"] for d in pack.get("departments", []) if d.get("site")}
    names = [
        n for n, s in net["sites"].items()
        if s["kind"] == "client" or n in referenced or s.get("supplier_profile") in supplier_of
    ]  # fmt: skip
    info = {}
    for n in names:
        s = net["sites"][n]
        cls = chosen_class(spec, pack, n)
        info[n] = (s, cls, net["distance_classes"][cls])
    columns: dict[str, int] = {}
    for side in ("ouest", "est"):
        ordered = sorted((n for n in names if info[n][0]["side"] == side), key=lambda n: (info[n][2]["ring"], n))
        columns.update({n: c for c, n in enumerate(ordered)})
    main = {
        "id": "usine", "kind": "usine", "label": pack.get("label", "Usine"), "external": False, "area": hall,
        "gate": [dock_x, hall[3]],
    }  # fmt: skip
    sites, links = [main], []
    lane_z = hall[3] + off
    for n in names:
        s, cls, dc = info[n]
        c = columns[n]
        if s["side"] == "ouest":
            x0 = dock_x - 10 - (c + 1) * cell
        else:
            x0 = dock_x + 10 + c * cell
        z0 = hall[3] + 2 * off + (dc["ring"] - 1) * cell
        cx = x0 + cell / 2
        speed = net["link_types"][s["link"]]["speed_kmh"]
        travel_h = dc["km"] / speed
        sites.append({
            "id": n, "kind": s["kind"], "label": site_label(n, s), "external": True,
            "area": [x0, z0, x0 + cell, z0 + cell], "gate": [cx, z0],
            "supplier_id": supplier_of.get(s.get("supplier_profile")),
            "distance_class": cls, "km": dc["km"], "travel_h": round(travel_h, 2),
            "transit_days": math.ceil(travel_h / hpd - EPS),
        })  # fmt: skip
        pts = [[cx, z0], [cx, lane_z], [dock_x, lane_z], [dock_x, hall[3]]]
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        links.append({
            "id": f"{s['link']}:{n}", "type": s["link"], "from_site": n, "to_site": "usine", "points": pts,
            "vehicle": net["link_types"][s["link"]].get("vehicle"),
        })  # fmt: skip
    return sites, links, {n: info[n][0] for n in names}


# --- placement du monde -----------------------------------------------------------------------------------------


def _hall(pack: dict[str, Any]) -> list[float]:
    w, d = pack["world"]["size"]
    return [-w / 2, -d / 2, w / 2, d / 2]


def _make_dept(dep: dict[str, Any], pack: dict[str, Any], area: list[float], origin=None, size=None) -> _Dept:
    bt = pack["block_types"][dep["block"]]
    cm = bt["cell_m"]
    cols = size[0] if size else round((area[2] - area[0]) / cm)
    rows = size[1] if size else round((area[3] - area[1]) / cm)
    return _Dept(dep, bt, dep.get("front", "nord"), origin or (area[0], area[1]), cm, cols, rows)


def _layout_dept(d: _Dept, dep: dict[str, Any], pack: dict[str, Any], spec: dict[str, Any], building=None) -> None:
    items = _expand(dep, spec)
    pattern = pack["block_types"][dep["block"]]["pattern"]
    if pattern == "single":
        _pattern_single(d, items, building)
    else:
        {"edge": _pattern_edge, "rows": _pattern_rows, "line": _pattern_line}[pattern](d, items)


def _front_band_point(d: _Dept) -> list[float]:
    if d.band:
        fr = d.frame
        c, r, w, h = fr.rect(0, fr.vn - d.band, fr.un, d.band)
        return d.center(c + w // 2, r + h // 2)
    for r in range(d.rows):
        for c in range(d.cols):
            if d.is_free(c, r):
                return d.center(c, r)
    return d.center(d.cols // 2, d.rows // 2)


def _access(d: _Dept, o: dict[str, Any]) -> list[float]:
    """Point d'interaction : première cellule libre devant l'objet (poste : devant lui), sinon derrière."""
    c, r = o["cell"]
    w, h = o["cells"]
    dc, dr = ROT_VEC[int(o["rotation"]) % 360] if o["role"] == "poste" else FRONT_VEC[d.front]
    for sx, sy in ((dc, dr), (-dc, -dr)):
        cc, rr = _edge_cell(c, r, w, h, sx, sy)
        while 0 <= cc < d.cols and 0 <= rr < d.rows:
            if d.is_free(cc, rr):
                return d.center(cc, rr)
            cc, rr = cc + sx, rr + sy
    return d.center(c, r, w, h)


def _station_positions(d: _Dept, stations: list[dict[str, Any]]) -> list[list[float]]:
    postes = [o for o in d.objects if o["role"] == "poste"]
    boards = [o for o in d.objects if o["role"] == "affichage" and not o.get("ref")]
    by_ref = {o["ref"]: o for o in d.objects if o.get("ref")}
    out, n = [], 0
    for s in stations:
        if s["kind"] == "machine":
            obj = by_ref.get(f"machine:{s['ref']}")
        else:
            obj = postes[n] if n < len(postes) else (boards[0] if boards else None)
            n += 1
        out.append(_access(d, obj) if obj else _front_band_point(d))
    return out


def _route(d: _Dept) -> list[list[float]]:
    """Trois points au plus (début, milieu, fin) sur la ligne médiane de l'allée, sinon la ligne libre la plus
    proche de l'avant."""
    horizontal = d.front in ("sud", "nord")
    cells = [c for c in d.aisles if d.is_free(*c)]
    if cells:
        axis = 1 if horizontal else 0
        mid = sorted({c[axis] for c in cells})
        mid = mid[len(mid) // 2]
        line = sorted((c for c in cells if c[axis] == mid), key=lambda c: c[1 - axis])
    else:
        order = range(d.rows - 1, -1, -1) if d.front == "sud" else range(d.rows) if d.front == "nord" else None
        if order is None:
            order = range(d.cols - 1, -1, -1) if d.front == "est" else range(d.cols)
        line = []
        for k in order:
            line = [(c, k) if horizontal else (k, c) for c in range(d.cols if horizontal else d.rows)]
            line = [c for c in line if d.is_free(*c)]
            if line:
                break
        mid = len(line) // 2
        line = line[max(mid - 3, 0) : mid + 4]
    if not line:
        return [d.center(d.cols // 2, d.rows // 2)]
    picks = [line[0], line[len(line) // 2], line[-1]]
    return [d.center(*c) for i, c in enumerate(picks) if c not in picks[:i]]


def _grid_out(d: _Dept) -> dict[str, Any]:
    return {
        "origin": [d.ox, d.oz], "cell_m": d.cell_m, "cols": d.cols, "rows": d.rows,
        "reserved": [list(c) for c in d.reserved()], "palette": {a: list(s) for a, s in d.palette.items()},
    }  # fmt: skip


def _forklift_route(depts: dict[str, _Dept], pack: dict[str, Any]) -> list[list[float]]:
    flow = next((r for r in pack.get("placement_rules", []) if r["kind"] == "flow"), None)
    anchors = []
    for name in flow["blocks"] if flow else []:
        d = depts.get(name)
        if d is None:
            continue
        fr = d.frame
        if d.band:
            c, r, w, h = fr.rect(0, fr.vn - d.band, fr.un, d.band)
        else:
            c, r, w, h = fr.rect(0, fr.vn - 1, fr.un, 1)
        anchors.append(d.center(c + w // 2, r + h // 2))
    return anchors if len(anchors) >= 2 else [[-10.5, 4.8], [8.0, 4.8]]


def place_world(spec: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    """Pose tout le monde, sans hasard. Retourne `world` (objets, sites, liens, bornes), `departments` (avec leur
    grille), `stations` et `agents` (positions et trajets recalculés), `aisles`, `unplaced`."""
    hall = _hall(pack)
    areas = {d["id"]: d["area"] for d in spec.get("departments", []) if d.get("area")}
    depts: dict[str, _Dept] = {}
    pack_deps = {d["id"]: d for d in pack.get("departments", [])}
    for dep in pack_deps.values():
        if not dep.get("external"):
            d = _make_dept(dep, pack, list(areas.get(dep["id"], dep["area"])))
            _layout_dept(d, dep, pack, spec)
            depts[dep["id"]] = d
    dock = next((o for d in depts.values() for o in d.objects if o["ref"] == "dock"), None)
    dock_x = dock["position"][0] if dock else 0.0
    sites, links, site_defs = _build_network(spec, pack, hall, dock_x) if pack.get("network") else ([], [], {})
    site_area = {s["id"]: s["area"] for s in sites}
    hosted = {dep["site"]: dep for dep in pack_deps.values() if dep.get("site")}
    external: list[tuple[dict[str, Any], str]] = []
    for s in sites[1:]:
        dep = hosted.get(s["id"]) or {"id": s["id"], "label": s["label"], "external": True, "block": "site",
                                      "elements": [], "front": "nord"}  # fmt: skip
        external.append((dep, s["id"]))
    for dep, sid in external:
        area = site_area[sid]
        d = _make_dept(dep, pack, area, size=None)
        _layout_dept(d, dep, pack, spec, building=site_defs[sid]["building"])
        depts[dep["id"]] = d
    # objets du monde : zone de chaque département interne, puis les objets posés
    objects: list[dict[str, Any]] = []
    for dep_id, d in depts.items():
        if not d.external:
            a = areas.get(dep_id) or pack_deps[dep_id]["area"]
            objects.append({
                "asset": "prop_floor_zone", "position": [(a[0] + a[2]) / 2, (a[1] + a[3]) / 2], "rotation": 0.0,
                "label": d.label, "ref": f"dept:{dep_id}", "id": f"{dep_id}.zone.0", "department_id": dep_id,
                "role": None, "cell": None, "cells": None,
            })  # fmt: skip
        objects += d.objects
    stations_out = []
    for dep_id, d in depts.items():
        mine = [s for s in spec.get("stations", []) if s.get("department_id") == dep_id]
        for s, pos in zip(mine, _station_positions(d, mine), strict=True):
            stations_out.append({"id": s["id"], "kind": s["kind"], "ref": s.get("ref"), "department_id": dep_id,
                                 "position": pos})  # fmt: skip
    agents = {
        a["id"]: {"department_id": a["department_id"], "route": _route(depts[a["department_id"]])}
        for a in spec.get("agents", []) if a.get("department_id") in depts
    }  # fmt: skip
    boxes = [hall] + [s["area"] for s in sites[1:]]
    bounds = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return {
        "world": {
            "template": pack["world"]["template"], "size": list(pack["world"]["size"]),
            "spawn": list(pack["world"]["spawn"]), "objects": objects, "forklift_route": _forklift_route(depts, pack),
            "sites": sites, "links": links, "bounds": bounds,
        },
        "departments": [
            {
                "id": dep_id, "label": d.label, "external": d.external, "block": d.block,
                "area": list(areas.get(dep_id) or (pack_deps[dep_id]["area"] if not d.external else site_area[
                    next(s for dep, s in external if dep["id"] == dep_id)])),
                "site_id": next((s for dep, s in external if dep["id"] == dep_id), None), "grid": _grid_out(d),
            }
            for dep_id, d in depts.items()
        ],
        "stations": stations_out,
        "agents": agents,
        "aisles": {dep_id: sorted(list(c) for c in d.aisles) for dep_id, d in depts.items()},
        "unplaced": [m for d in depts.values() for m in d.unplaced],
    }  # fmt: skip


# --- retouches du formateur -------------------------------------------------------------------------------------


def _edit_field(edit: Any, name: str) -> Any:
    return edit.get(name) if isinstance(edit, dict) else getattr(edit, name, None)


def _dept_from_bundle(bundle: dict[str, Any], dep: dict[str, Any], pack: dict[str, Any]) -> _Dept:
    pack_dep = next((p for p in pack.get("departments", []) if p["id"] == dep["id"]), {})
    g = dep["grid"]
    block = pack["block_types"].get(dep.get("block") or "", {})
    d = _Dept(dep | {"front": pack_dep.get("front", "nord")}, block, pack_dep.get("front", "nord"), tuple(g["origin"]),
              g["cell_m"], g["cols"], g["rows"])  # fmt: skip
    d.palette = {a: tuple(s) for a, s in g["palette"].items()}
    aisles = bundle.get("aisles", {}).get(dep["id"])
    d.objects = [o for o in bundle["world"]["objects"] if o.get("department_id") == dep["id"] and o.get("cell")]
    for o in d.objects:
        d.mark(d.occ, *o["cell"], *o["cells"])
        if o["role"] == "poste":
            d.fronts[_edge_cell(*o["cell"], *o["cells"], *ROT_VEC[int(o["rotation"]) % 360])] = o["id"]
    reserved = {tuple(c) for c in g["reserved"]}
    d.aisles = {tuple(c) for c in aisles} if aisles is not None else reserved - set(d.fronts)
    for c, r in d.aisles | reserved:
        d.mark(d.blk, c, r, 1, 1)
    return d


def apply_edits(
    bundle: dict[str, Any], edits: list[Any], pack: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Applique les retouches (au plus 200) au plan de `place_world`, sans hasard. Une retouche refusée est listée
    avec sa raison et laisse le plan intact ; les positions des postes et les trajets sont recalculés."""
    if len(edits) > MAX_EDITS:
        raise ValueError(f"{len(edits)} retouches : {MAX_EDITS} au plus")
    out = copy.deepcopy(bundle)
    objects = out["world"]["objects"]
    by_id = {o["id"]: o for o in objects}
    depts = {d["id"]: _dept_from_bundle(out, d, pack) for d in out["departments"] if d.get("grid")}
    display_roles = {
        e["asset"] for p in pack.get("departments", []) for e in p.get("elements", []) if e["role"] == "affichage"
    }
    removed: set[str] = set()
    added: list[dict[str, Any]] = []
    touched: set[str] = set()
    rejections: list[dict[str, Any]] = []

    def reject(i: int, reason: str, message: str) -> None:
        rejections.append({"index": i, "reason": reason, "message": message})

    def check(d: _Dept, i: int, c: int, r: int, w: int, h: int, poste: dict[str, Any] | None, rot: int) -> bool:
        """Rect libre dans le bloc ? Ordre : hors_bloc, devant_poste, allee, occupe."""
        if c < 0 or r < 0 or c + w > d.cols or r + h > d.rows:
            reject(i, "hors_bloc", f"La retouche sort du bloc « {d.label} ».")
            return False
        cells = [(cc, rr) for cc in range(c, c + w) for rr in range(r, r + h)]
        own = poste["id"] if poste else None
        if any(d.fronts.get(x) not in (None, own) for x in cells):
            reject(i, "devant_poste", "La retouche bloque l'accès d'un poste de travail.")
            return False
        if poste:
            fc, fr = _edge_cell(c, r, w, h, *ROT_VEC[rot])
            if not d.is_free(fc, fr) or (fc, fr) in cells:
                reject(i, "devant_poste", "Le poste n'aurait plus de place devant lui.")
                return False
        if any(x in d.aisles for x in cells):
            reject(i, "allee", "La retouche empiète sur une allée.")
            return False
        m = ((1 << w) - 1) << c
        if any(d.occ[rr] & m for rr in range(r, r + h)):
            reject(i, "occupe", "La place est déjà occupée.")
            return False
        return True

    for i, edit in enumerate(edits):
        op, cell = _edit_field(edit, "op"), _edit_field(edit, "cell")
        rot_edit = int(_edit_field(edit, "rot") or 0)
        if op == "add":
            d = depts.get(_edit_field(edit, "department_id") or "")
            if d is None:
                reject(i, "cible_inconnue", "Bloc inconnu.")
                continue
            asset = _edit_field(edit, "asset")
            if asset not in d.palette:
                reject(i, "asset_non_permis", f"« {asset} » n'est pas permis dans le bloc « {d.label} ».")
                continue
            w, h = d.palette[asset][::-1] if rot_edit % 180 else d.palette[asset]
            if not check(d, i, cell[0], cell[1], w, h, None, rot_edit):
                continue
            role = "affichage" if asset in display_roles else "decor"
            obj = d.add_object({"asset": asset, "label": None, "ref": None}, cell[0], cell[1], w, h, rot_edit,
                               role=role, obj_id=f"{d.id}.ajout.{i}")  # fmt: skip
            added.append(obj)
            by_id[obj["id"]] = obj
            touched.add(d.id)
            continue
        o = by_id.get(_edit_field(edit, "object_id") or "")
        if o is None or o["id"] in removed or o.get("department_id") not in depts:
            reject(i, "cible_inconnue", "Objet inconnu.")
            continue
        d = depts[o["department_id"]]
        if op == "remove":
            if o["role"] not in EDITABLE_ROLES or o.get("ref"):
                reject(i, "role_fixe", "Cet objet est simulé ou fixé par le plan : il ne peut pas être retiré.")
                continue
            d.mark(d.occ, *o["cell"], *o["cells"], on=False)
            removed.add(o["id"])
            d.objects.remove(o)
            touched.add(d.id)
            continue
        if not o.get("cell") or o["role"] in FIXED_MOVE:
            reject(i, "role_fixe", "Cet objet est fixé par le plan : il ne peut pas être déplacé.")
            continue
        w, h = o["cells"][::-1] if rot_edit % 180 else o["cells"]
        rot = (int(o["rotation"]) + rot_edit) % 360
        d.mark(d.occ, *o["cell"], *o["cells"], on=False)
        if not check(d, i, cell[0], cell[1], w, h, o if o["role"] == "poste" else None, rot):
            d.mark(d.occ, *o["cell"], *o["cells"])
            continue
        d.fronts = {c: k for c, k in d.fronts.items() if k != o["id"]}
        o["cell"], o["cells"], o["rotation"] = [cell[0], cell[1]], [w, h], float(rot)
        o["position"] = d.center(cell[0], cell[1], w, h)
        d.mark(d.occ, cell[0], cell[1], w, h)
        if o["role"] == "poste":
            d.fronts[_edge_cell(cell[0], cell[1], w, h, *ROT_VEC[rot])] = o["id"]
        touched.add(d.id)
    out["world"]["objects"] = [o for o in objects if o["id"] not in removed] + added
    for dep in out["departments"]:
        d = depts.get(dep["id"])
        if d is None or dep["id"] not in touched:
            continue
        dep["grid"]["reserved"] = [list(c) for c in d.reserved()]
        mine = [s for s in out["stations"] if s["department_id"] == d.id]
        for s, pos in zip(mine, _station_positions(d, mine), strict=True):
            s["position"] = pos
        for a in out["agents"].values():
            if a["department_id"] == d.id:
                a["route"] = _route(d)
    return out, rejections


def recompile_layout(
    spec: dict[str, Any], pack: dict[str, Any], edits: list[Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Nouvelle spec dont le plan est recalculé puis retouché : monde, départements, positions des postes et trajets
    des agents (`spec["agents"][i]["route"]`) ; `layout_edits` = les retouches reçues. Retourne aussi les retouches
    refusées (la spec reçue n'est pas modifiée). Les retouches sont des dict ou des `LayoutEdit`."""
    from gmix.game.spec import LayoutEdit  # import tardif : spec ne dépend pas du placeur

    models = [e if isinstance(e, LayoutEdit) else LayoutEdit(**e) for e in edits]
    bundle, rejected = apply_edits(place_world(spec, pack), models, pack)
    stations = {s["id"]: s["position"] for s in bundle["stations"]}
    routes = {agent_id: a["route"] for agent_id, a in bundle["agents"].items()}
    new = spec | {
        "world": spec["world"] | bundle["world"],
        "departments": bundle["departments"],
        "stations": [s | {"position": stations.get(s["id"], s.get("position"))} for s in spec["stations"]],
        "agents": [a | {"route": routes.get(a["id"], a.get("route"))} for a in spec["agents"]],
        "layout_edits": [e.model_dump(mode="json") if isinstance(e, LayoutEdit) else e for e in edits],
    }
    return new, rejected


# --- contrôle des règles de placement ---------------------------------------------------------------------------


def _obj_rect(o: dict[str, Any], cell_m: float) -> tuple[float, float, float, float]:
    if o.get("cells"):
        w, d = o["cells"][0] * cell_m, o["cells"][1] * cell_m
    else:
        w, d = _fp(o["asset"])
        if int(o["rotation"]) % 180:
            w, d = d, w
    x, z = o["position"]
    return x - w / 2, z - d / 2, x + w / 2, z + d / 2


def _gap(a: tuple, b: tuple) -> tuple[float, float, float, float]:
    """Écarts (dx, dz) et chevauchements (ox, oz) de deux rectangles ; un écart négatif = recouvrement."""
    dx, dz = max(b[0] - a[2], a[0] - b[2]), max(b[1] - a[3], a[1] - b[3])
    return dx, dz, min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])


def _distance(a: list[tuple], b: list[tuple]) -> float:
    return min(math.hypot(max(dx, 0), max(dz, 0)) for ra in a for rb in b for dx, dz, _, _ in [_gap(ra, rb)])


def _touching(a: tuple, b: tuple) -> bool:
    dx, dz, ox, oz = _gap(a, b)
    return (dx <= 3 + EPS and oz > EPS) or (dz <= 3 + EPS and ox > EPS)


def _seg_dist(p: list[float], a: list[float], b: list[float]) -> float:
    """Distance d'un point au segment ab."""
    dx, dz = b[0] - a[0], b[1] - a[1]
    t = 0.0 if dx == dz == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / (dx * dx + dz * dz)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz)


def _crosses(a: list[float], b: list[float], c: list[float], d: list[float]) -> bool:
    """Croisement franc de ab et cd (les contacts en bout et les segments colinéaires ne comptent pas)."""

    def side(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    return side(a, b, c) * side(a, b, d) < -EPS and side(c, d, a) * side(c, d, b) < -EPS


def _shares_segment(p: list[list[float]], q: list[list[float]]) -> bool:
    """Deux polylignes empruntent-elles un tronçon commun (segments colinéaires qui se recouvrent) ?"""
    for a, b in zip(p, p[1:], strict=False):
        for c, d in zip(q, q[1:], strict=False):
            if (
                abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) > EPS
                or abs((b[0] - a[0]) * (d[1] - a[1]) - (b[1] - a[1]) * (d[0] - a[0])) > EPS
            ):
                continue
            axis = 0 if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else 1
            if (
                min(max(a[axis], b[axis]), max(c[axis], d[axis])) - max(min(a[axis], b[axis]), min(c[axis], d[axis]))
                > EPS
            ):
                return True
    return False


def _protected_path(rule: dict[str, Any], spec: dict[str, Any], rects, objects: list[dict[str, Any]]) -> list[str]:
    """Règle `protected_path` (annexe 0010 §8) : circulation de a vers b, croisements, sens unique, barrières."""
    rid, a, b = rule["id"], rule["a"], rule["b"]
    world = spec.get("world", {})
    links = world.get("links", [])
    link = next((lk for lk in links if (lk["from_site"], lk["to_site"]) == (a, b)), None)
    path = [list(pt) for pt in link["points"]] if link else None
    route = [list(pt) for pt in world.get("forklift_route", [])]
    ra, rb = rects(a), rects(b)
    if path is None and len(route) >= 2 and ra and rb:

        def nearest(r):
            c = [(r[0][0] + r[0][2]) / 2, (r[0][1] + r[0][3]) / 2]
            return min(range(len(route)), key=lambda i: math.hypot(route[i][0] - c[0], route[i][1] - c[1]))

        i, j = sorted((nearest(ra), nearest(rb)))
        path = route[i : j + 1] if i != j else None
    if path is None:
        return [f"règle {rid} : aucune circulation entre {a} et {b}."]
    msgs = []
    others = [lk["points"] for lk in links if lk is not link] + ([route] if link and len(route) >= 2 else [])
    segments = list(zip(path, path[1:], strict=False))
    crossings = sum(
        _crosses(p, q, c, d) for p, q in segments for pts in others for c, d in zip(pts, pts[1:], strict=False)
    )
    if crossings > rule["crossings_max"]:
        msgs.append(f"règle {rid} : le chemin {a} -> {b} croise {crossings} fois une autre circulation, "
                    f"{rule['crossings_max']} au plus.")  # fmt: skip
    if rule["one_way"] and any(
        (lk["from_site"], lk["to_site"]) == (b, a) and _shares_segment(path, lk["points"]) for lk in links
    ):
        msgs.append(f"règle {rid} : le chemin {a} -> {b} est à double sens.")
    if rule["barrier"]:

        def near(o):
            return min((_seg_dist(o["position"], p, q) for p, q in segments), default=float("inf"))

        guarded = any(o.get("role") == "barriere" and near(o) <= PROTECT_M for o in objects)
        for o in objects:
            if o.get("role") == "poste" and near(o) <= PROTECT_M and not guarded:
                msgs.append(f"règle {rid} : « {o.get('label') or o['asset']} » à {near(o):.1f} m du chemin "
                            f"{a} -> {b}, sans barrière.")  # fmt: skip
    return msgs


def check_placement(spec: dict[str, Any], pack: dict[str, Any]) -> list[str]:
    """Écarts du plan de la spec aux règles du pack et à l'intégrité des grilles : un message français par écart."""
    deps = {d["id"]: d for d in spec.get("departments", [])}
    pack_deps = {d["id"]: d for d in pack.get("departments", [])}
    objects = spec.get("world", {}).get("objects", [])
    cell_of = {i: d["grid"]["cell_m"] for i, d in deps.items() if d.get("grid")}
    msgs: list[str] = []

    def rects(name: str) -> list[tuple]:
        if name in deps:
            return [tuple(deps[name]["area"])]
        by_block = [tuple(d["area"]) for d in deps.values() if d.get("block") == name]
        if by_block:
            return by_block
        return [_obj_rect(o, cell_of.get(o.get("department_id"), 0.5)) for o in objects
                if o.get("ref") and (o["ref"] == name or o["ref"].startswith(name + ":"))]  # fmt: skip

    for rule in pack.get("placement_rules", []):
        rid, kind = rule["id"], rule["kind"]
        if kind in ("adjacent", "flow"):
            pairs = (
                [(rule["a"], rule["b"])]
                if kind == "adjacent"
                else list(zip(rule["blocks"], rule["blocks"][1:], strict=False))
            )
            for a, b in pairs:
                ra, rb = rects(a), rects(b)
                if not ra or not rb:
                    msgs.append(f"règle {rid} : {a if not ra else b} est introuvable dans le plan.")
                elif not any(_touching(x, y) for x in ra for y in rb):
                    msgs.append(
                        f"règle {rid} : {a} et {b} ne sont pas contigus ({_distance(ra, rb):.1f} m, 3 m au plus)."
                    )
        elif kind in ("separated", "near"):
            ra, rb = rects(rule["a"]), rects(rule["b"])
            if not ra or not rb:
                msgs.append(f"règle {rid} : {rule['a'] if not ra else rule['b']} est introuvable dans le plan.")
                continue
            gap = _distance(ra, rb)
            if kind == "separated" and gap < rule["min_m"] - EPS:
                msgs.append(
                    f"règle {rid} : {rule['a']} et {rule['b']} sont à {gap:.1f} m, {rule['min_m']} m au moins exigés."
                )
            if kind == "near" and gap > rule["max_m"] + EPS:
                msgs.append(
                    f"règle {rid} : {rule['a']} et {rule['b']} sont à {gap:.1f} m, {rule['max_m']} m au plus exigés."
                )
        elif kind == "aisle_min":
            for name, bt in pack.get("block_types", {}).items():
                for key in ("front_aisle_cells", "row_aisle_cells"):
                    width = bt.get(key, 0) * bt["cell_m"]
                    if 0 < width < rule["min_m"] - EPS and any(d.get("block") == name for d in deps.values()):
                        msgs.append(
                            f"règle {rid} : l'allée du bloc {name} fait {width:g} m, {rule['min_m']} m au moins exigés."
                        )
            inner = [d for d in deps.values() if not d.get("external")]
            for i, a in enumerate(inner):
                for b in inner[i + 1 :]:
                    dx, dz, ox, oz = _gap(tuple(a["area"]), tuple(b["area"]))
                    gap = dx if oz > EPS and 0 < dx <= 3 else dz if ox > EPS and 0 < dz <= 3 else None
                    if gap is not None and gap < rule["min_m"] - EPS:
                        msgs.append(
                            f"règle {rid} : l'allée entre {a['id']} et {b['id']} fait {gap:g} m, "
                            f"{rule['min_m']} m au moins."
                        )
        elif kind == "protected_path":
            msgs += _protected_path(rule, spec, rects, objects)
        elif kind == "facing":
            targets = [d["id"] for d in deps.values() if rule["block"] in (d["id"], d.get("block"))]
            dock = next((o for o in objects if o.get("ref") == "dock"), None)
            for o in objects:
                if o.get("department_id") not in targets or o.get("role") != rule["role"]:
                    continue
                rot = int(o["rotation"]) % 360
                if rule["toward"] == "front":
                    ok = rot == ROT[pack_deps.get(o["department_id"], {}).get("front", "nord")]
                else:
                    tx, tz = dock["position"] if dock and rule["toward"] == "dock" else (0.0, 0.0)
                    fx, fz = ROT_VEC[rot]
                    ok = fx * (tx - o["position"][0]) + fz * (tz - o["position"][1]) > 0
                if not ok:
                    msgs.append(
                        f"règle {rid} : « {o.get('label') or o['asset']} » ({o['id']}) "
                        f"ne fait pas face à {rule['toward']}."
                    )
    msgs += _integrity(spec, pack, deps, pack_deps, objects)
    return msgs


def _integrity(spec, pack, deps, pack_deps, objects) -> list[str]:
    msgs = []
    for dep_id, dep in deps.items():
        g = dep.get("grid")
        if not g:
            continue
        mine = [o for o in objects if o.get("department_id") == dep_id and o.get("cell")]
        reserved = {tuple(c) for c in g["reserved"]}
        seen: dict[Cell, str] = {}
        flagged: set[tuple[str, str]] = set()
        for o in mine:
            c, r = o["cell"]
            w, h = o["cells"]
            name = o.get("label") or o["asset"]
            if c < 0 or r < 0 or c + w > g["cols"] or r + h > g["rows"]:
                msgs.append(f"bloc {dep_id} : « {name} » ({o['id']}) sort de la grille.")
            cells = [(cc, rr) for cc in range(c, c + w) for rr in range(r, r + h)]
            if (
                any(x in reserved for x in cells)
                and o["role"] != "poste"
                or (o["role"] == "poste" and set(cells) & reserved)
            ):
                msgs.append(f"bloc {dep_id} : « {name} » ({o['id']}) est sur une cellule d'allée.")
            for x in cells:
                other = seen.setdefault(x, o["id"])
                if other != o["id"] and (other, o["id"]) not in flagged:
                    flagged.add((other, o["id"]))
                    msgs.append(f"bloc {dep_id} : {other} et {o['id']} se chevauchent.")
        pack_dep = pack_deps.get(dep_id)
        if pack_dep and not pack_dep.get("external"):
            want = Counter((e["role"], e["asset"]) for e in _expand(pack_dep, spec) if e["role"] not in EDITABLE_ROLES)
            have = Counter((o["role"], o["asset"]) for o in mine)
            for (role, asset), n in sorted(want.items()):
                if have[(role, asset)] < n:
                    label = next(
                        e["label"] for e in _expand(pack_dep, spec) if (e["role"], e["asset"]) == (role, asset)
                    )
                    msgs.append(f"bloc {dep_id} : {label} ({asset}) n'est pas placé ({have[(role, asset)]} sur {n}).")
    return msgs


# --- assets exigés par le pack ----------------------------------------------------------------------------------


def required_assets(pack: dict[str, Any]) -> set[str]:
    """Assets que le pack utilise (hors palettes de décor de l'éditeur)."""
    found: set[str] = set()
    for dep in pack.get("departments", []):
        found |= {e["asset"] for e in dep.get("elements", [])}
        if dep.get("agent", {}).get("character"):
            found.add(dep["agent"]["character"])
    found |= {m["asset"] for m in pack.get("machine_types", {}).values() if m.get("asset")}
    net = pack.get("network", {})
    found |= {s["building"] for s in net.get("sites", {}).values() if s.get("building")}
    found |= {t["vehicle"] for t in net.get("link_types", {}).values() if t.get("vehicle")}
    found |= {a["character"] for a in pack.get("extra_agents", {}).values() if a.get("character")}
    for member in pack.get("crew", []):
        found |= set(member.get("characters", []))
    return found


def pack_coverage(pack_id: str, catalog: AssetCatalog | None = None) -> dict[str, Any]:
    """Part des assets exigés par le pack qui existent au catalogue et ne sont pas « a_sourcer »."""
    from gmix.game.spec import load_pack

    known = (catalog or load_assets_catalog()).by_id()
    required = sorted(required_assets(load_pack(pack_id)))
    missing = [a for a in required if a not in known or known[a].status == "a_sourcer"]
    return {
        "ratio": 1.0 if not required else 1 - len(missing) / len(required),
        "required": required,
        "missing": missing,
    }

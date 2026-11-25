# ruff: noqa: E501
"""Own implementation of small carbon-chain structures: parsing, naming and isomer counting.

No cheminformatics library is used. A condensed formula such as CH3-CH(CH3)-CH3 becomes a tree of
carbon atoms with bond orders. Hydrogen counts written in the text are checked against valence
(every carbon must have exactly four bonds), so a typo in a table is a rejection, not a guess.

Two ways to count the structural isomers of an alkane are here:
- `enumerate_alkanes(n)`: grow every tree one carbon at a time (maximum four bonds per carbon) and
  collapse copies with a canonical string (AHU encoding rooted at the centre of the tree);
- `otter_count(n)`: Polya counting of rooted trees with the Otter dissimilarity formula
  (vertex-rooted minus edge-rooted plus symmetric-edge-rooted), pure arithmetic, no trees built.
"""

from __future__ import annotations

import re
from collections import defaultdict
from fractions import Fraction
from functools import cache

from app.factory.lanes.chemistry.tables import ROOTS

Tree = dict[int, dict[int, int]]  # node -> {neighbour: bond order}


class StructureError(ValueError):
    pass


# ---------------------------------------------------------------- condensed formula parser

_GROUP = re.compile(r"C(H(\d*))?")
_BOND = {"-": 1, "=": 2, "≡": 3}


def parse_condensed(text: str) -> Tree:
    tree: Tree = defaultdict(dict)
    hydrogens: dict[int, int] = {}
    counter = [0]

    def chain(s: str, i: int, parent: int | None, first_order: int) -> None:
        prev = parent
        order = first_order
        while True:
            m = _GROUP.match(s, i)
            if not m:
                raise StructureError(f"expected a carbon group at {s[i:]!r}")
            node = counter[0]
            counter[0] += 1
            tree[node]
            hydrogens[node] = 0 if m.group(1) is None else int(m.group(2) or 1)
            if prev is not None:
                tree[node][prev] = order
                tree[prev][node] = order
            i = m.end()
            while i < len(s) and s[i] == "(":
                depth, j = 0, i
                while True:
                    if s[j] == "(":
                        depth += 1
                    elif s[j] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                inner = s[i + 1 : j]
                k = re.match(r"\d*", s[j + 1 :]).group()  # type: ignore[union-attr]
                for _ in range(int(k) if k else 1):
                    chain(inner, 0, node, 1)
                i = j + 1 + len(k)
            if i >= len(s):
                return
            if s[i] not in _BOND:
                raise StructureError(f"expected a bond at {s[i:]!r}")
            order = _BOND[s[i]]
            prev = node
            i += 1

    chain(text, 0, None, 1)
    for node, nbrs in tree.items():
        if sum(nbrs.values()) + hydrogens[node] != 4:
            raise StructureError(f"carbon {node} of {text!r} does not have four bonds")
    return dict(tree)


def carbon_count(tree: Tree) -> int:
    return len(tree)


# ---------------------------------------------------------------- naming (alkanes)


def _paths(tree: Tree) -> list[list[int]]:
    leaves = [n for n, nb in tree.items() if len(nb) <= 1] or list(tree)
    best: list[list[int]] = []
    longest = 0
    for start in leaves:
        # depth-first walk of every simple path from this leaf (trees: unique per end node)
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            ext = [nb for nb in tree[node] if nb not in path]
            if not ext:
                if len(path) > longest:
                    longest, best = len(path), []
                if len(path) == longest:
                    best.append(path)
            for nb in ext:
                stack.append((nb, [*path, nb]))
    return best


def _branch_name(tree: Tree, root: int, parent: int) -> str:
    """Name a side branch that is a straight chain of up to two carbons."""
    chain = [root]
    cur, prev = root, parent
    while True:
        nxt = [nb for nb in tree[cur] if nb != prev]
        if not nxt:
            break
        if len(nxt) > 1:
            raise StructureError("branched side chain is outside the lane")
        prev, cur = cur, nxt[0]
        chain.append(cur)
    if len(chain) == 1:
        return "methyl"
    if len(chain) == 2:
        return "ethyl"
    raise StructureError("side chain longer than ethyl is outside the lane")


_MULT = {1: "", 2: "di", 3: "tri", 4: "tetra", 5: "penta"}


def name_alkane(tree: Tree) -> str:
    if any(o != 1 for nb in tree.values() for o in nb.values()):
        raise StructureError("not a saturated chain")
    best: tuple[tuple[object, ...], list[tuple[int, str]], int] | None = None
    for path in _paths(tree):
        for oriented in (path, path[::-1]):
            subs: list[tuple[int, str]] = []
            on_path = set(oriented)
            for idx, node in enumerate(oriented, start=1):
                for nb in tree[node]:
                    if nb not in on_path:
                        subs.append((idx, _branch_name(tree, nb, node)))
            locs = sorted(i for i, _ in subs)
            first_alpha = [i for i, nme in sorted(subs, key=lambda t: (t[1], t[0]))]
            key = (-len(subs), locs, first_alpha)
            if best is None or key < best[0]:
                best = (key, subs, len(oriented))
    assert best is not None
    _, subs, length = best
    root = ROOTS[length] + "ane"
    if not subs:
        return root
    by_name: dict[str, list[int]] = defaultdict(list)
    for loc, nme in subs:
        by_name[nme].append(loc)
    parts = []
    for nme in sorted(by_name):
        locs = sorted(by_name[nme])
        parts.append(",".join(map(str, locs)) + "-" + _MULT[len(locs)] + nme)
    return "-".join(parts) + root


def alternative_numbering(tree: Tree) -> str | None:
    """The same chain and branches numbered from the wrong end (a named mistake), or None."""
    paths = _paths(tree)
    path = paths[0]
    on_path = set(path)
    subs_f: list[tuple[int, str]] = []
    for idx, node in enumerate(path, start=1):
        for nb in tree[node]:
            if nb not in on_path:
                subs_f.append((idx, _branch_name(tree, nb, node)))
    if not subs_f:
        return None
    n = len(path)
    subs_b = [(n + 1 - i, nm) for i, nm in subs_f]
    good = name_alkane(tree)
    for subs in (subs_f, subs_b):
        by: dict[str, list[int]] = defaultdict(list)
        for loc, nme in subs:
            by[nme].append(loc)
        text = (
            "-".join(
                ",".join(map(str, sorted(by[nme]))) + "-" + _MULT[len(by[nme])] + nme
                for nme in sorted(by)
            )
            + ROOTS[n]
            + "ane"
        )
        if text != good:
            return text
    return None


# ---------------------------------------------------------------- naming (straight unsaturated chains)


def name_unsaturated(tree: Tree) -> str:
    """Straight chain with exactly one double or one triple bond."""
    if any(len(nb) > 2 for nb in tree.values()):
        raise StructureError("branched chain is outside this naming rule")
    ends = [n for n, nb in tree.items() if len(nb) <= 1]
    order = [ends[0]]
    while len(order) < len(tree):
        nxt = [nb for nb in tree[order[-1]] if nb not in order]
        order.append(nxt[0])
    bonds = [tree[order[i]][order[i + 1]] for i in range(len(order) - 1)]
    multi = [(i + 1, b) for i, b in enumerate(bonds) if b > 1]
    if len(multi) != 1:
        raise StructureError("need exactly one multiple bond")
    pos, kind = multi[0]
    length = len(order)
    loc = min(pos, length - pos)
    suffix = "ene" if kind == 2 else "yne"
    root = ROOTS[length]
    if length <= 3:
        return root + suffix
    return f"{root}-{loc}-{suffix}"


# ---------------------------------------------------------------- functional groups (straight chain)

_TERMINAL = {"OH": "alcohol", "Cl": "haloalkane", "CHO": "aldehyde", "COOH": "carboxylic acid"}


def name_functional(text: str) -> tuple[str, int]:
    """Name of a straight chain ending in OH, Cl, CHO or COOH, and its carbon count."""
    pieces = text.split("-")
    last = pieces[-1]
    if last not in _TERMINAL:
        raise StructureError("unknown end group")
    group = _TERMINAL[last]
    body = pieces[:-1]
    carbons = 0
    for piece in body:
        if piece == "H":
            continue
        if not re.fullmatch(r"CH[23]", piece):
            raise StructureError(f"unexpected piece {piece!r}")
        carbons += 1
    if group in ("aldehyde", "carboxylic acid"):
        carbons += 1  # the carbon of CHO or COOH is part of the chain
    elif last in ("OH", "Cl") and carbons == 0:
        raise StructureError("no carbon")
    root = ROOTS[carbons]
    if group == "alcohol":
        return (root + "anol" if carbons < 3 else f"{root}an-1-ol"), carbons
    if group == "aldehyde":
        return root + "anal", carbons
    if group == "carboxylic acid":
        return root + "anoic acid", carbons
    return (f"chloro{root}ane" if carbons < 3 else f"1-chloro{root}ane"), carbons


def functional_formula(group: str, n: int) -> str:
    if group in ("aldehyde", "carboxylic acid"):
        end = "CHO" if group == "aldehyde" else "COOH"
        body = ["H"] if n == 1 else ["CH3", *["CH2"] * (n - 2)]
        return "-".join([*body, end])
    end = "OH" if group == "alcohol" else "Cl"
    body = ["CH3", *["CH2"] * (n - 1)]
    return "-".join([*body, end])


# ---------------------------------------------------------------- isomer counting, method 1: enumerate


def _canon(tree: dict[int, set[int]]) -> str:
    degree = {n: len(nb) for n, nb in tree.items()}
    leaves = [n for n, d in degree.items() if d <= 1]
    remaining = len(tree)
    layer = leaves
    removed: set[int] = set()
    while remaining > 2:
        remaining -= len(layer)
        nxt = []
        for leaf in layer:
            removed.add(leaf)
            for nb in tree[leaf]:
                if nb not in removed:
                    degree[nb] -= 1
                    if degree[nb] == 1:
                        nxt.append(nb)
        layer = nxt
    centres = [n for n in tree if n not in removed]

    def enc(node: int, parent: int | None) -> str:
        return "(" + "".join(sorted(enc(nb, node) for nb in tree[node] if nb != parent)) + ")"

    return min(enc(c, None) for c in centres)


def enumerate_alkanes(n: int) -> list[str]:
    """Canonical strings of every distinct carbon skeleton with n carbons (max four bonds each)."""
    trees: dict[str, dict[int, set[int]]] = {"()": {0: set()}}
    for size in range(2, n + 1):
        grown: dict[str, dict[int, set[int]]] = {}
        for tree in trees.values():
            for node in list(tree):
                if len(tree[node]) >= 4:
                    continue
                new = {k: set(v) for k, v in tree.items()}
                new[size - 1] = {node}
                new[node].add(size - 1)
                grown.setdefault(_canon(new), new)
        trees = grown
    return sorted(trees)


# ---------------------------------------------------------------- isomer counting, method 2: Otter


def _series_mul(a: list[int], b: list[int], limit: int) -> list[int]:
    out = [0] * (limit + 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if i + j <= limit:
                    out[i + j] += x * y
    return out


def _compose(a: list[int], k: int, limit: int) -> list[int]:
    """a(x^k)."""
    out = [0] * (limit + 1)
    for i, x in enumerate(a):
        if i * k <= limit:
            out[i * k] += x
    return out


@cache
def alkyl_counts(limit: int) -> tuple[int, ...]:
    """r[n]: rooted trees with n carbons whose every carbon has at most three children."""
    r = [0] * (limit + 1)
    for n in range(1, limit + 1):
        r[0] = 0
        r2 = _series_mul(r, r, limit)
        r3 = _series_mul(r2, r, limit)
        h1 = [Fraction(x) for x in r]
        h2 = [Fraction(x + y, 2) for x, y in zip(r2, _compose(r, 2, limit), strict=True)]
        h3 = [
            Fraction(x + 3 * y + 2 * z, 6)
            for x, y, z in zip(
                r3, _series_mul(r, _compose(r, 2, limit), limit), _compose(r, 3, limit), strict=True
            )
        ]
        total: list[Fraction] = [Fraction(0)] * (limit + 1)
        total[0] += 1
        for series in (h1, h2, h3):
            for i, x in enumerate(series):
                total[i] += x
        # r(x) = x * (1 + h1 + h2 + h3): the coefficient of x^n needs total[n-1]
        value = total[n - 1]
        if value.denominator != 1:
            raise ArithmeticError("non-integer count")
        r[n] = int(value)
    return tuple(r)


def otter_count(n: int) -> int:
    """Number of alkane skeletons with n carbons by Otter's formula."""
    limit = n
    r = list(alkyl_counts(limit))
    r2 = _series_mul(r, r, limit)
    r3 = _series_mul(r2, r, limit)
    r4 = _series_mul(r3, r, limit)
    c2, c3, c4 = _compose(r, 2, limit), _compose(r, 3, limit), _compose(r, 4, limit)
    h1 = [Fraction(x) for x in r]
    h2 = [Fraction(a + b, 2) for a, b in zip(r2, c2, strict=True)]
    h3 = [
        Fraction(a + 3 * b + 2 * c, 6)
        for a, b, c in zip(r3, _series_mul(r, c2, limit), c3, strict=True)
    ]
    rc2 = _series_mul(c2, c2, limit)
    h4 = [
        Fraction(a + 6 * b + 3 * c + 8 * d + 6 * e, 24)
        for a, b, c, d, e in zip(
            r4, _series_mul(r2, c2, limit), rc2, _series_mul(r, c3, limit), c4, strict=True
        )
    ]
    # vertex-rooted: a carbon with up to four alkyl neighbours
    vertex = Fraction(0)
    for series in (h1, h2, h3, h4):
        vertex += series[n - 1]
    vertex += 1 if n == 1 else 0
    edge = Fraction(r2[n] + c2[n], 2)  # unordered pair of alkyl trees joined by an edge
    symmetric = Fraction(r[n // 2] if n % 2 == 0 else 0)
    total = vertex - edge + symmetric
    if total.denominator != 1:
        raise ArithmeticError("non-integer isomer count")
    return int(total)

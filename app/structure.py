from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import math


@dataclass
class OrgEdge:
    owner: str
    owned: str
    share_pct: float
    voting_pct: float
    dividend_entitled: bool


@dataclass
class ConsolidationGroup:
    root_enterprise_id: int
    member_enterprise_ids: List[int]
    reason: str


def _pct(v: float) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def find_100pct_parent_map(ownership_rows) -> Dict[int, int]:
    """Map owned_enterprise_id -> owner_enterprise_id for strict 100% chains.

    We consider only ENTERPRISE->ENTERPRISE edges where:
      - share_pct == 100
      - voting_pct == 100 (or 0 meaning 'same as share')
    Dividend entitlement is *not* required for consolidation eligibility; that
    is handled separately by dividend rules.
    """
    parent: Dict[int, int] = {}
    for o in ownership_rows:
        if o.owner_kind != "ENTERPRISE" or not o.owner_enterprise_id:
            continue
        sp = _pct(o.share_pct)
        vp = _pct(o.voting_pct) if _pct(o.voting_pct) else sp
        if abs(sp - 100.0) < 1e-6 and abs(vp - 100.0) < 1e-6:
            # if multiple 100% parents exist, keep first; dossier should avoid that
            parent.setdefault(int(o.owned_enterprise_id), int(o.owner_enterprise_id))
    return parent


def build_consolidation_groups(case_enterprise_ids: Iterable[int], ownership_rows) -> List[ConsolidationGroup]:
    """Return consolidation groups based on strict 100% chains.

    Each enterprise belongs to one group anchored at the top-most parent in the
    100% chain (which itself may be owned by PERSON).
    """
    parent = find_100pct_parent_map(ownership_rows)

    def find_root(eid: int) -> int:
        seen: Set[int] = set()
        cur = eid
        while cur in parent and cur not in seen:
            seen.add(cur)
            cur = parent[cur]
        return cur

    groups: Dict[int, List[int]] = {}
    for eid in case_enterprise_ids:
        r = find_root(int(eid))
        groups.setdefault(r, []).append(int(eid))

    out: List[ConsolidationGroup] = []
    for root, members in sorted(groups.items(), key=lambda x: x[0]):
        members_sorted = sorted(set(members))
        reason = "100%-deelnemingen geconsolideerd" if len(members_sorted) > 1 else "enkelvoudige entiteit"
        out.append(ConsolidationGroup(root_enterprise_id=root, member_enterprise_ids=members_sorted, reason=reason))
    return out


def effective_control_pct(beneficial_map: Dict[int, Dict[str, float]], enterprise_id: int) -> float:
    """Return effective voting pct for an enterprise based on beneficial_map."""
    d = beneficial_map.get(int(enterprise_id), {})
    try:
        return float(d.get("voting_pct_total", 0.0))
    except Exception:
        return 0.0


def minority_participations(beneficial_map: Dict[int, Dict[str, float]], *, min_pct: float = 0.0001) -> List[int]:
    """Return enterprise_ids where applicant has >min_pct and <100% share."""
    out: List[int] = []
    for eid, d in beneficial_map.items():
        try:
            sp = float(d.get("share_pct_total", 0.0))
        except Exception:
            sp = 0.0
        if sp > min_pct and sp < 99.9999:
            out.append(int(eid))
    return sorted(set(out))


def max_withdrawable_working_capital(
    *,
    current_assets: float,
    current_liabilities: float,
    equity: float,
    total_assets: float,
    liquidity_min: float,
    solvability_min: float,
) -> float:
    """Approximation of 'maximaal te onttrekken vlottende activa'.

    We compute the maximum cash withdrawal w such that:
      (CA - w) / CL >= liquidity_min
      (EQ - w) / (TA - w) >= solvability_min

    Assumptions:
      - withdrawal reduces current assets, equity and total assets by the same amount
      - no tax effects

    This is a conservative bound used for reporting.
    """
    ca = float(current_assets)
    cl = float(current_liabilities)
    eq = float(equity)
    ta = float(total_assets)
    if ca <= 0 or ta <= 0:
        return 0.0

    # Liquidity bound
    w_liq = ca - (liquidity_min * cl)

    # Solvency bound: (eq-w)/(ta-w) >= s  => eq - w >= s(ta - w) => eq - w >= s ta - s w
    # => eq - s ta >= w(1 - s) => w <= (eq - s ta)/(1 - s)
    s = float(solvability_min)
    if s >= 1.0:
        w_sol = 0.0
    else:
        w_sol = (eq - s * ta) / (1.0 - s)

    # Also cannot withdraw more than current assets or equity
    w = min(w_liq, w_sol, ca, eq)
    if math.isnan(w) or w < 0:
        return 0.0
    return float(w)


def build_mermaid(case_name: str, nodes: List[Tuple[str, str]], edges: List[OrgEdge]) -> str:
    """Return Mermaid flowchart code.

    nodes: list of (node_id, label)
    edges: list of edges with share/vote/dividend
    """
    lines = ["flowchart TB"]
    lines.append(f"%% {case_name}")
    for nid, label in nodes:
        safe_label = label.replace("\"", "'")
        lines.append(f"{nid}[\"{safe_label}\"]")
    for e in edges:
        meta = f"{e.share_pct:.2f}% / {e.voting_pct:.2f}%".replace(".00%", "%")
        if not e.dividend_entitled:
            meta += " (geen dividend)"
        lines.append(f"{e.owner} -->|\"{meta}\"| {e.owned}")
    return "\n".join(lines) + "\n"


def render_organogram_png(
    *,
    out_path: Path,
    nodes: List[Tuple[str, str]],
    edges: List[OrgEdge],
    title: str = "Organogram",
) -> None:
    """Render a simple organogram PNG using matplotlib.

    This is intentionally simple (MVP). It provides a visual in the PDF.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Simple layered layout: BFS from PERSON node if exists
    # node ids are strings; we compute parents list
    children: Dict[str, List[str]] = {}
    parents: Dict[str, List[str]] = {}
    for e in edges:
        children.setdefault(e.owner, []).append(e.owned)
        parents.setdefault(e.owned, []).append(e.owner)

    root = "P"
    if root not in {nid for nid, _ in nodes}:
        root = nodes[0][0] if nodes else "P"

    # BFS levels
    level: Dict[str, int] = {root: 0}
    q = [root]
    while q:
        cur = q.pop(0)
        for ch in children.get(cur, []):
            if ch not in level:
                level[ch] = level[cur] + 1
                q.append(ch)

    # group by level
    by_level: Dict[int, List[str]] = {}
    for nid, _ in nodes:
        by_level.setdefault(level.get(nid, 99), []).append(nid)
    max_level = max(by_level.keys()) if by_level else 0

    # positions
    pos: Dict[str, Tuple[float, float]] = {}
    for lv in range(0, max_level + 1):
        ns = sorted(by_level.get(lv, []))
        if not ns:
            continue
        # spread horizontally
        for i, nid in enumerate(ns):
            x = (i + 1) / (len(ns) + 1)
            y = 1.0 - (lv / (max_level + 1 if max_level else 1))
            pos[nid] = (x, y)

    # fallback for nodes not reached
    if 99 in by_level:
        ns = sorted(by_level[99])
        for i, nid in enumerate(ns):
            pos[nid] = ((i + 1) / (len(ns) + 1), 0.05)

    fig = plt.figure(figsize=(11, 7))
    ax = plt.gca()
    ax.set_title(title)
    ax.axis("off")

    # draw edges
    for e in edges:
        if e.owner not in pos or e.owned not in pos:
            continue
        x1, y1 = pos[e.owner]
        x2, y2 = pos[e.owned]
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", lw=1),
        )
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        lbl = f"{e.share_pct:.0f}%" if abs(e.share_pct - round(e.share_pct)) < 1e-6 else f"{e.share_pct:.1f}%"
        if not e.dividend_entitled:
            lbl += " x"
        ax.text(mx, my, lbl, fontsize=8, ha="center", va="center")

    # draw nodes
    node_labels = {nid: label for nid, label in nodes}
    for nid, (x, y) in pos.items():
        label = node_labels.get(nid, nid)
        ax.scatter([x], [y], s=800)
        ax.text(x, y, label, fontsize=9, ha="center", va="center", color="white", wrap=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)

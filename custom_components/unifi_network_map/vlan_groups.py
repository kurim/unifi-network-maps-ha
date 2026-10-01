"""Group map nodes into VLAN boxes, one per VLAN and physical parent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from unifi_topology.model import group_nodes_by_vlan

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from unifi_topology import Edge

INFRASTRUCTURE_NODE_TYPES = frozenset({"gateway", "switch", "ap"})
UNASSIGNED_GROUP = "Unassigned"


@dataclass(frozen=True)
class VlanGroups:
    """Groups in the shape the renderer takes: members, order, VLAN ids."""

    groups: dict[str, list[str]]
    order: list[str]
    vlan_ids: dict[str, int]


def build_vlan_groups(
    edges: list[Edge],
    node_types: Mapping[str, str],
    node_names: Mapping[str, str] | None,
    vlan_names: Mapping[int, str],
    node_vlans: Mapping[str, int | None] | None,
) -> VlanGroups:
    """Box each VLAN's clients per switch/AP they are connected to.

    Infrastructure devices (gateway, switch, AP) are never boxed: they
    typically carry every VLAN on their trunk/uplink ports, so no single
    VLAN describes them. A client's VLAN is the one the controller reports
    for it (the same value the detail panel shows); only when that is
    unknown does the VLAN tagged on its edge stand in. Splitting by
    immediate parent gives every box a place directly under that parent in
    the topology tree, instead of one box spanning unrelated switches.
    """
    vlan_of = _client_vlans(edges, node_types, vlan_names, node_vlans or {})
    parent_of = {edge.right: edge.left for edge in edges}
    labels = node_names or {}
    buckets: dict[tuple[int | None, str], list[str]] = {}
    for node, vlan_id in vlan_of.items():
        buckets.setdefault((vlan_id, parent_of.get(node, "")), []).append(node)
    return _named_groups(buckets, vlan_names, labels)


def _client_vlans(
    edges: list[Edge],
    node_types: Mapping[str, str],
    vlan_names: Mapping[int, str],
    node_vlans: Mapping[str, int | None],
) -> dict[str, int | None]:
    edge_vlans = _edge_vlans(edges, vlan_names)
    nodes = {node for edge in edges for node in (edge.left, edge.right)}
    return {
        node: _first_known(
            node_vlans.get(node.strip().lower()), edge_vlans.get(node)
        )
        for node in sorted(nodes)
        if node_types.get(node) not in INFRASTRUCTURE_NODE_TYPES
    }


def _edge_vlans(
    edges: list[Edge], vlan_names: Mapping[int, str]
) -> dict[str, int]:
    """The VLAN each node's edges carry, as the topology library infers it."""
    groups, _order, group_vlan_ids = group_nodes_by_vlan(
        edges, dict(vlan_names)
    )
    return {
        member: group_vlan_ids[name]
        for name, members in groups.items()
        if name in group_vlan_ids
        for member in members
    }


def _first_known(*candidates: int | None) -> int | None:
    return next((value for value in candidates if value is not None), None)


def _named_groups(
    buckets: dict[tuple[int | None, str], list[str]],
    vlan_names: Mapping[int, str],
    labels: Mapping[str, str],
) -> VlanGroups:
    groups: dict[str, list[str]] = {}
    vlan_ids: dict[str, int] = {}
    parent_by_name: dict[str, str] = {}
    for vlan_id, parent in sorted(buckets, key=_bucket_order(labels)):
        name = _group_name(vlan_id, parent, vlan_names, labels)
        if parent_by_name.get(name, parent) != parent:
            name = f"{name} [{parent}]"
        parent_by_name[name] = parent
        groups[name] = buckets[(vlan_id, parent)]
        if vlan_id is not None:
            vlan_ids[name] = vlan_id
    return VlanGroups(groups=groups, order=list(groups), vlan_ids=vlan_ids)


def _bucket_order(
    labels: Mapping[str, str],
) -> Callable[[tuple[int | None, str]], tuple[bool, int, str]]:
    def key(bucket: tuple[int | None, str]) -> tuple[bool, int, str]:
        vlan_id, parent = bucket
        return (
            vlan_id is None,
            vlan_id or 0,
            (labels.get(parent) or parent).lower(),
        )

    return key


def _group_name(
    vlan_id: int | None,
    parent: str,
    vlan_names: Mapping[int, str],
    labels: Mapping[str, str],
) -> str:
    base = (
        UNASSIGNED_GROUP
        if vlan_id is None
        else vlan_names.get(vlan_id, f"VLAN {vlan_id}")
    )
    if not parent:
        return base
    return f"{base} ({labels.get(parent) or parent})"

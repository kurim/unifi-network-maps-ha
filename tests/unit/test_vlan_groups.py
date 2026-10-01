"""Tests for per-parent VLAN grouping."""

from __future__ import annotations

from unifi_topology import Edge

from custom_components.unifi_network_map.vlan_groups import build_vlan_groups

TYPES = {
    "gw": "gateway",
    "sw1": "switch",
    "sw2": "switch",
    "ap": "ap",
    "a": "client",
    "b": "client",
    "c": "client",
}
VLAN_NAMES = {1: "LAN", 20: "Guest"}


def _edges(*pairs: tuple[str, str], vlans: tuple[int, ...] = ()) -> list[Edge]:
    return [
        Edge(left=left, right=right, vlans=vlans, active_vlans=vlans)
        for left, right in pairs
    ]


def test_boxes_clients_per_parent_and_vlan() -> None:
    edges = _edges(
        ("gw", "sw1"), ("gw", "sw2"), ("sw1", "a"), ("sw1", "b"), ("sw2", "c")
    )
    result = build_vlan_groups(
        edges, TYPES, None, VLAN_NAMES, {"a": 1, "b": 20, "c": 1}
    )
    assert result.groups == {
        "LAN (sw1)": ["a"],
        "LAN (sw2)": ["c"],
        "Guest (sw1)": ["b"],
    }
    assert result.order == ["LAN (sw1)", "LAN (sw2)", "Guest (sw1)"]
    assert result.vlan_ids == {
        "LAN (sw1)": 1,
        "LAN (sw2)": 1,
        "Guest (sw1)": 20,
    }


def test_infrastructure_is_never_boxed() -> None:
    edges = _edges(("gw", "sw1"), ("sw1", "ap"), ("ap", "a"), vlans=(1,))
    result = build_vlan_groups(edges, TYPES, None, VLAN_NAMES, {})
    members = {node for nodes in result.groups.values() for node in nodes}
    assert members == {"a"}


def test_client_vlan_wins_over_edge_vlan() -> None:
    """The controller's VLAN for the client is what the detail panel shows,
    so it decides the box even when the edge carries another (or no) tag.
    """
    edges = _edges(("sw1", "a"), vlans=(20,))
    result = build_vlan_groups(edges, TYPES, None, VLAN_NAMES, {"a": 1})
    assert list(result.groups) == ["LAN (sw1)"]


def test_edge_vlan_stands_in_when_client_vlan_unknown() -> None:
    edges = _edges(("sw1", "a"), vlans=(20,))
    result = build_vlan_groups(edges, TYPES, None, VLAN_NAMES, {"a": None})
    assert list(result.groups) == ["Guest (sw1)"]


def test_client_with_a_known_vlan_is_not_unassigned_without_edge_tags() -> (
    None
):
    """Wired clients often have untagged edges; the client VLAN must not be
    lost to an "Unassigned" box because of that.
    """
    edges = _edges(("sw1", "a"), ("sw1", "b"))
    result = build_vlan_groups(
        edges, TYPES, None, VLAN_NAMES, {"a": 1, "b": 1}
    )
    assert list(result.groups) == ["LAN (sw1)"]
    assert result.groups["LAN (sw1)"] == ["a", "b"]


def test_unknown_vlan_goes_to_unassigned_last() -> None:
    edges = _edges(("sw1", "a"), ("sw1", "b"))
    result = build_vlan_groups(edges, TYPES, None, VLAN_NAMES, {"a": 1})
    assert result.order == ["LAN (sw1)", "Unassigned (sw1)"]
    assert "Unassigned (sw1)" not in result.vlan_ids


def test_node_vlans_lookup_ignores_mac_case() -> None:
    edges = _edges(("sw1", "AA:BB"))
    result = build_vlan_groups(
        edges,
        {"sw1": "switch", "AA:BB": "client"},
        None,
        VLAN_NAMES,
        {"aa:bb": 1},
    )
    assert list(result.groups) == ["LAN (sw1)"]


def test_box_label_uses_the_parents_display_name() -> None:
    edges = _edges(("f4:e2:c6:ae:13:ef", "a"))
    types = {"f4:e2:c6:ae:13:ef": "switch", "a": "client"}
    result = build_vlan_groups(
        edges, types, {"f4:e2:c6:ae:13:ef": "USW Ultra"}, VLAN_NAMES, {"a": 1}
    )
    assert list(result.groups) == ["LAN (USW Ultra)"]


def test_parents_sharing_a_display_name_keep_separate_boxes() -> None:
    edges = _edges(("sw1", "a"), ("sw2", "b"))
    result = build_vlan_groups(
        edges,
        TYPES,
        {"sw1": "Switch", "sw2": "Switch"},
        VLAN_NAMES,
        {"a": 1, "b": 1},
    )
    assert len(result.groups) == 2
    assert {tuple(members) for members in result.groups.values()} == {
        ("a",),
        ("b",),
    }


def test_client_without_a_parent_edge_keeps_the_plain_vlan_name() -> None:
    edges = _edges(("a", "sw1"))
    result = build_vlan_groups(edges, TYPES, None, VLAN_NAMES, {"a": 1})
    assert result.groups == {"LAN": ["a"]}


def test_unnamed_vlan_falls_back_to_its_id() -> None:
    edges = _edges(("sw1", "a"))
    result = build_vlan_groups(edges, TYPES, None, {}, {"a": 7})
    assert list(result.groups) == ["VLAN 7 (sw1)"]

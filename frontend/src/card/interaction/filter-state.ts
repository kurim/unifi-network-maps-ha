import type { DeviceType, DeviceTypeFilters } from "../core/types";

/**
 * Client subtypes from the unifi-topology payload.
 * These are all filtered together under the "client" filter button.
 */
export const CLIENT_SUBTYPES = [
  "client",
  "camera",
  "tv",
  "phone",
  "printer",
  "nas",
  "speaker",
  "game_console",
  "iot",
  "client_cluster",
] as const;

export function createFilterState(): DeviceTypeFilters {
  return {
    gateway: true,
    switch: true,
    ap: true,
    client: true,
    other: true,
  };
}

export function toggleFilter(state: DeviceTypeFilters, type: DeviceType): DeviceTypeFilters {
  return {
    ...state,
    [type]: !state[type],
  };
}

export function enableFilter(state: DeviceTypeFilters, type: DeviceType): DeviceTypeFilters {
  if (state[type]) {
    return state;
  }
  return {
    ...state,
    [type]: true,
  };
}

export function normalizeDeviceType(type: string): DeviceType {
  if (type === "gateway" || type === "switch" || type === "ap") {
    return type;
  }
  if ((CLIENT_SUBTYPES as readonly string[]).includes(type)) {
    return "client";
  }
  return "other";
}

/** Id the SVG gives the edge that runs into a group's box (`::group::<name>`). */
export const GROUP_EDGE_PREFIX = "::group::";

/**
 * Hides each group box whose members are all filtered out, and returns the
 * edge ids that run into those boxes so they can be hidden with them.
 */
export function applyGroupFilters(svg: SVGElement, hiddenNodes: Set<string>): Set<string> {
  const members = new Map<string, string[]>();
  svg.querySelectorAll("[data-node-id][data-group]").forEach((element) => {
    const group = element.getAttribute("data-group");
    const nodeId = element.getAttribute("data-node-id");
    if (!group || !nodeId) return;
    members.set(group, [...(members.get(group) ?? []), nodeId]);
  });

  const hiddenGroupEdges = new Set<string>();
  svg.querySelectorAll(".network-group[data-group-name]").forEach((box) => {
    const name = box.getAttribute("data-group-name") ?? "";
    const ids = members.get(name) ?? [];
    const hidden = ids.length > 0 && ids.every((id) => hiddenNodes.has(id));
    box.classList.toggle("group--filtered", hidden);
    if (hidden) hiddenGroupEdges.add(`${GROUP_EDGE_PREFIX}${name}`);
  });
  return hiddenGroupEdges;
}

import {
  applyGroupFilters,
  createFilterState,
  toggleFilter,
  enableFilter,
  normalizeDeviceType,
} from "../card/interaction/filter-state";

describe("filter-state", () => {
  describe("createFilterState", () => {
    it("creates state with all filters enabled", () => {
      const state = createFilterState();
      expect(state).toEqual({
        gateway: true,
        switch: true,
        ap: true,
        client: true,
        other: true,
      });
    });
  });

  describe("toggleFilter", () => {
    it("toggles filter from true to false", () => {
      const state = createFilterState();
      const result = toggleFilter(state, "gateway");
      expect(result.gateway).toBe(false);
      // Other filters unchanged
      expect(result.switch).toBe(true);
      expect(result.ap).toBe(true);
    });

    it("toggles filter from false to true", () => {
      const state = { ...createFilterState(), gateway: false };
      const result = toggleFilter(state, "gateway");
      expect(result.gateway).toBe(true);
    });

    it("returns new object (immutable)", () => {
      const state = createFilterState();
      const result = toggleFilter(state, "gateway");
      expect(result).not.toBe(state);
    });

    it("toggles each device type correctly", () => {
      const types = ["gateway", "switch", "ap", "client", "other"] as const;
      for (const type of types) {
        const state = createFilterState();
        const result = toggleFilter(state, type);
        expect(result[type]).toBe(false);
      }
    });
  });

  describe("enableFilter", () => {
    it("returns same object if already enabled", () => {
      const state = createFilterState();
      const result = enableFilter(state, "gateway");
      expect(result).toBe(state); // Same reference
    });

    it("enables disabled filter", () => {
      const state = { ...createFilterState(), gateway: false };
      const result = enableFilter(state, "gateway");
      expect(result.gateway).toBe(true);
    });

    it("returns new object when enabling", () => {
      const state = { ...createFilterState(), gateway: false };
      const result = enableFilter(state, "gateway");
      expect(result).not.toBe(state);
    });

    it("enables each device type correctly", () => {
      const types = ["gateway", "switch", "ap", "client", "other"] as const;
      for (const type of types) {
        const state = { ...createFilterState(), [type]: false };
        const result = enableFilter(state, type);
        expect(result[type]).toBe(true);
      }
    });
  });

  describe("normalizeDeviceType", () => {
    it("returns gateway for gateway", () => {
      expect(normalizeDeviceType("gateway")).toBe("gateway");
    });

    it("returns switch for switch", () => {
      expect(normalizeDeviceType("switch")).toBe("switch");
    });

    it("returns ap for ap", () => {
      expect(normalizeDeviceType("ap")).toBe("ap");
    });

    it("returns client for client", () => {
      expect(normalizeDeviceType("client")).toBe("client");
    });

    it("returns other for unknown types", () => {
      expect(normalizeDeviceType("router")).toBe("other");
      expect(normalizeDeviceType("unknown")).toBe("other");
      expect(normalizeDeviceType("")).toBe("other");
      expect(normalizeDeviceType("firewall")).toBe("other");
    });
  });
});

describe("applyGroupFilters", () => {
  const buildSvg = (): SVGElement => {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg">
      <g class="network-group" data-group-name="LAN (sw1)"></g>
      <g class="network-group" data-group-name="IoT (sw1)"></g>
      <g data-node-id="a" data-group="LAN (sw1)"></g>
      <g data-node-id="b" data-group="LAN (sw1)"></g>
      <g data-node-id="c" data-group="IoT (sw1)"></g>
    </svg>`;
    return wrapper.querySelector("svg") as SVGElement;
  };

  it("hides a box and returns its edge id once every member is hidden", () => {
    const svg = buildSvg();
    const hidden = applyGroupFilters(svg, new Set(["a", "b"]));
    expect([...hidden]).toEqual(["::group::LAN (sw1)"]);
    const boxes = svg.querySelectorAll(".network-group");
    expect(boxes[0].classList.contains("group--filtered")).toBe(true);
    expect(boxes[1].classList.contains("group--filtered")).toBe(false);
  });

  it("keeps a box with at least one visible member", () => {
    const svg = buildSvg();
    expect(applyGroupFilters(svg, new Set(["a"])).size).toBe(0);
    expect(svg.querySelector(".group--filtered")).toBeNull();
  });

  it("shows the box again when the filter is switched back", () => {
    const svg = buildSvg();
    applyGroupFilters(svg, new Set(["a", "b"]));
    applyGroupFilters(svg, new Set());
    expect(svg.querySelector(".group--filtered")).toBeNull();
  });

  it("ignores boxes without tagged members", () => {
    const svg = buildSvg();
    svg.insertAdjacentHTML("beforeend", '<g class="network-group" data-group-name="Empty"></g>');
    expect(applyGroupFilters(svg, new Set(["a", "b", "c"])).has("::group::Empty")).toBe(false);
  });
});

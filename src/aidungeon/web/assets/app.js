(() => {
  const state = {
    dungeon: null,
    currentRoom: 0,
    visited: new Set([0]),
  };

  const elements = {
    roomLabel: document.querySelector("[data-room-label]"),
    roomName: document.querySelector("[data-room-name]"),
    roomDescription: document.querySelector("[data-room-description]"),
    roomTags: document.querySelector("[data-room-tags]"),
    connections: document.querySelector("[data-connections]"),
    items: document.querySelector("[data-items]"),
    monsters: document.querySelector("[data-monsters]"),
    breadcrumbs: document.querySelector("[data-breadcrumbs]"),
    resetButton: document.querySelector("[data-reset]"),
    canvas: document.querySelector("[data-map]"),
    statusDistance: document.querySelector("[data-status-distance]"),
    statusRooms: document.querySelector("[data-status-rooms]"),
  };

  const renderEntityList = (target, entities, emptyMessage) => {
    if (!target) return;
    target.innerHTML = "";
    if (!entities || !entities.length) {
      const li = document.createElement("li");
      li.className = "entity-empty";
      li.textContent = emptyMessage;
      target.appendChild(li);
      return;
    }
    entities.forEach((entity) => {
      const li = document.createElement("li");
      const title = document.createElement("span");
      title.className = "entity-title";
      const quantity = entity.quantity && entity.quantity > 1 ? ` (x${entity.quantity})` : "";
      title.textContent = `${entity.label}${quantity}`;
      const desc = document.createElement("span");
      desc.className = "entity-desc";
      desc.textContent = entity.description || "No description.";
      li.appendChild(title);
      li.appendChild(desc);
      target.appendChild(li);
    });
  };

  const fetchDungeon = async (opts = {}) => {
    const params = opts.reload ? "?reload=1" : "";
    const response = await fetch(`/api/dungeon${params}`);
    if (!response.ok) {
      throw new Error(`Failed to load dungeon: ${response.status}`);
    }
    return response.json();
  };

  const renderRoom = () => {
    if (!state.dungeon) return;
    const room = state.dungeon.rooms[state.currentRoom];
    if (!room) return;

    state.visited.add(room.id);

    elements.roomLabel.textContent = `Room ${room.id}`;
    elements.roomName.textContent = room.label;
    elements.roomDescription.textContent = room.description || "No narrative available.";

    elements.roomTags.innerHTML = "";
    if (room.tags && room.tags.length) {
      room.tags.forEach((tag) => {
        const span = document.createElement("span");
        span.textContent = tag;
        elements.roomTags.appendChild(span);
      });
    }

    renderEntityList(elements.items, room.items, "No items discovered.");
    renderEntityList(elements.monsters, room.monsters, "No monsters detected.");

    elements.connections.innerHTML = "";
    const neighbors = state.dungeon.adjacency[room.id] || [];
    const directionMap = state.dungeon.directions[room.id] || {};
    neighbors.forEach((neighborId) => {
      const nextRoom = state.dungeon.rooms[neighborId];
      const button = document.createElement("button");
      button.type = "button";
      const directionName = (directionMap[neighborId] || "").toLowerCase();
      const keyHint = directionName ? keyDirectionHints[directionName] || "" : "";
      const directionLabel = directionName ? `${directionName.toUpperCase()} → ` : "→ ";
      const hintLabel = keyHint ? ` [${keyHint}]` : "";
      button.textContent = `${directionLabel}${nextRoom.label}${hintLabel}`;
      button.addEventListener("click", () => {
        state.currentRoom = neighborId;
        renderRoom();
        renderBreadcrumbs();
        renderMap();
      });
      elements.connections.appendChild(button);
    });

    elements.statusRooms.textContent = `Rooms: ${Object.keys(state.dungeon.rooms).length}`;
  };

  const renderBreadcrumbs = () => {
    if (!state.dungeon) return;
    const room = state.dungeon.rooms[state.currentRoom];
    const trail = room.trail || [];
    elements.breadcrumbs.textContent = `Path: start${trail.length ? " → " + trail.join(" → ") : ""}`;
    elements.statusDistance.textContent = `Steps: ${trail.length}`;
  };

  const renderMap = () => {
    const canvas = elements.canvas;
    if (!canvas || !state.dungeon) return;
    const ctx = canvas.getContext("2d");
    const rooms = Object.values(state.dungeon.rooms);
    const padding = 40;
    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height = canvas.offsetHeight;

    const xs = rooms.map((room) => room.position[0]);
    const ys = rooms.map((room) => room.position[1]);
    const minX = Math.min(...xs);
    const minY = Math.min(...ys);
    const maxX = Math.max(...xs);
    const maxY = Math.max(...ys);

    const spanX = maxX - minX || 1;
    const spanY = maxY - minY || 1;
    const scale = Math.min(
      (width - padding * 2) / spanX,
      (height - padding * 2) / spanY
    );

    const project = (room) => ({
      x: padding + (room.position[0] - minX) * scale,
      y: height - padding - (room.position[1] - minY) * scale,
    });

    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = "rgba(77, 182, 172, 0.35)";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";

    ctx.beginPath();
    rooms.forEach((room) => {
      const neighbors = state.dungeon.adjacency[room.id] || [];
      const point = project(room);
      neighbors.forEach((neighborId) => {
        const neighbor = state.dungeon.rooms[neighborId];
        const target = project(neighbor);
        ctx.moveTo(point.x, point.y);
        ctx.lineTo(target.x, target.y);
      });
    });
    ctx.stroke();

    rooms.forEach((room) => {
      const point = project(room);
      const visited = state.visited.has(room.id);
      const isActive = room.id === state.currentRoom;
      ctx.beginPath();
      ctx.fillStyle = isActive
        ? "#ff8a65"
        : visited
        ? "#4db6ac"
        : "rgba(77, 182, 172, 0.25)";
      ctx.shadowBlur = isActive ? 18 : visited ? 8 : 0;
      ctx.shadowColor = ctx.fillStyle;
      ctx.arc(point.x, point.y, isActive ? 7 : 5, 0, Math.PI * 2);
      ctx.fill();

      if (!visited) {
        return;
      }

      const hasItems = room.items && room.items.length;
      const hasMonsters = room.monsters && room.monsters.length;
      ctx.shadowBlur = 0;
      if (hasItems) {
        ctx.fillStyle = "#ffd54f";
        ctx.fillRect(point.x - 9, point.y - 14, 6, 6);
      }
      if (hasMonsters) {
        ctx.fillStyle = "#ef5350";
        ctx.beginPath();
        ctx.moveTo(point.x + 5, point.y + 8);
        ctx.lineTo(point.x + 11, point.y + 14);
        ctx.lineTo(point.x - 1, point.y + 14);
        ctx.closePath();
        ctx.fill();
      }
    });
    ctx.shadowBlur = 0;
  };

  const normalizeDungeon = (raw) => {
    const rooms = {};
    Object.entries(raw.rooms || {}).forEach(([id, room]) => {
      const numericId = Number(id);
      const items = Array.isArray(room.items) ? room.items : [];
      const monsters = Array.isArray(room.monsters) ? room.monsters : [];
      rooms[numericId] = {
        ...room,
        id: numericId,
        position: room.position || [0, 0],
        tags: room.tags || [],
        trail: room.trail || [],
        items: items.map((entity) => ({
          ...entity,
          tags: entity.tags || [],
          description: entity.description || "",
          quantity: Number(entity.quantity) || 1,
        })),
        monsters: monsters.map((entity) => ({
          ...entity,
          tags: entity.tags || [],
          description: entity.description || "",
          quantity: Number(entity.quantity) || 1,
        })),
      };
    });
    const adjacency = {};
    Object.entries(raw.adjacency || {}).forEach(([id, neighbors]) => {
      adjacency[Number(id)] = (neighbors || []).map((value) => Number(value));
    });
    const directions = {};
    Object.entries(raw.directions || {}).forEach(([id, neighbors]) => {
      const numericId = Number(id);
      directions[numericId] = {};
      Object.entries(neighbors || {}).forEach(([neighborId, direction]) => {
        directions[numericId][Number(neighborId)] = direction;
      });
    });
    return { ...raw, rooms, adjacency, directions };
  };

  const keyDirectionMap = {
    w: "north",
    a: "west",
    s: "south",
    d: "east",
  };

  const keyDirectionHints = {
    north: "W",
    south: "S",
    east: "D",
    west: "A",
  };

  const tryMove = (directionName) => {
    if (!state.dungeon) return;
    const roomDirections = state.dungeon.directions[state.currentRoom] || {};
    const entry = Object.entries(roomDirections).find(([, dir]) => dir.toLowerCase() === directionName);
    if (!entry) return;
    const [neighborId] = entry;
    state.currentRoom = Number(neighborId);
    renderRoom();
    renderBreadcrumbs();
    renderMap();
  };

  const loadDungeon = async (opts = {}) => {
    try {
      document.body.classList.add("loading");
      const rawDungeon = await fetchDungeon(opts);
      state.dungeon = normalizeDungeon(rawDungeon);
      state.currentRoom = 0;
      state.visited = new Set([0]);
      renderRoom();
      renderBreadcrumbs();
      renderMap();
    } catch (error) {
      console.error(error);
      alert("Failed to load dungeon. Check the server logs for details.");
    } finally {
      document.body.classList.remove("loading");
    }
  };

  elements.resetButton.addEventListener("click", () => loadDungeon({ reload: true }));

  window.addEventListener("resize", () => renderMap());

  window.addEventListener("keydown", (event) => {
    if (!state.dungeon) return;
    const directionName = keyDirectionMap[event.key.toLowerCase()];
    if (!directionName) return;
    event.preventDefault();
    tryMove(directionName);
  });

  loadDungeon();
})();

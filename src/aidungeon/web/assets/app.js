(() => {
  const state = { dungeon: null, currentRoom: 0, visited: new Set([0]) };

  // Список всех «торгуемых» предметов (синхронен default_config.toml)
  const ALL_ITEM_NAMES = [
    "Torch", "Potion of Healing", "Empty Map", "Emerald",
    "Ender Pearl", "Redstone Dust", "Bone", "Coal"
  ];

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
    tradeBox: document.querySelector("[data-trade]"),
    tradeOffers: document.querySelector("[data-trade-offers]"),
    tradeResult: document.querySelector("[data-trade-result]"),
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
      const spacer = document.createTextNode(" — ");
      li.appendChild(title);
      li.appendChild(spacer);
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

  const rngPick = (arr, k) => {
    const pool = [...arr];
    const out = [];
    for (let i = 0; i < Math.min(k, pool.length); i++) {
      const idx = Math.floor(Math.random() * pool.length);
      out.push(pool.splice(idx, 1)[0]);
    }
    return out;
  };

  const renderTrade = (room) => {
    if (!elements.tradeBox) return;

    if (room.symbol !== "V") {
      elements.tradeBox.hidden = true;
      elements.tradeOffers.innerHTML = "";
      elements.tradeResult.textContent = "";
      return;
    }

    elements.tradeBox.hidden = false;
    elements.tradeOffers.innerHTML = "";
    elements.tradeResult.textContent = "";

    const offers = rngPick(ALL_ITEM_NAMES, 3);
    offers.forEach((name) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = name;
      btn.addEventListener("click", () => {
        elements.tradeResult.textContent = `You decided not to buy and just steal "${name}"!!!`;
      });
      elements.tradeOffers.appendChild(btn);
    });
  };

  // ✅ оставляем только одно объявление
  const keyDirectionMap = { w: "north", a: "west", s: "south", d: "east" };
  const keyDirectionHints = { north: "W", south: "S", east: "D", west: "A" };

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

    // >>> Villager Trader Post
    renderTrade(room);

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
      const keyHint = keyDirectionHints[directionName] || "";
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

    if (ctx.imageSmoothingEnabled !== undefined) {
      ctx.imageSmoothingEnabled = false;
    }

    const rooms = Object.values(state.dungeon.rooms);
    const padding = 40;
    const width = (canvas.width = canvas.offsetWidth);
    const height = (canvas.height = canvas.offsetHeight);

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
      x: Math.round(padding + (room.position[0] - minX) * scale),
      y: Math.round(height - padding - (room.position[1] - minY) * scale),
    });

    ctx.clearRect(0, 0, width, height);

    // Рёбра
    ctx.strokeStyle = "rgba(105, 184, 59, 0.45)";
    ctx.lineWidth = 2;
    ctx.lineCap = "butt";
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

    // Узлы
    rooms.forEach((room) => {
      const point = project(room);
      const visited = state.visited.has(room.id);
      const isActive = room.id === state.currentRoom;

      ctx.beginPath();
      ctx.fillStyle = isActive ? "#ff8a65" : visited ? "#69b83b" : "rgba(105, 184, 59, 0.25)";
      ctx.fillRect(point.x - (isActive ? 5 : 4), point.y - (isActive ? 5 : 4), (isActive ? 10 : 8), (isActive ? 10 : 8));

      if (!visited) return;

      const hasItems = room.items && room.items.length;
      const hasMonsters = room.monsters && room.monsters.length;

      if (hasItems) {
        ctx.fillStyle = "#ffd54f";
        ctx.fillRect(point.x - 10, point.y - 14, 6, 6);
      }
      if (hasMonsters) {
        ctx.fillStyle = "#ef5350";
        ctx.fillRect(point.x + 6, point.y + 6, 6, 6);
      }
    });
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
      alert("Failed to load dungeon.\nCheck the server logs for details.");
    } finally {
      document.body.classList.remove("loading");
    }
  };

  // ✅ оставляем только слушатель клавиш
  window.addEventListener("keydown", (event) => {
    if (!state.dungeon) return;
    const directionName = keyDirectionMap[event.key.toLowerCase()];
    if (!directionName) return;
    event.preventDefault();
    tryMove(directionName);
  });

  elements.resetButton.addEventListener("click", () => loadDungeon({ reload: true }));
  window.addEventListener("resize", () => renderMap());

  loadDungeon();
})();

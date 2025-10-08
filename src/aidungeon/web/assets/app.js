(() => {
  const state = {
    dungeon: null,
    currentRoom: 0,
  };

  const elements = {
    roomLabel: document.querySelector("[data-room-label]"),
    roomName: document.querySelector("[data-room-name]"),
    roomDescription: document.querySelector("[data-room-description]"),
    roomTags: document.querySelector("[data-room-tags]"),
    connections: document.querySelector("[data-connections]"),
    breadcrumbs: document.querySelector("[data-breadcrumbs]"),
    resetButton: document.querySelector("[data-reset]"),
    canvas: document.querySelector("[data-map]"),
    statusDistance: document.querySelector("[data-status-distance]"),
    statusRooms: document.querySelector("[data-status-rooms]"),
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

    elements.connections.innerHTML = "";
    const neighbors = state.dungeon.adjacency[room.id] || [];
    neighbors.forEach((neighborId) => {
      const nextRoom = state.dungeon.rooms[neighborId];
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `➡ ${nextRoom.label}`;
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
      const isActive = room.id === state.currentRoom;
      ctx.beginPath();
      ctx.fillStyle = isActive ? "#ff8a65" : "#4db6ac";
      ctx.shadowBlur = isActive ? 18 : 8;
      ctx.shadowColor = ctx.fillStyle;
      ctx.arc(point.x, point.y, isActive ? 7 : 5, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.shadowBlur = 0;
  };

  const loadDungeon = async (opts = {}) => {
    try {
      document.body.classList.add("loading");
      state.dungeon = await fetchDungeon(opts);
      state.currentRoom = 0;
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

  loadDungeon();
})();

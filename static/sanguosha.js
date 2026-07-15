// View switcher logic
document.getElementById("show-qa-btn").addEventListener("click", () => {
    document.getElementById("sgs-area").style.display = "none";
    document.querySelector(".chat-area").style.display = "flex";
    document.querySelector(".sidebar-content").style.display = "block";
    document.querySelector(".sidebar-footer").style.display = "block";
    document.getElementById("show-qa-btn").className = "btn btn-primary";
    document.getElementById("show-sgs-btn").className = "btn btn-secondary";
});

document.getElementById("show-sgs-btn").addEventListener("click", () => {
    document.querySelector(".chat-area").style.display = "none";
    document.querySelector(".sidebar-content").style.display = "none";
    document.querySelector(".sidebar-footer").style.display = "none";
    document.getElementById("sgs-area").style.display = "flex";
    document.getElementById("show-qa-btn").className = "btn btn-secondary";
    document.getElementById("show-sgs-btn").className = "btn btn-primary";
});

// Sanguosha Multiplayer State
let sgsSocket = null;
let myPlayerName = "";
let currentRoomId = "";
let gameState = null;
let selectedCardId = null;
let selectedTargetName = null;
let activeConversion = null; // "SHA" or "SHAN"

const lobbyEl = document.getElementById("sgs-lobby");
const waitingEl = document.getElementById("sgs-waiting");
const boardEl = document.getElementById("sgs-board");
const roomBadge = document.getElementById("sgs-room-badge");
const leaveBtn = document.getElementById("leave-sgs-btn");

// Join room handler
document.getElementById("sgs-join-btn").addEventListener("click", () => {
    let nameInput = document.getElementById("sgs-player-name").value.trim();
    if (!nameInput) {
        nameInput = "将领_" + Math.floor(Math.random() * 900 + 100);
        document.getElementById("sgs-player-name").value = nameInput;
    }
    myPlayerName = nameInput;

    let rId = document.getElementById("sgs-room-id").value.trim();
    if (!rId) {
        rId = Math.floor(Math.random() * 900000 + 100000).toString();
        document.getElementById("sgs-room-id").value = rId;
    }
    currentRoomId = rId;

    connectToSgsRoom();
});

// Leave room handler
leaveBtn.addEventListener("click", () => {
    if (sgsSocket) {
        sgsSocket.close();
    }
    resetToLobby();
});

function resetToLobby() {
    lobbyEl.style.display = "flex";
    waitingEl.style.display = "none";
    boardEl.style.display = "none";
    roomBadge.textContent = "房间号: 未加入";
    leaveBtn.style.display = "none";
    gameState = null;
    selectedCardId = null;
    selectedTargetName = null;
    activeConversion = null;
}

function connectToSgsRoom() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${proto}//${host}/ws/sanguosha/${currentRoomId}/${myPlayerName}`;

    sgsSocket = new WebSocket(url);

    sgsSocket.onopen = () => {
        roomBadge.textContent = `房间号: ${currentRoomId}`;
        leaveBtn.style.display = "block";
    };

    sgsSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "state_update") {
            updateSgsBoard(data);
        }
    };

    sgsSocket.onclose = (event) => {
        console.log("WebSocket closed", event);
        if (event.reason) {
            alert("断开连接: " + event.reason);
        }
        resetToLobby();
    };

    sgsSocket.onerror = (err) => {
        console.error("WebSocket error", err);
    };
}

// Host starts game
document.getElementById("sgs-start-game-btn").addEventListener("click", () => {
    if (sgsSocket && sgsSocket.readyState === WebSocket.OPEN) {
        sgsSocket.send(JSON.stringify({ action: "start_game" }));
    }
});

function updateSgsBoard(data) {
    gameState = data;
    const players = data.players;
    const me = players.find(p => p.name === myPlayerName);

    if (!data.is_started) {
        // Show Waiting Room
        lobbyEl.style.display = "none";
        waitingEl.style.display = "flex";
        boardEl.style.display = "none";

        document.getElementById("waiting-room-number").textContent = data.room_id;
        const listEl = document.getElementById("waiting-players-list");
        listEl.innerHTML = "";

        players.forEach(p => {
            const row = document.createElement("div");
            row.style.padding = "8px 12px";
            row.style.background = "rgba(255,255,255,0.03)";
            row.style.border = "1px solid rgba(255,255,255,0.05)";
            row.style.borderRadius = "4px";
            row.style.display = "flex";
            row.style.justifyContent = "space-between";
            row.style.fontSize = "13px";

            row.innerHTML = `<span>⚔️ ${p.name} ${p.is_host ? '<span style="color: var(--primary-light); font-size: 11px;">[房主]</span>' : ''}</span>
                             <span style="color: var(--text-muted);">准备就绪</span>`;
            listEl.appendChild(row);
        });

        // Toggle start game button visibility for host
        const startBtn = document.getElementById("sgs-start-game-btn");
        const hostTip = document.getElementById("sgs-host-tip");
        if (me && me.is_host) {
            startBtn.style.display = "block";
            startBtn.disabled = players.length < 4;
            hostTip.textContent = players.length < 4 ? "至少需要 4 位玩家才能开启杀局" : "兵马齐备，可以开启杀局！";
        } else {
            startBtn.style.display = "none";
            hostTip.textContent = "等待房主开启战局...";
        }
    } else {
        // Show Active Game Board
        lobbyEl.style.display = "none";
        waitingEl.style.display = "none";
        boardEl.style.display = "flex";

        renderPlayersCircle(data);
        renderMyPanel(me, data);
        renderLogs(data.logs);
        updateActionConsole(me, data);
    }
}

// Render circular arrangement of players
function renderPlayersCircle(data) {
    const container = document.getElementById("sgs-players-container");
    container.innerHTML = "";

    const players = data.players;
    const meIndex = players.findIndex(p => p.name === myPlayerName);
    const n = players.length;

    for (let i = 0; i < n; i++) {
        const relativeIndex = (i - meIndex + n) % n;
        const pl = players[i];

        // Use percentage-based positioning relative to container center
        const angle = Math.PI / 2 + (relativeIndex * (2 * Math.PI / n));
        const pctX = 50 + 38 * Math.cos(angle);
        const pctY = 50 + 33 * Math.sin(angle);

        const node = document.createElement("div");
        node.className = "sgs-player-node";
        if (pl.name === data.current_player) {
            node.classList.add("active-turn");
        }
        if (!pl.alive) {
            node.classList.add("dead");
        }

        const oldHp = node.getAttribute("data-hp");
        if (oldHp && parseInt(oldHp) > pl.hp) {
            node.classList.add("shake", "damaged-flash");
            setTimeout(() => {
                node.classList.remove("shake", "damaged-flash");
            }, 500);
        }
        node.setAttribute("data-hp", pl.hp);

        // Position using percentage offsets
        node.style.left = `${pctX}%`;
        node.style.top = `${pctY}%`;

        // Highlight if this player is selectable as a target for target-selected card
        const isTargetable = checkIfTargetable(pl);
        if (isTargetable) {
            node.classList.add("target-select");
            node.addEventListener("click", () => {
                selectedTargetName = pl.name;
                renderPlayersCircle(data);
                updateActionConsole(players.find(p => p.name === myPlayerName), data);
            });
        }

        if (selectedTargetName === pl.name) {
            node.style.borderColor = "var(--primary-light)";
            node.style.boxShadow = "0 0 15px var(--primary-light)";
        }

        // Setup character translation
        const charName = pl.character ? (CHARACTERS[pl.character]?.name || pl.character) : "选择中";
        const charSkill = pl.character ? (CHARACTERS[pl.character]?.skill || "") : "";
        const role = getIdentityChinese(pl.identity);

        // Build HP Goutou icons
        let hpIcons = "";
        for (let h = 0; h < pl.max_hp; h++) {
            hpIcons += h < pl.hp ? '<span class="sgs-hook-hp">💚</span>' : '<span class="sgs-hook-hp lost">🖤</span>';
        }

        // Equipment items display
        const eqWeapon = pl.weapon ? pl.weapon.name : "空武器栏";
        const eqArmor = pl.armor ? pl.armor.name : "空防具栏";
        const eqDefHorse = pl.def_horse ? pl.def_horse.name : "空防御马";
        const eqOffHorse = pl.off_horse ? pl.off_horse.name : "空进攻马";

        node.innerHTML = `
            <div class="sgs-player-header">
                <span>${pl.name}</span>
                <span style="font-size:9.5px; color: var(--text-muted);">${pl.hand_count} 张牌</span>
            </div>
            <div class="sgs-player-avatar" style="background: rgba(25,20,15,0.85);">
                ${charName}
                ${pl.identity !== "???" ? `<span class="sgs-player-identity-badge ${pl.identity.toLowerCase()}">${role}</span>` : ""}
                ${charSkill ? `<span class="sgs-player-avatar-skill">${charSkill}</span>` : ""}
            </div>
            <div class="sgs-player-hp-bar">
                ${hpIcons}
            </div>
            <div class="sgs-player-equipments">
                <div class="sgs-player-eq-item ${pl.weapon ? 'equipped' : ''}">${eqWeapon}</div>
                <div class="sgs-player-eq-item ${pl.armor ? 'equipped' : ''}">${eqArmor}</div>
                <div class="sgs-player-eq-item ${pl.def_horse ? 'equipped' : ''}">${eqDefHorse}</div>
                <div class="sgs-player-eq-item ${pl.off_horse ? 'equipped' : ''}">${eqOffHorse}</div>
            </div>
        `;
        container.appendChild(node);
    }
}

// Render self hand cards & profile
function renderMyPanel(me, data) {
    const profileEl = document.getElementById("sgs-my-profile");
    profileEl.innerHTML = "";

    const handEl = document.getElementById("sgs-my-hand");
    handEl.innerHTML = "";

    if (!me) return;

    // Self profile details
    const charName = me.character ? (CHARACTERS[me.character]?.name || me.character) : "选择中";
    const role = getIdentityChinese(me.identity);
    const skillDesc = me.character ? CHARACTERS[me.character]?.desc : "";

    profileEl.innerHTML = `
        <div style="flex:1; display:flex; flex-direction:column; justify-content:center; text-align:center;">
            <div style="font-size: 16px; font-weight:700; color:var(--primary-light);">${charName}</div>
            <div style="font-size: 11px; margin-top: 4px; padding: 2px 6px; background: rgba(255,255,255,0.05); border-radius: 4px;">我的身份: <strong>${role}</strong></div>
            <div style="font-size: 10px; color:var(--text-muted); margin-top:6px; line-height:1.3; overflow:hidden;" title="${skillDesc}">${skillDesc}</div>
        </div>
    `;

    // Self hand cards
    me.hand_cards.forEach(card => {
        const cardEl = document.createElement("div");
        cardEl.className = "sgs-card";
        if (selectedCardId === card.id) {
            cardEl.classList.add("selected");
        }

        const isRed = card.color === "red";
        cardEl.innerHTML = `
            <div class="sgs-card-suit-val ${isRed ? 'red' : 'black'}">
                <span>${card.suit}</span>
                <span>${getCardValueStr(card.value)}</span>
            </div>
            <div class="sgs-card-name">${card.name}</div>
            <span class="sgs-card-type-badge">${getCardTypeStr(card.type)}</span>
        `;

        cardEl.addEventListener("click", () => {
            if (selectedCardId === card.id) {
                selectedCardId = null; // Unselect
                selectedTargetName = null;
                activeConversion = null;
            } else {
                selectedCardId = card.id;
                selectedTargetName = null;
                activeConversion = null;
            }
            renderMyPanel(me, data);
            renderPlayersCircle(data);
            updateActionConsole(me, data);
        });

        // Zhao Yun / Guan Yu skill conversions display if selected
        if (selectedCardId === card.id) {
            // Zhao Yun "Longdan" option
            if (me.character === "zhaoyun") {
                if (card.key === "SHA") {
                    addConversionOption(cardEl, "SHAN", "当【闪】出");
                } else if (card.key === "SHAN") {
                    addConversionOption(cardEl, "SHA", "当【杀】出");
                }
            }
            // Guan Yu "Wusheng" option
            if (me.character === "guanyu" && card.color === "red" && card.key !== "SHA") {
                addConversionOption(cardEl, "SHA", "当【杀】出");
            }
        }

        handEl.appendChild(cardEl);
    });
}

function addConversionOption(cardEl, targetKey, label) {
    const btn = document.createElement("button");
    btn.textContent = label;
    btn.style.cssText = "position:absolute; bottom:25px; left:50%; transform:translateX(-50%); font-size:10px; padding:2px 6px; z-index:15; background:var(--primary); border:none; color:#fff; border-radius:3px; cursor:pointer;";
    btn.addEventListener("click", (e) => {
        e.stopPropagation();
        activeConversion = targetKey;
        btn.style.background = "#10b981";
    });
    cardEl.appendChild(btn);
}

// Render system logs
function renderLogs(logs) {
    const panel = document.getElementById("sgs-log-panel");
    panel.innerHTML = "";
    logs.forEach(log => {
        const item = document.createElement("div");
        item.style.padding = "2px 0";
        item.textContent = log;
        panel.appendChild(item);
    });
    // Auto-scroll to bottom
    panel.scrollTop = panel.scrollHeight;
}

// Update play buttons, prompt logs based on turn
function updateActionConsole(me, data) {
    const confirmBtn = document.getElementById("sgs-action-confirm");
    const passBtn = document.getElementById("sgs-action-pass");
    const indicator = document.getElementById("sgs-turn-indicator");
    const promptBox = document.getElementById("sgs-prompt-box");

    confirmBtn.disabled = true;
    passBtn.disabled = true;
    promptBox.style.display = "none";

    if (!me || !me.alive) {
        indicator.textContent = "你在战场中作壁上观（已阵亡）";
        return;
    }

    const isMyTurn = data.current_player === myPlayerName;

    if (data.phase === "response_waiting") {
        indicator.textContent = `进行中：等待应对`;
        if (data.response_target === myPlayerName) {
            promptBox.style.display = "block";
            passBtn.disabled = false;
            
            if (data.response_type === "shan") {
                promptBox.textContent = `💥 警告！请打出一张【闪】响应，否则承受 1 点伤害！`;
                if (selectedCardId) {
                    const card = me.hand_cards.find(c => c.id === selectedCardId);
                    if (card && (card.key === "SHAN" || (me.character === "zhaoyun" && card.key === "SHA" && activeConversion === "SHAN"))) {
                        confirmBtn.disabled = false;
                    }
                }
            } else if (data.response_type === "sha") {
                promptBox.textContent = `⚔️ 决斗/南蛮！请打出一张【杀】响应，否则扣血！`;
                if (selectedCardId) {
                    const card = me.hand_cards.find(c => c.id === selectedCardId);
                    if (card && (card.key === "SHA" || (me.character === "zhaoyun" && card.key === "SHAN" && activeConversion === "SHA") || (me.character === "guanyu" && card.color === "red" && activeConversion === "SHA"))) {
                        confirmBtn.disabled = false;
                    }
                }
            } else if (data.response_type === "bagua_judge") {
                promptBox.textContent = `🛡️ 八卦阵！是否启动判定？`;
                confirmBtn.disabled = false;
                confirmBtn.textContent = "启动判定";
                // Intercept click to trigger bagua_judge
                confirmBtn.onclick = () => {
                    sgsSocket.send(JSON.stringify({ action: "bagua_judge" }));
                    confirmBtn.onclick = handleConfirmClick; // Restore
                };
            }
        }
    } else if (isMyTurn && data.phase === "normal_turn") {
        indicator.textContent = `你的回合（出牌阶段）`;
        passBtn.disabled = false;
        passBtn.textContent = "结束回合";

        // Enable confirm if valid card and target selected if needed
        if (selectedCardId) {
            const card = me.hand_cards.find(c => c.id === selectedCardId);
            if (card) {
                const needsTarget = ["SHA", "CHAI", "SHUN", "JUEDOU"].includes(card.key);
                if (!needsTarget || selectedTargetName) {
                    confirmBtn.disabled = false;
                }
            }
        }
    } else {
        indicator.textContent = `【${data.current_player}】 正在进行回合...`;
    }
}

// Verify if a player can be targeted by selected card
function checkIfTargetable(pl) {
    if (!gameState || !selectedCardId || !pl.alive) return false;
    const me = gameState.players.find(p => p.name === myPlayerName);
    if (!me) return false;

    const card = me.hand_cards.find(c => c.id === selectedCardId);
    if (!card) return false;

    const isSlash = card.key === "SHA" || (me.character === "zhaoyun" && card.key === "SHAN" && activeConversion === "SHA") || (me.character === "guanyu" && card.color === "red" && activeConversion === "SHA");

    if (isSlash) {
        if (pl.name === myPlayerName) return false;
        // Verify attack distance
        const idx1 = gameState.players.findIndex(p => p.name === myPlayerName);
        const idx2 = gameState.players.findIndex(p => p.name === pl.name);
        const alive = gameState.players.filter(p => p.alive);
        const idx1_a = alive.findIndex(p => p.name === myPlayerName);
        const idx2_a = alive.findIndex(p => p.name === pl.name);
        
        let dist = Math.min(Math.abs(idx1_a - idx2_a), alive.length - Math.abs(idx1_a - idx2_a));
        if (me.off_horse) dist -= 1;
        if (pl.def_horse) dist += 1;
        dist = Math.max(1, dist);

        let range = me.weapon ? (me.weapon.range || 1) : 1;
        return dist <= range;
    }

    if (card.key === "SHUN") {
        if (pl.name === myPlayerName) return false;
        // Verify distance limit 1
        const alive = gameState.players.filter(p => p.alive);
        const idx1_a = alive.findIndex(p => p.name === myPlayerName);
        const idx2_a = alive.findIndex(p => p.name === pl.name);
        let dist = Math.min(Math.abs(idx1_a - idx2_a), alive.length - Math.abs(idx1_a - idx2_a));
        if (me.off_horse) dist -= 1;
        if (pl.def_horse) dist += 1;
        dist = Math.max(1, dist);
        return dist <= 1;
    }

    if (["CHAI", "JUEDOU"].includes(card.key)) {
        return pl.name !== myPlayerName;
    }

    return false;
}

// Button click callbacks
document.getElementById("sgs-action-confirm").addEventListener("click", handleConfirmClick);
document.getElementById("sgs-action-pass").addEventListener("click", handlePassClick);

function handleConfirmClick() {
    if (!sgsSocket || sgsSocket.readyState !== WebSocket.OPEN) return;

    if (gameState.phase === "response_waiting") {
        if (gameState.response_type === "bagua_judge") {
            sgsSocket.send(JSON.stringify({ action: "bagua_judge" }));
        } else {
            sgsSocket.send(JSON.stringify({
                action: "respond_card",
                card_id: selectedCardId,
                conversion: activeConversion
            }));
        }
    } else { // Normal turn card playing
        sgsSocket.send(JSON.stringify({
            action: "play_card",
            card_id: selectedCardId,
            target_name: selectedTargetName,
            conversion: activeConversion
        }));
    }

    selectedCardId = null;
    selectedTargetName = null;
    activeConversion = null;
}

function handlePassClick() {
    if (!sgsSocket || sgsSocket.readyState !== WebSocket.OPEN) return;

    if (gameState.phase === "response_waiting") {
        sgsSocket.send(JSON.stringify({
            action: "respond_card",
            card_id: null // Null card is Pass
        }));
    } else {
        sgsSocket.send(JSON.stringify({ action: "end_turn" }));
    }

    selectedCardId = null;
    selectedTargetName = null;
    activeConversion = null;
}

// Translators and string helpers
function getIdentityChinese(id) {
    const dict = {
        "Lord": "主公",
        "Loyalist": "忠臣",
        "Rebel": "反贼",
        "Defector": "内奸"
    };
    return dict[id] || id;
}

function getCardValueStr(val) {
    if (val === 1) return "A";
    if (val === 11) return "J";
    if (val === 12) return "Q";
    if (val === 13) return "K";
    return val.toString();
}

function getCardTypeStr(t) {
    const dict = {
        "basic": "基本牌",
        "scroll": "锦囊牌",
        "equipment": "装备牌"
    };
    return dict[t] || t;
}

// Skill triggering helpers for Liu Bei (Rende) / Sun Quan (Zhiheng)
// Can be implemented using double-click triggers or separate action bars
const CHARACTERS = {
    "caocao": {"name": "曹操", "skill": "奸雄", "desc": "受到伤害时，可获得造成伤害的牌"},
    "liubei": {"name": "刘备", "skill": "仁德", "desc": "可将手牌交给其他玩家（给满2张回1血）"},
    "sunquan": {"name": "孙权", "skill": "制衡", "desc": "限一次，弃置手牌换取等量新牌"},
    "guanyu": {"name": "关羽", "skill": "武圣", "desc": "任意红色牌可当【杀】使用或打出"},
    "zhangfei": {"name": "张飞", "skill": "咆哮", "desc": "出牌阶段可以使用无限次【杀】"},
    "zhaoyun": {"name": "赵云", "skill": "龙胆", "desc": "【杀】与【闪】可以互换使用或打出"}
};

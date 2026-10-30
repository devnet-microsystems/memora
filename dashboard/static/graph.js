/**
 * Memora Memory Graph — True 3D interactive visualization using 3d-force-graph (Three.js).
 * Populated exclusively with real data from /api/memory backend endpoint.
 */
function initMemoryGraph(containerId, refreshMs = 10000) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let graph = null;
    let showAllNodes = false;

    const showAllCheckbox = document.getElementById("show-all-nodes");
    if (showAllCheckbox) {
        showAllNodes = showAllCheckbox.checked;
        showAllCheckbox.addEventListener("change", (e) => {
            showAllNodes = e.target.checked;
            if (graph) updateGraph();
        });
    }

    // Category colors — high contrast on dark navy background, neon command-center palette
    const GROUP_COLORS = {
        person: "#34D399",      // electric green
        place: "#60A5FA",       /* electric blue */
        med: "#A78BFA",         /* restrained purple */
        habit: "#38BDF8",       /* neon cyan */
        condition: "#FB7185",   /* soft rose */
        preference: "#22D3EE",  /* cyan */
        flag: "#FBBF24",        /* amber */
        alert: "#EF4444",       /* red */
        pending: "#94A3B8",     /* slate grey */
        caa_button: "#60A5FA",  /* electric blue */
        unknown: "#94A3B8"
    };

    // Node radius by category (screen space pixels)
    const GROUP_SIZE = {
        alert: 13,
        condition: 12,
        med: 11,
        person: 11,
        place: 10,
        habit: 10,
        preference: 9,
        caa_button: 9,
        pending: 8,
        flag: 7,
        unknown: 7
    };

    function getColorForGroup(group) {
        return GROUP_COLORS[group] || GROUP_COLORS.unknown;
    }

    function getSizeForGroup(group) {
        return GROUP_SIZE[group] || GROUP_SIZE.unknown;
    }

    function showNodeDetails(node) {
        const groupLabelMap = {
            person: "Persona",
            place: "Luogo",
            med: "Farmaco",
            habit: "Abbitudine",
            condition: "Condizione",
            preference: "Preferenza",
            flag: "Segnale",
            alert: "Allerta",
            pending: "In attesa",
            caa_button: "Comunicazione AAC"
        };
        const groupLabel = groupLabelMap[node.group] || node.group;

        const detail = document.getElementById("graph-node-detail");
        if (detail) {
            detail.innerHTML = `
                <div style="padding: 12px; background: #0a0a14; border: 1px solid #333; border-radius: 8px; color: #fff; font-family: Atkinson Hyperlegible, sans-serif; font-size: 13px; line-height: 1.5; max-width: 300px;">
                    <div style="font-weight: bold; color: #1f5fbf; margin-bottom: 6px; border-bottom: 1px solid #333; padding-bottom: 4px;">🧠 Memoria</div>
                    <div style="margin-bottom: 4px;"><strong>ID:</strong> ${escapeHtml(node.id)}</div>
                    <div style="margin-bottom: 4px;"><strong>Tipo:</strong> ${escapeHtml(groupLabel)}</div>
                    <div style="margin-bottom: 4px;"><strong>Contenuto:</strong> ${escapeHtml(node.name || node.label || node.id)}</div>
                    <div style="margin-top: 8px; font-size: 11px; color: #888;">Fai clic su un altro nodo per cambiare selezione</div>
                </div>
            `;
            detail.style.display = "block";
        }
    }

    function hideNodeDetails() {
        const detail = document.getElementById("graph-node-detail");
        if (detail) detail.style.display = "none";
    }

    function escapeHtml(text) {
        if (!text) return "";
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function addRecenterButton() {
        const existing = container.querySelector(".graph-recenter-btn");
        if (existing) return;

        const btn = document.createElement("button");
        btn.className = "graph-recenter-btn";
        btn.textContent = "🔄 Inquadra grafo";
        btn.style.position = "absolute";
        btn.style.top = "10px";
        btn.style.right = "10px";
        btn.style.zIndex = "100";
        btn.style.padding = "8px 16px";
        btn.style.background = "#1f5fbf";
        btn.style.color = "#fff";
        btn.style.border = "none";
        btn.style.borderRadius = "6px";
        btn.style.cursor = "pointer";
        btn.style.fontFamily = "Atkinson Hyperlegible, sans-serif";
        btn.style.fontSize = "13px";
        btn.style.boxShadow = "0 2px 6px rgba(0,0,0,0.5)";
        btn.onclick = () => {
            if (graph) graph.zoomToFit(500, 10);
        };
        container.style.position = "relative";
        container.appendChild(btn);

        // Add node details panel
        const detail = document.createElement("div");
        detail.id = "graph-node-detail";
        detail.style.position = "absolute";
        detail.style.bottom = "10px";
        detail.style.left = "10px";
        detail.style.zIndex = "100";
        detail.style.display = "none";
        detail.style.maxWidth = "320px";
        container.appendChild(detail);
    }

    async function updateGraph() {
        try {
            const resp = await fetch("/api/memory");
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }
            const graphData = await resp.json();

            // Lazy initialization of 3d-force-graph
            if (!graph) {
                if (typeof ForceGraph3D === "undefined") {
                    throw new Error("3d-force-graph libreria non caricata: verifica il CDN o la connessione di rete");
                }

                // Configurazione grafo 3D — ogni metodo è verificato contro l'API di 3d-force-graph v1.80.1
                // Metodi rimossi (non supportati): linkHoverWidth, linkHoverColor, nodeOpacityHover
                // Fisica configurata tramite d3Force (se disponibile nella versione caricata)
                graph = ForceGraph3D()(container)
                    .backgroundColor("#05050a")
                    .nodeRelSize(6)
                    .nodeAutoColorBy("group")
                    .linkWidth(2)
                    .linkColor(() => "#3a3a4a")
                    .nodeOpacity(1)
                    .onNodeClick((node) => {
                        showNodeDetails(node);
                    })
                    .onNodeHover((node) => {
                        // hover gestito da Three.js orbit controls
                    })
                    .onEngineStop(() => {
                        // fisica stabilizzata — nessuna azione richiesta
                    })
                    .cooldownTicks(200);

                // Fisica 3D tramite d3-force (se disponibile nella versione caricata)
                if (typeof graph.d3Force === "function") {
                    const chargeForce = graph.d3Force("charge");
                    if (chargeForce && typeof chargeForce.strength === "function") {
                        chargeForce.strength(-300);
                    }
                    const linkForce = graph.d3Force("link");
                    if (linkForce && typeof linkForce.distance === "function" && typeof linkForce.strength === "function") {
                        linkForce.distance(100).strength(0.85);
                    }
                }

                // Cooldown per stabilizzare la fisica
                graph.cooldownTicks(200);

                addRecenterButton();
            }

            // Filter nodes: hide caa_button and pending unless showAllNodes
            const filteredNodes = (graphData.nodes || []).filter(n => {
                const isHiddenGroup = (n.group === "caa_button" || n.group === "pending");
                return !isHiddenGroup || showAllNodes;
            });

            // Build set of visible node IDs
            const visibleNodeIds = new Set(filteredNodes.map(n => n.id));

            // Filter edges: only keep edges where both endpoints are visible
            const filteredEdges = (graphData.edges || []).filter(e =>
                visibleNodeIds.has(e.from) && visibleNodeIds.has(e.to)
            );

            // Map to 3d-force-graph data format
            const nodes = filteredNodes.map(n => ({
                id: n.id,
                name: n.label || n.id,
                group: n.group,
                color: getColorForGroup(n.group),
                size: getSizeForGroup(n.group)
            }));

            const links = filteredEdges.map(e => ({
                source: e.from,
                target: e.to,
                label: e.label || "related_to",
                color: "#3a3a4a",
                width: 2
            }));

            graph.graphData({ nodes: nodes, links: links });

            // Center view on new data
            if (nodes.length > 0) {
                graph.zoomToFit(500, 10);
            } else {
                hideNodeDetails();
                container.querySelectorAll(".graph-empty-msg").forEach(el => el.remove());
                const emptyMsg = document.createElement("div");
                emptyMsg.className = "graph-empty-msg";
                emptyMsg.style.position = "absolute";
                emptyMsg.style.top = "50%";
                emptyMsg.style.left = "50%";
                emptyMsg.style.transform = "translate(-50%, -50%)";
                emptyMsg.style.color = "#666";
                emptyMsg.style.fontFamily = "Atkinson Hyperlegible, sans-serif";
                emptyMsg.style.fontSize = "16px";
                emptyMsg.textContent = "Nessun nodo nel grafo";
                container.appendChild(emptyMsg);
            }

        } catch (e) {
            const msg = String(e.message || e);
            console.error("Failed to fetch memory graph:", e);
            container.querySelectorAll(".graph-empty-msg, .graph-error-msg").forEach(el => el.remove());
            const errMsg = document.createElement("div");
            errMsg.className = "graph-error-msg";
            errMsg.style.position = "absolute";
            errMsg.style.top = "50%";
            errMsg.style.left = "50%";
            errMsg.style.transform = "translate(-50%, -50%)";
            errMsg.style.color = "#ff6666";
            errMsg.style.fontFamily = "Atkinson Hyperlegible, sans-serif";
            errMsg.style.fontSize = "16px";
            errMsg.style.textAlign = "center";
            errMsg.style.maxWidth = "400px";
            errMsg.style.padding = "16px";
            errMsg.style.background = "#1a0a0a";
            errMsg.style.border = "1px solid #ff6666";
            errMsg.style.borderRadius = "8px";
            if (msg.includes("3d-force-graph libreria non caricata")) {
                errMsg.appendChild(Object.assign(document.createElement("strong"), {textContent: "Errore libreria 3D:"}));
                errMsg.appendChild(document.createElement("br"));
                errMsg.appendChild(document.createTextNode(msg));
                errMsg.appendChild(document.createElement("br"));
                errMsg.appendChild(document.createTextNode("Ricarica la pagina per riprovare."));
            } else if (msg.includes("Errore configurazione 3d-force-graph")) {
                errMsg.appendChild(Object.assign(document.createElement("strong"), {textContent: "Errore configurazione 3D:"}));
                errMsg.appendChild(document.createElement("br"));
                errMsg.appendChild(document.createTextNode(msg));
            } else if (msg.includes("HTTP")) {
                errMsg.appendChild(Object.assign(document.createElement("strong"), {textContent: "Errore API:"}));
                errMsg.appendChild(document.createElement("br"));
                errMsg.appendChild(document.createTextNode(msg));
                errMsg.appendChild(document.createElement("br"));
                errMsg.appendChild(document.createTextNode("Il backend potrebbe non essere raggiungibile."));
            } else {
                errMsg.textContent = msg;
            }
            container.appendChild(errMsg);
        }
    }

    // Initial fetch
    updateGraph();

    // Auto refresh
    if (refreshMs > 0) {
        setInterval(updateGraph, refreshMs);
    }

    // Handle window resize — wake up physics to re-layout
    window.addEventListener("resize", () => {
        if (graph) {
            if (typeof graph.warmupTicks === "function") {
                graph.warmupTicks();
                graph.cooldownTicks(50);
            }
        }
    });
}

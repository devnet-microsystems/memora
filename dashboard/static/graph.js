function initMemoryGraph(containerId, refreshMs = 10000) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // We will store the current state here to only apply diffs
    const nodes = new vis.DataSet();
    const edges = new vis.DataSet();
    let network = null;

    const data = {
        nodes: nodes,
        edges: edges
    };

    const options = {
        nodes: {
            shape: "dot",
            size: 20,
            font: { size: 14, color: "#fff" },
            borderWidth: 2
        },
        edges: {
            width: 2,
            font: { size: 12, align: "middle", color: "#ccc" },
            arrows: { to: { enabled: true, scaleFactor: 0.5 } }
        },
        physics: {
            forceAtlas2Based: {
                gravitationalConstant: -26,
                centralGravity: 0.005,
                springLength: 230,
                springConstant: 0.18
            },
            maxVelocity: 146,
            solver: "forceAtlas2Based",
            timestep: 0.35,
            stabilization: { iterations: 150 }
        }
    };

    network = new vis.Network(container, data, options);

    // Provide a way to filter nodes
    let showAllNodes = false;
    const showAllCheckbox = document.getElementById("show-all-nodes");
    if (showAllCheckbox) {
        showAllNodes = showAllCheckbox.checked;
        showAllCheckbox.addEventListener("change", (e) => {
            showAllNodes = e.target.checked;
            updateGraph(); // Re-fetch or re-apply filters immediately
        });
    }

    function getColorForGroup(group) {
        const colors = {
            person: { background: "#4CAF50", border: "#388E3C" }, // green
            place: { background: "#2196F3", border: "#1976D2" }, // blue
            med: { background: "#9C27B0", border: "#7B1FA2" }, // purple
            habit: { background: "#FF9800", border: "#F57C00" }, // orange
            condition: { background: "#F44336", border: "#D32F2F" }, // red
            preference: { background: "#00BCD4", border: "#0097A7" }, // cyan
            flag: { background: "#FFEB3B", border: "#FBC02D" }, // yellow
            alert: { background: "#E91E63", border: "#C2185B" }, // pink
            pending: { background: "#9E9E9E", border: "#757575" }, // grey
            caa_button: { background: "#607D8B", border: "#455A64" }, // blue grey
            unknown: { background: "#FFFFFF", border: "#BDBDBD" }
        };
        return colors[group] || colors.unknown;
    }

    async function updateGraph() {
        try {
            const resp = await fetch("/api/memory");
            const graphData = await resp.json();

            if (graphData && graphData.nodes && graphData.edges) {
                // Prepare new nodes and edges
                const newNodesMap = new Map();
                const newEdgesMap = new Map();

                graphData.nodes.forEach(n => {
                    // Filter logic
                    const isHiddenGroup = (n.group === "caa_button" || n.group === "pending");
                    if (isHiddenGroup && !showAllNodes) return; // skip

                    newNodesMap.set(n.id, {
                        id: n.id,
                        label: n.label,
                        group: n.group,
                        title: n.title,
                        color: getColorForGroup(n.group)
                    });
                });

                graphData.edges.forEach(e => {
                    const edgeId = `${e.from}-${e.to}-${e.label}`;
                    
                    // Only add edge if both nodes exist in newNodesMap (due to filtering)
                    if (newNodesMap.has(e.from) && newNodesMap.has(e.to)) {
                        newEdgesMap.set(edgeId, {
                            id: edgeId,
                            from: e.from,
                            to: e.to,
                            label: e.label
                        });
                    }
                });

                // Diffing Nodes
                const currentNodes = nodes.get();
                const nodesToAdd = [];
                const nodesToUpdate = [];
                const nodesToRemove = [];

                currentNodes.forEach(cn => {
                    if (!newNodesMap.has(cn.id)) {
                        nodesToRemove.push(cn.id);
                    } else {
                        // Check if needs update (simplified, we just update all existing for now)
                        nodesToUpdate.push(newNodesMap.get(cn.id));
                        newNodesMap.delete(cn.id); // mark as processed
                    }
                });
                newNodesMap.forEach(n => nodesToAdd.push(n));

                nodes.remove(nodesToRemove);
                nodes.update(nodesToUpdate);
                nodes.add(nodesToAdd);

                // Diffing Edges
                const currentEdges = edges.get();
                const edgesToAdd = [];
                const edgesToUpdate = [];
                const edgesToRemove = [];

                currentEdges.forEach(ce => {
                    if (!newEdgesMap.has(ce.id)) {
                        edgesToRemove.push(ce.id);
                    } else {
                        edgesToUpdate.push(newEdgesMap.get(ce.id));
                        newEdgesMap.delete(ce.id);
                    }
                });
                newEdgesMap.forEach(e => edgesToAdd.push(e));

                edges.remove(edgesToRemove);
                edges.update(edgesToUpdate);
                edges.add(edgesToAdd);
            }
        } catch (e) {
            console.error("Failed to fetch memory graph:", e);
        }
    }

    // Initial fetch
    updateGraph();
    
    // Auto refresh
    if (refreshMs > 0) {
        setInterval(updateGraph, refreshMs);
    }
}

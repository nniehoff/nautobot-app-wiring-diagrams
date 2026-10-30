// Square-line wiring diagrams: ELK lays out the graph that render.to_layout() describes, then each cable is drawn
// as horizontal and vertical runs, hopping over every vertical run it crosses.
//
// The SVG mirrors Graphviz's output closely enough for wiring-diagram.js (pan, zoom, hover tracing) to drive it:
// g.edge#wd-e<n> with the hover classes, g.node#wd-<node>-node, and a_wd-<node>[-<port>] groups around cells.
(function (root) {
    "use strict";

    const FONT = "Helvetica, Arial, sans-serif";
    const FONT_SIZE = 10;
    const SUBTITLE_SIZE = 9;
    const ROW = 20;
    const HEADER = 22;
    const HEADER_WITH_SUBTITLE = 32;
    const PAD = 8;
    const MARGIN = 16;
    const TITLE = 28;
    const JUMP = 4;
    const IN_SCOPE_HEADER = "#cfe2ff";
    const OUT_OF_SCOPE_HEADER = "#e9ecef";
    const DASHES = {dashed: "6,4", dotted: "2,3"};

    let context = null;

    function textWidth(text, size, bold) {
        if (context === null && typeof document !== "undefined") {
            context = document.createElement("canvas").getContext("2d");
        }
        if (!context) {
            return text.length * size * 0.6;
        }
        context.font = `${bold ? "bold " : ""}${size}px ${FONT}`;
        return context.measureText(text).width;
    }

    function escapeXml(value) {
        return String(value).replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"})[c]);
    }

    function headerHeight(node) {
        return node.subtitle ? HEADER_WITH_SUBTITLE : HEADER;
    }

    // ELK input: fixed-size boxes with each port pinned to its row on the east or west edge, columns kept as
    // partitions, and the server's top-to-bottom order kept as model order.
    function buildElkGraph(data) {
        const children = data.nodes.map((node) => {
            const width = Math.ceil(Math.max(
                textWidth(node.label, FONT_SIZE, true),
                textWidth(node.subtitle || "", SUBTITLE_SIZE, false),
                ...node.ports.map((port) => textWidth(port.name, FONT_SIZE, false)),
            )) + 2 * PAD;
            const top = headerHeight(node);
            return {
                id: node.id,
                width: width,
                height: top + node.ports.length * ROW,
                layoutOptions: {
                    "elk.portConstraints": "FIXED_POS",
                    "elk.partitioning.partition": String(node.partition),
                },
                ports: node.ports.map((port, index) => ({
                    id: `${node.id}:${port.id}`,
                    x: port.side === "WEST" ? 0 : width,
                    y: top + index * ROW + ROW / 2,
                    width: 0,
                    height: 0,
                    layoutOptions: {"elk.port.side": port.side},
                })),
            };
        });
        return {
            id: "root",
            layoutOptions: {
                "elk.algorithm": "layered",
                "elk.direction": "RIGHT",
                "elk.edgeRouting": "ORTHOGONAL",
                "elk.partitioning.activate": "true",
                "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
                "elk.layered.crossingMinimization.forceNodeModelOrder": "true",
                // Shortest total cable length; the default left busy switches pinned to the top.
                "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
                "elk.spacing.nodeNode": "24",
                "elk.spacing.edgeEdge": "8",
                "elk.spacing.edgeNode": "12",
                "elk.layered.spacing.nodeNodeBetweenLayers": "48",
                "elk.layered.spacing.edgeEdgeBetweenLayers": "8",
                "elk.layered.spacing.edgeNodeBetweenLayers": "16",
            },
            children: children,
            edges: data.edges.map((edge) => ({
                id: edge.id,
                sources: [edge.source.join(":")],
                targets: [edge.target.join(":")],
            })),
        };
    }

    // Each laid-out edge as a list of points, start to end.
    function edgePoints(laidOut) {
        const points = {};
        (laidOut.edges || []).forEach((edge) => {
            const list = [];
            (edge.sections || []).forEach((section) => {
                list.push(section.startPoint, ...(section.bendPoints || []), section.endPoint);
            });
            points[edge.id] = list;
        });
        return points;
    }

    // SVG path data for a run of points, with a semicircular hop wherever a horizontal run crosses another
    // cable's vertical run. Crossings too close to a bend are left flat.
    function jumpPath(points, verticals, ownId) {
        let d = `M${points[0].x},${points[0].y}`;
        for (let i = 1; i < points.length; i++) {
            const from = points[i - 1];
            const to = points[i];
            if (Math.abs(from.y - to.y) < 0.5 && Math.abs(from.x - to.x) > 2 * JUMP) {
                const dir = Math.sign(to.x - from.x);
                const low = Math.min(from.x, to.x) + JUMP;
                const high = Math.max(from.x, to.x) - JUMP;
                const crossings = verticals
                    .filter((v) => v.id !== ownId && v.x > low && v.x < high && from.y > v.y1 + 0.5 && from.y < v.y2 - 0.5)
                    .map((v) => v.x)
                    .sort((a, b) => (a - b) * dir);
                let last = from.x - dir * JUMP;
                crossings.forEach((x) => {
                    if ((x - last) * dir < 2 * JUMP) {
                        return; // Overlaps the previous hop.
                    }
                    // Sweep flag: hop over the top whichever way the run goes.
                    d += `L${x - dir * JUMP},${from.y}A${JUMP},${JUMP} 0 0 ${dir > 0 ? 1 : 0} ${x + dir * JUMP},${from.y}`;
                    last = x;
                });
            }
            d += `L${to.x},${to.y}`;
        }
        return d;
    }

    function verticalRuns(points) {
        const runs = [];
        Object.entries(points).forEach(([id, list]) => {
            for (let i = 1; i < list.length; i++) {
                if (Math.abs(list[i - 1].x - list[i].x) < 0.5 && Math.abs(list[i - 1].y - list[i].y) > 0.5) {
                    runs.push({
                        id: id,
                        x: list[i].x,
                        y1: Math.min(list[i - 1].y, list[i].y),
                        y2: Math.max(list[i - 1].y, list[i].y),
                    });
                }
            }
        });
        return runs;
    }

    function link(id, url, title, inner) {
        return `<g id="a_${id}"><a href="${escapeXml(url)}"><title>${escapeXml(title)}</title>${inner}</a></g>`;
    }

    function nodeSvg(node, box) {
        const top = headerHeight(node);
        const x = box.x;
        const y = box.y;
        const fill = node.inScope ? IN_SCOPE_HEADER : OUT_OF_SCOPE_HEADER;
        const cx = x + box.width / 2;
        let header = `<rect x="${x}" y="${y}" width="${box.width}" height="${top}" fill="${fill}" stroke="#212529"/>`;
        if (node.subtitle) {
            header += `<text x="${cx}" y="${y + 14}" text-anchor="middle" font-family="${FONT}" font-size="${FONT_SIZE}" font-weight="bold">${escapeXml(node.label)}</text>`;
            header += `<text x="${cx}" y="${y + 26}" text-anchor="middle" font-family="${FONT}" font-size="${SUBTITLE_SIZE}">${escapeXml(node.subtitle)}</text>`;
        } else {
            header += `<text x="${cx}" y="${y + 15}" text-anchor="middle" font-family="${FONT}" font-size="${FONT_SIZE}" font-weight="bold">${escapeXml(node.label)}</text>`;
        }
        let cells = link(`wd-${node.id}`, node.url, node.label, header);
        node.ports.forEach((port, index) => {
            const rowY = y + top + index * ROW;
            cells += link(
                `wd-${node.id}-${port.id}`,
                port.url,
                port.name,
                `<rect x="${x}" y="${rowY}" width="${box.width}" height="${ROW}" fill="#ffffff" stroke="#212529"/>` +
                `<text x="${x + PAD}" y="${rowY + 14}" font-family="${FONT}" font-size="${FONT_SIZE}">${escapeXml(port.name)}</text>`,
            );
        });
        return `<g id="wd-${node.id}-node" class="node">${cells}</g>`;
    }

    function edgeSvg(edge, d) {
        const dash = DASHES[edge.dash] ? ` stroke-dasharray="${DASHES[edge.dash]}"` : "";
        const path = `<path d="${d}" fill="none" stroke="${escapeXml(edge.color)}" stroke-width="${edge.width}"${dash}/>`;
        return `<g id="${edge.id}" class="edge ${escapeXml(edge.classes)}">` +
            `<a href="${escapeXml(edge.url)}"><title>${escapeXml(edge.tooltip)}</title>${path}</a></g>`;
    }

    // The finished SVG document as a string. `laidOut` is ELK's result for buildElkGraph(data).
    function renderSvg(data, laidOut) {
        const boxes = {};
        (laidOut.children || []).forEach((child) => {
            boxes[child.id] = child;
        });
        const points = edgePoints(laidOut);
        const verticals = verticalRuns(points);
        const width = Math.ceil(laidOut.width) + 2 * MARGIN;
        const height = Math.ceil(laidOut.height) + 2 * MARGIN + (data.title ? TITLE : 0);
        const offsetY = MARGIN + (data.title ? TITLE : 0);
        const parts = [
            `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${width}pt" height="${height}pt" viewBox="0 0 ${width} ${height}">`,
            `<rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"/>`,
        ];
        if (data.title) {
            parts.push(`<text x="${width / 2}" y="${MARGIN + 12}" text-anchor="middle" font-family="${FONT}" font-size="14">${escapeXml(data.title)}</text>`);
        }
        parts.push(`<g transform="translate(${MARGIN},${offsetY})">`);
        data.nodes.forEach((node) => parts.push(nodeSvg(node, boxes[node.id])));
        data.edges.forEach((edge) => {
            const list = points[edge.id];
            if (list && list.length > 1) {
                parts.push(edgeSvg(edge, jumpPath(list, verticals, edge.id)));
            }
        });
        parts.push("</g></svg>");
        return parts.join("");
    }

    function layout(data, Elk) {
        return new Elk().layout(buildElkGraph(data)).then((laidOut) => renderSvg(data, laidOut));
    }

    function download(blob, filename) {
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
    }

    function loadScript(url) {
        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = url;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`Could not load ${url}`));
            document.head.appendChild(script);
        });
    }

    function svgSize(svgText) {
        const match = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(svgText);
        return [Number(match[1]), Number(match[2])];
    }

    function exportPng(svgText, filename) {
        const [width, height] = svgSize(svgText);
        const url = URL.createObjectURL(new Blob([svgText], {type: "image/svg+xml"}));
        const image = new Image();
        image.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = width * 2;
            canvas.height = height * 2;
            const context2d = canvas.getContext("2d");
            context2d.scale(2, 2);
            context2d.drawImage(image, 0, 0, width, height);
            URL.revokeObjectURL(url);
            canvas.toBlob((blob) => download(blob, filename), "image/png");
        };
        image.src = url;
    }

    // jsPDF and svg2pdf.js load on the first PDF export; most views never need them.
    async function exportPdf(svgText, filename, scripts) {
        if (!root.jspdf) {
            await loadScript(scripts.jspdf);
        }
        if (!root.jspdf.jsPDF.API.svg) {
            await loadScript(scripts.svg2pdf);
        }
        const [width, height] = svgSize(svgText);
        const holder = document.createElement("div");
        holder.style.cssText = "position:absolute;left:-100000px;top:0";
        holder.appendChild(document.importNode(new DOMParser().parseFromString(svgText, "image/svg+xml").documentElement, true));
        document.body.appendChild(holder);
        try {
            const pdf = new root.jspdf.jsPDF({
                orientation: width > height ? "landscape" : "portrait",
                unit: "pt",
                format: [width, height],
            });
            await pdf.svg(holder.firstChild, {x: 0, y: 0, width: width, height: height});
            pdf.save(filename);
        } finally {
            holder.remove();
        }
    }

    // Browser: lay out each square diagram on the page, hand it to wiring-diagram.js, and wire up its exports.
    function start() {
        document.querySelectorAll("[data-wd-square]").forEach((container) => {
            const wrapper = container.closest("[data-wd-diagram]");
            const data = JSON.parse(document.getElementById(container.dataset.wdSquare).textContent);
            layout(data, root.ELK).then((svgText) => {
                const svg = new DOMParser().parseFromString(svgText, "image/svg+xml").documentElement;
                container.replaceChildren(document.importNode(svg, true));
                root.NautobotWiringDiagram.setup(wrapper);
                const name = wrapper.dataset.wdFilename || "wiring";
                const scripts = {jspdf: container.dataset.wdJspdf, svg2pdf: container.dataset.wdSvg2pdf};
                wrapper.querySelectorAll("[data-wd-export]").forEach((button) => {
                    button.disabled = false;
                    button.addEventListener("click", () => {
                        const format = button.dataset.wdExport;
                        if (format === "svg") {
                            download(new Blob([svgText], {type: "image/svg+xml"}), `${name}.svg`);
                        } else if (format === "png") {
                            exportPng(svgText, `${name}.png`);
                        } else {
                            button.disabled = true;
                            exportPdf(svgText, `${name}.pdf`, scripts)
                                .catch((error) => alert(`The PDF could not be made: ${error.message}`))
                                .finally(() => {
                                    button.disabled = false;
                                });
                        }
                    });
                });
            }).catch((error) => {
                container.textContent = `The diagram could not be laid out: ${error}`;
            });
        });
    }

    const api = {buildElkGraph, jumpPath, renderSvg, layout};
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    } else {
        root.NautobotWiringSquare = api;
        start();
    }
})(typeof globalThis !== "undefined" ? globalThis : this);

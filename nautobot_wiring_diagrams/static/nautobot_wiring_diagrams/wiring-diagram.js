// Pan, zoom, and hover tracing for wiring diagrams rendered by Graphviz.
//
// render.py gives every cable (g.edge) the classes wd-<node> and wd-<node>-<port> for both of its ends, every
// node the id wd-<node>-node, and every header and port cell an ID that Graphviz writes as a_wd-<node>[-<port>].
(function () {
    "use strict";

    const MIN_SCALE = 0.05;
    const MAX_SCALE = 4;
    const ZOOM_STEP = 1.25;
    const DRAG_THRESHOLD = 4;
    const LABEL_SIZE = 10;

    // The PDF page and scale for a `width` x `height` diagram, or null for one page the diagram's size. A copy of
    // render.pick_page: the first page it fits at full size, else the last scaled down, turned to match.
    function pickPage(width, height, page) {
        let picked = null;
        for (const size of (page && page.sizes) || []) {
            const [short, long] = [Math.min(size.width, size.height), Math.max(size.width, size.height)];
            const [pageWidth, pageHeight] = width > height ? [long, short] : [short, long];
            const scale = Math.min(
                1,
                (pageWidth - 2 * page.margin) / Math.max(width, 1),
                (pageHeight - 2 * page.margin) / Math.max(height, 1),
            );
            picked = {name: size.name, width: pageWidth, height: pageHeight, scale: scale};
            if (scale === 1) {
                break;
            }
        }
        return picked;
    }

    // The page options render.page_data() wrote for this diagram.
    function pageData(wrapper) {
        const script = document.getElementById(wrapper.dataset.wdPage || "");
        return script ? JSON.parse(script.textContent) : null;
    }

    function inches(points) {
        return (points / 72).toFixed(1).replace(/\.0$/, "");
    }

    // Say what page the PDF lands on, and warn when its labels would print too small to read.
    function showPage(wrapper, width, height) {
        const note = wrapper.querySelector("[data-wd-page-note]");
        const page = pageData(wrapper);
        if (!note || !page) {
            return;
        }
        const picked = pickPage(width, height, page);
        note.classList.remove("text-secondary", "text-warning");
        if (!picked) {
            note.classList.add("text-secondary");
            note.textContent = `PDF: ${inches(width)} × ${inches(height)} in`;
            return;
        }
        const orientation = picked.width > picked.height ? "landscape" : "portrait";
        const percent = Math.round(picked.scale * 100);
        if (picked.scale < page.warnBelow) {
            note.classList.add("text-warning");
            note.innerHTML = '<span class="mdi mdi-alert" aria-hidden="true"></span> ';
            note.append(`PDF: ${picked.name} ${orientation} at ${percent}%, labels about ${(LABEL_SIZE * picked.scale).toFixed(1)} pt`);
            note.title = "Labels may be hard to read. Choose a larger PDF page size, None, or narrow the diagram.";
        } else {
            note.classList.add("text-secondary");
            note.textContent = `PDF: ${picked.name} ${orientation} at ${percent}%`;
            note.title = "";
        }
    }

    function setup(wrapper) {
        const container = wrapper.querySelector(".nautobot-wiring-diagram");
        const svg = container && container.querySelector("svg");
        if (!svg) {
            return;
        }
        const box = svg.viewBox.baseVal;
        const full = {x: box.x, y: box.y, width: box.width, height: box.height};
        let view = {...full};
        svg.removeAttribute("width");
        svg.removeAttribute("height");
        svg.setAttribute("preserveAspectRatio", "xMinYMin meet");
        // Graphviz and the square view both draw in points; the curved PDF adds a title, so this is close.
        showPage(wrapper, full.width, full.height);

        function apply() {
            svg.setAttribute("viewBox", `${view.x} ${view.y} ${view.width} ${view.height}`);
        }

        // Show `width` diagram units across the container, keeping its aspect ratio.
        function setWidth(width, anchorX, anchorY) {
            const scale = full.width / width;
            if (scale < MIN_SCALE || scale > MAX_SCALE) {
                return;
            }
            const height = width * container.clientHeight / container.clientWidth;
            view = {
                x: anchorX - (anchorX - view.x) * width / view.width,
                y: anchorY - (anchorY - view.y) * height / view.height,
                width: width,
                height: height,
            };
            apply();
        }

        function fitWidth() {
            const height = full.width * container.clientHeight / container.clientWidth;
            view = {x: full.x, y: full.y, width: full.width, height: height};
            apply();
        }

        function fitAll() {
            const ratio = container.clientHeight / container.clientWidth;
            const width = Math.max(full.width, full.height / ratio);
            view = {x: full.x, y: full.y, width: width, height: width * ratio};
            apply();
        }

        function toDiagram(clientX, clientY) {
            const point = new DOMPoint(clientX, clientY).matrixTransform(svg.getScreenCTM().inverse());
            return [point.x, point.y];
        }

        function zoomAt(factor, clientX, clientY) {
            const [x, y] = toDiagram(clientX, clientY);
            setWidth(view.width / factor, x, y);
        }

        function zoomCenter(factor) {
            const rect = container.getBoundingClientRect();
            zoomAt(factor, rect.left + rect.width / 2, rect.top + rect.height / 2);
        }

        // Trackpad and wheel: scroll pans; pinch (sent as ctrl+wheel) or ctrl/cmd+wheel zooms.
        container.addEventListener("wheel", (event) => {
            event.preventDefault();
            if (event.ctrlKey || event.metaKey) {
                zoomAt(Math.exp(-event.deltaY * 0.01), event.clientX, event.clientY);
                return;
            }
            const unitsPerPixel = view.width / container.clientWidth;
            view.x += event.deltaX * unitsPerPixel;
            view.y += event.deltaY * unitsPerPixel;
            apply();
        }, {passive: false});

        // Drag pans. A drag that started on a link must not follow it.
        let drag = null;
        container.addEventListener("pointerdown", (event) => {
            if (event.button !== 0) {
                return;
            }
            drag = {x: event.clientX, y: event.clientY, view: {...view}, moved: false};
        });
        container.addEventListener("pointermove", (event) => {
            if (!drag) {
                return;
            }
            const dx = event.clientX - drag.x;
            const dy = event.clientY - drag.y;
            if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) {
                return;
            }
            if (!drag.moved) {
                drag.moved = true;
                container.setPointerCapture(event.pointerId);
                container.classList.add("wd-dragging");
            }
            const unitsPerPixel = view.width / container.clientWidth;
            view.x = drag.view.x - dx * unitsPerPixel;
            view.y = drag.view.y - dy * unitsPerPixel;
            apply();
        });
        function endDrag() {
            container.classList.remove("wd-dragging");
            if (drag && drag.moved) {
                container.addEventListener("click", (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                }, {capture: true, once: true});
            }
            drag = null;
        }
        container.addEventListener("pointerup", endDrag);
        container.addEventListener("pointercancel", endDrag);

        wrapper.querySelectorAll("[data-wd-zoom]").forEach((button) => {
            button.addEventListener("click", () => {
                const action = button.dataset.wdZoom;
                if (action === "in") {
                    zoomCenter(ZOOM_STEP);
                } else if (action === "out") {
                    zoomCenter(1 / ZOOM_STEP);
                } else if (action === "width") {
                    fitWidth();
                } else {
                    fitAll();
                }
            });
        });

        // Wider invisible copies of each cable's path, so thin lines are easy to hover.
        svg.querySelectorAll("g.edge path").forEach((path) => {
            const hit = path.cloneNode(false);
            hit.classList.add("wd-hit");
            hit.removeAttribute("stroke-dasharray");
            path.parentNode.insertBefore(hit, path);
        });

        function clearHighlight() {
            container.classList.remove("wd-focus");
            svg.querySelectorAll(".wd-lit").forEach((element) => element.classList.remove("wd-lit"));
        }

        function highlight(edges) {
            clearHighlight();
            if (!edges.length) {
                return;
            }
            container.classList.add("wd-focus");
            edges.forEach((edge) => {
                edge.classList.add("wd-lit");
                edge.classList.forEach((name) => {
                    if (/^wd-n\d+$/.test(name)) {
                        const node = svg.querySelector(`#${CSS.escape(name)}-node`);
                        if (node) {
                            node.classList.add("wd-lit");
                        }
                    }
                });
            });
        }

        // Hover a cable to trace it, a port to trace its cables, or a device header to trace all of its cables.
        container.addEventListener("pointerover", (event) => {
            if (drag && drag.moved) {
                return;
            }
            const edge = event.target.closest("g.edge");
            if (edge) {
                highlight([edge]);
                return;
            }
            const cell = event.target.closest("g[id^='a_wd-n']");
            if (cell) {
                highlight(Array.from(svg.querySelectorAll(`g.edge.${CSS.escape(cell.id.slice(2))}`)));
                return;
            }
            clearHighlight();
        });
        container.addEventListener("pointerleave", clearHighlight);

        fitWidth();
        window.addEventListener("resize", () => setWidth(view.width, view.x, view.y));
    }

    // wiring-diagram-square.js calls setup() again once its SVG is drawn; until then there is nothing to set up.
    window.NautobotWiringDiagram = {setup: setup, pickPage: pickPage, pageData: pageData};
    document.querySelectorAll("[data-wd-diagram]").forEach(setup);
})();

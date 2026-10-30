# Vendored libraries

Served from Nautobot's static files so the square-line view works without internet access.

| File | Package | License |
|------|---------|---------|
| `elk-0.12.0.bundled.js` | [elkjs](https://github.com/kieler/elkjs) 0.12.0, `lib/elk.bundled.js` | EPL-2.0 ([LICENSE-elkjs.md](LICENSE-elkjs.md)) |
| `jspdf-4.2.1.umd.min.js` | [jsPDF](https://github.com/parallax/jsPDF) 4.2.1, `dist/jspdf.umd.min.js` | MIT ([LICENSE-jspdf](LICENSE-jspdf)) |
| `svg2pdf-2.8.1.umd.min.js` | [svg2pdf.js](https://github.com/yWorks/svg2pdf.js) 2.8.1, `dist/svg2pdf.umd.min.js` | MIT ([LICENSE-svg2pdf](LICENSE-svg2pdf)) |

The files are unmodified except that the `sourceMappingURL` comment was removed from the two minified files,
since their source maps are not shipped. To update one, copy the same file from the new npm release, rename
it with the new version, and update the references in `templates/nautobot_wiring_diagrams/inc/diagram.html`.

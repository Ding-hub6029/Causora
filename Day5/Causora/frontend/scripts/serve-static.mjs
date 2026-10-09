// Serves an explicit static or live export under ./builds without any dependency.
// PORT and HOST environment variables are honoured; defaults are 3000 and 0.0.0.0.
import http from "node:http";
import https from "node:https";
import fs from "node:fs";
import path from "node:path";

const frontend = path.resolve(import.meta.dirname, "..");
const mode = process.env.CAUSORA_FRONTEND_MODE ?? ((process.env.CAUSORA_STATIC_ONLY === "true" || process.env.NEXT_PUBLIC_CAUSORA_STATIC_ONLY === "true") ? "static" : "live");
if (!["live", "static"].includes(mode)) throw new Error("CAUSORA_FRONTEND_MODE must be live or static.");
const variant = path.join(frontend, "builds", mode);
const root = variant;
const markerPath = path.join(root, ".causora-build.json");
if (fs.existsSync(markerPath) && JSON.parse(fs.readFileSync(markerPath, "utf8")).mode !== mode) {
  throw new Error(`Frontend build does not match ${mode} mode. Run npm run build:previews first.`);
}
const port = Number(process.env.PORT ?? 3000);
const host = process.env.HOST ?? "0.0.0.0";
const staticOnly = mode === "static";
// Keep the browser on one origin. This also works when a preview browser
// restricts cross-origin POSTs to another loopback port.
const backend = new URL(process.env.CAUSORA_BACKEND_URL ?? "http://127.0.0.1:8000");
if (!["http:", "https:"].includes(backend.protocol) || backend.username || backend.password) {
  throw new Error("CAUSORA_BACKEND_URL must be an HTTP(S) URL without credentials.");
}
const types = { ".pdf": "application/pdf", ".csv": "text/csv; charset=utf-8", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".html": "text/html; charset=utf-8", ".mjs": "text/javascript; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".txt": "text/plain", ".woff2": "font/woff2" };

if (!fs.existsSync(path.join(root, "index.html"))) {
  console.error(`builds/${mode}/index.html is missing. Run \`npm run build:previews\` first.`);
  process.exit(1);
}

http.createServer((request, response) => {
  let file;
  try {
    const url = new URL(request.url ?? "/", "http://localhost");
    if (url.pathname === "/health" || url.pathname.startsWith("/api/")) {
      if (staticOnly) {
        response.writeHead(503, { "Content-Type": "application/json", "Cache-Control": "no-store", "X-Causora-Backend-Status": "not-configured" });
        response.end(JSON.stringify({ error: { code: "backend_not_configured", message: "This static-only preview has no public API backend." } }));
        return;
      }
      const upstreamUrl = new URL(`${url.pathname}${url.search}`, backend);
      const headers = { ...request.headers, host: upstreamUrl.host };
      delete headers.connection;
      const upstream = (backend.protocol === "https:" ? https : http).request(upstreamUrl, {
        method: request.method, headers, timeout: 60_000,
      }, (incoming) => {
        response.writeHead(incoming.statusCode ?? 502, incoming.headers);
        incoming.pipe(response);
      });
      upstream.on("timeout", () => upstream.destroy(new Error("Backend timeout")));
      upstream.on("error", () => {
        if (!response.headersSent) {
          response.writeHead(502, { "Content-Type": "application/json" });
          response.end(JSON.stringify({ error: { code: "simulation_failed", message: "Simulation service is unavailable. Existing results remain available." } }));
        } else response.destroy();
      });
      request.on("aborted", () => upstream.destroy());
      request.pipe(upstream);
      return;
    }
    file = path.resolve(root, `.${decodeURIComponent(url.pathname)}`);
  } catch {
    response.writeHead(400); response.end("Invalid URL"); return;
  }
  if (file !== root && !file.startsWith(`${root}${path.sep}`)) { response.writeHead(403); response.end(); return; }
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, "index.html");
  if (!fs.existsSync(file) && fs.existsSync(`${file}.html`)) file = `${file}.html`;
  if (!fs.existsSync(file)) { file = path.join(root, "404.html"); response.statusCode = 404; }
  if (!fs.existsSync(file)) { response.writeHead(404); response.end("Not found"); return; }
  response.setHeader("Content-Type", types[path.extname(file)] ?? "application/octet-stream");
  fs.createReadStream(file).pipe(response);
}).listen(port, host, () => console.log(`Causora static site listening on http://${host}:${port}`));


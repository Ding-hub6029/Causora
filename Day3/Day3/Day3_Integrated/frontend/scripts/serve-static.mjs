// Serves the static export in ./out without any dependency. Used by `npm start`.
// PORT and HOST environment variables are honoured; defaults are 3000 and 0.0.0.0.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..", "out");
const port = Number(process.env.PORT ?? 3000);
const host = process.env.HOST ?? "0.0.0.0";
const types = { ".pdf": "application/pdf", ".csv": "text/csv; charset=utf-8", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".txt": "text/plain", ".woff2": "font/woff2" };

if (!fs.existsSync(path.join(root, "index.html"))) {
  console.error("out/index.html is missing. Run `npm run build` first.");
  process.exit(1);
}

http.createServer((request, response) => {
  let file;
  try {
    const url = new URL(request.url ?? "/", "http://localhost");
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


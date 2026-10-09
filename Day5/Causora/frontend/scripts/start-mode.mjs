import { spawn } from "node:child_process";
import path from "node:path";
const mode = process.argv[2];
if (!["live", "static"].includes(mode)) throw new Error("Use live or static.");
const child = spawn(process.execPath, [path.join(import.meta.dirname, "serve-static.mjs")], { stdio: "inherit", env: { ...process.env, CAUSORA_FRONTEND_MODE: mode, CAUSORA_STATIC_ONLY: String(mode === "static"), NEXT_PUBLIC_CAUSORA_STATIC_ONLY: String(mode === "static") } });
child.on("error", error => { console.error(error.message); process.exitCode = 1; });
child.on("exit", code => { process.exitCode = code ?? 1; });
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => child.kill(signal));

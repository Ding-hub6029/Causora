import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";

const source = resolve("node_modules/pdfjs-dist/build/pdf.worker.min.mjs");
const destinationDirectory = resolve("public");
const destination = resolve(destinationDirectory, "pdf.worker.min.mjs");

if (!existsSync(source)) {
  console.error("PDF.js worker is missing. Run npm ci before starting the frontend.");
  process.exitCode = 1;
} else {
  mkdirSync(destinationDirectory, { recursive: true });
  copyFileSync(source, destination);
  console.log("Prepared the local PDF.js worker asset.");
}

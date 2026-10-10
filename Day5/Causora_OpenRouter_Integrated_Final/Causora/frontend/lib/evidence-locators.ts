export type PdfLocator = [number, number, number, number];
export type ViewportBox = { x: number; y: number; width: number; height: number };
export type LocatorSource = "api-bbox" | "exact-source-text";
export type ResolvedLocator = { box: ViewportBox; source: LocatorSource };

export type PdfTextItem = {
  str: string;
  transform: number[];
  width: number;
  height: number;
};

export type PdfViewport = {
  width: number;
  height: number;
  convertToViewportPoint(x: number, y: number): number[];
};

function normalizeText(value: string): string {
  return value.normalize("NFC").replace(/\s+/g, " ").trim();
}

function toViewportBox(pdfRect: number[], viewport: PdfViewport): ViewportBox | null {
  const first = viewport.convertToViewportPoint(pdfRect[0], pdfRect[1]);
  const second = viewport.convertToViewportPoint(pdfRect[2], pdfRect[3]);
  if (first.length !== 2 || second.length !== 2 || [...first, ...second].some((part) => !Number.isFinite(part))) return null;
  const x = Math.min(first[0], second[0]);
  const y = Math.min(first[1], second[1]);
  const right = Math.max(first[0], second[0]);
  const bottom = Math.max(first[1], second[1]);
  if (x < 0 || y < 0 || right > viewport.width || bottom > viewport.height || right <= x || bottom <= y) return null;
  return { x, y, width: right - x, height: bottom - y };
}

/** Uses a server-provided PDF-point bbox, or derives a rectangle only from an exact quote in the cited page text. */
export function resolveEvidenceLocator(
  items: PdfTextItem[],
  quote: string,
  bbox: PdfLocator | null,
  viewport: PdfViewport
): ResolvedLocator | null {
  if (bbox) {
    if (bbox.some((value) => !Number.isFinite(value)) || bbox[0] < 0 || bbox[1] < 0 || bbox[2] <= bbox[0] || bbox[3] <= bbox[1]) return null;
    const box = toViewportBox(bbox, viewport);
    return box ? { box, source: "api-bbox" } : null;
  }
  const target = normalizeText(quote);
  if (!target) return null;
  let fullText = "";
  const spans: Array<{ start: number; end: number; item: PdfTextItem }> = [];
  for (const item of items) {
    if (typeof item.str !== "string" || !item.str.trim()) continue;
    const segment = normalizeText(item.str);
    if (!segment) continue;
    if (fullText) fullText += " ";
    const start = fullText.length;
    fullText += segment;
    spans.push({ start, end: fullText.length, item });
  }
  const start = fullText.indexOf(target);
  if (start < 0) return null;
  const end = start + target.length;
  const boxes = spans.filter((span) => span.start < end && span.end > start).map(({ item }) => {
    if (item.transform.length < 6 || !Number.isFinite(item.transform[4]) || !Number.isFinite(item.transform[5]) || !Number.isFinite(item.width) || !Number.isFinite(item.height) || item.width <= 0 || item.height <= 0) return null;
    const x = item.transform[4];
    const baselineY = item.transform[5];
    return toViewportBox([x, baselineY - item.height, x + item.width, baselineY], viewport);
  }).filter((box): box is ViewportBox => box !== null);
  if (!boxes.length) return null;
  const left = Math.min(...boxes.map((box) => box.x));
  const top = Math.min(...boxes.map((box) => box.y));
  const right = Math.max(...boxes.map((box) => box.x + box.width));
  const bottom = Math.max(...boxes.map((box) => box.y + box.height));
  if (right <= left || bottom <= top) return null;
  return { box: { x: left, y: top, width: right - left, height: bottom - top }, source: "exact-source-text" };
}

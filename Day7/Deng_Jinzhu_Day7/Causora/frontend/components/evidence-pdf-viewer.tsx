"use client";

import { useEffect, useState } from "react";
import type { EvidenceRecord } from "@/lib/contracts";
import { evidenceSourceHref } from "@/lib/evidence-api";
import { resolveEvidenceLocator, type ResolvedLocator } from "@/lib/evidence-locators";

type ViewerState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; width: number; height: number; pageCount: number; locator: ResolvedLocator | null; locatorNotice: string };

type PdfJsPage = {
  getViewport(options: { scale: number }): { width: number; height: number; convertToViewportPoint(x: number, y: number): number[] };
  getTextContent(): Promise<{ items: Array<{ str?: string; transform?: number[]; width?: number; height?: number }> }>;
  render(options: { canvas: HTMLCanvasElement; canvasContext: CanvasRenderingContext2D; viewport: ReturnType<PdfJsPage["getViewport"]> }): { promise: Promise<void>; cancel(): void };
};

type PdfJsDocument = { numPages: number; getPage(pageNumber: number): Promise<PdfJsPage> };

type PdfJsLoadingTask = { promise: Promise<PdfJsDocument>; destroy(): Promise<void> };

type PdfJsModule = {
  GlobalWorkerOptions: { workerSrc: string };
  getDocument(options: { url: string; withCredentials?: boolean }): PdfJsLoadingTask;
};

export function EvidencePdfViewer({ evidence }: { evidence: EvidenceRecord }) {
  const [state, setState] = useState<ViewerState>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const sourceHref = evidenceSourceHref(evidence);
  const sourceUrl = sourceHref?.split("#", 1)[0] ?? null;

  useEffect(() => {
    let disposed = false;
    let loadingTask: PdfJsLoadingTask | undefined;
    let documentProxy: PdfJsDocument | undefined;
    let renderTask: ReturnType<PdfJsPage["render"]> | undefined;
    const canvas = document.querySelector<HTMLCanvasElement>(`[data-evidence-canvas="${CSS.escape(evidence.id)}"]`);

    async function loadPage() {
      setState({ status: "loading" });
      if (!sourceUrl) {
        setState({ status: "error", message: "This source file is not in the approved local evidence bundle." });
        return;
      }
      try {
        const pdfjs = await import("pdfjs-dist") as unknown as PdfJsModule;
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
        loadingTask = pdfjs.getDocument({ url: sourceUrl, withCredentials: false });
        documentProxy = await loadingTask.promise;
        if (disposed) return;
        if (!Number.isSafeInteger(evidence.page) || evidence.page < 1 || evidence.page > documentProxy.numPages) {
          setState({ status: "error", message: `Page ${evidence.page} is outside the source document (1–${documentProxy.numPages}).` });
          return;
        }
        const page = await documentProxy.getPage(evidence.page);
        if (disposed) return;
        const viewport = page.getViewport({ scale: 1.5 });
        const activeCanvas = canvas ?? document.querySelector<HTMLCanvasElement>(`[data-evidence-canvas="${CSS.escape(evidence.id)}"]`);
        const context = activeCanvas?.getContext("2d");
        if (!activeCanvas || !context) throw new Error("The PDF canvas is unavailable in this browser.");
        activeCanvas.width = Math.ceil(viewport.width);
        activeCanvas.height = Math.ceil(viewport.height);
        renderTask = page.render({ canvas: activeCanvas, canvasContext: context, viewport });
        await renderTask.promise;
        if (disposed) return;
        const textContent = await page.getTextContent();
        const items = textContent.items.flatMap((item) => {
          if (typeof item.str !== "string" || !Array.isArray(item.transform) || typeof item.width !== "number" || typeof item.height !== "number") return [];
          return [{ str: item.str, transform: item.transform, width: item.width, height: item.height }];
        });
        const locator = resolveEvidenceLocator(items, evidence.quote, evidence.locatorBbox, viewport);
        const locatorNotice = locator?.source === "api-bbox"
          ? "Server-provided PDF bounding box highlighted."
          : locator?.source === "exact-source-text"
            ? "No bbox was supplied; the highlight was derived from an exact text match to the preserved quote on this PDF page."
            : evidence.locatorBbox
              ? "The supplied bbox is outside this page; no highlight was drawn."
              : "No exact quote location is available on this page; no highlight was drawn.";
        setState({ status: "ready", width: viewport.width, height: viewport.height, pageCount: documentProxy.numPages, locator, locatorNotice });
      } catch (error) {
        if (disposed) return;
        const message = error instanceof Error && /fetch|network|404|loading|unexpected server response|server response|http status/i.test(error.message)
          ? "The source PDF could not be loaded. Check the local demo assets and retry."
          : error instanceof Error ? error.message : "The source PDF could not be rendered.";
        setState({ status: "error", message });
      }
    }

    void loadPage();
    return () => {
      disposed = true;
      renderTask?.cancel();
      void loadingTask?.destroy().catch(() => undefined);
    };
  }, [attempt, evidence.id, evidence.page, evidence.quote, evidence.locatorBbox, sourceUrl]);

  return <section className="evidence-pdf-viewer" aria-label={`Source PDF page ${evidence.page}`}>
    <div className="evidence-pdf-viewer-head"><b>Source document · page {evidence.page}</b>{state.status === "ready" && <span>{state.pageCount} pages</span>}</div>
    {state.status === "loading" && <p className="evidence-pdf-status" role="status">Loading the original PDF page…</p>}
    {state.status === "error" && <div className="evidence-pdf-error" role="alert"><p>{state.message}</p><button type="button" onClick={() => setAttempt((current) => current + 1)}>Retry PDF load</button></div>}
    <div className={`evidence-pdf-page ${state.status === "ready" ? "ready" : ""}`}>
      <canvas data-evidence-canvas={evidence.id} aria-label={`PDF page ${evidence.page}`} />
      {state.status === "ready" && state.locator && <svg className="evidence-pdf-overlay" viewBox={`0 0 ${state.width} ${state.height}`} preserveAspectRatio="none" role="img" aria-label={state.locator.source === "api-bbox" ? "Source location highlighted from API bbox" : "Source location highlighted from exact quote text"}>
        <rect x={state.locator.box.x} y={state.locator.box.y} width={state.locator.box.width} height={state.locator.box.height} />
      </svg>}
    </div>
    {state.status === "ready" && <p className={`evidence-locator-note ${state.locator ? "matched" : "unlocated"}`} role="status">{state.locatorNotice}</p>}
    {sourceHref && <a className="evidence-open-source" href={sourceHref} target="_blank" rel="noopener noreferrer">Open source PDF at page {evidence.page}<span aria-hidden="true">↗</span></a>}
  </section>;
}

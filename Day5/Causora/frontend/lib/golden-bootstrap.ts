import { loadVerifiedGoldenRun, VERIFIED_GOLDEN_STORAGE_KEY, type StorageLike, type VerifiedGoldenRun } from "./golden-cache";

export const VERIFIED_GOLDEN_ASSET_PATH = "/golden/verified_golden_e2e.json";
const MAX_GOLDEN_BYTES = 1_500_000;

export type GoldenSource = "browser-cache" | "static-bundle";

export type LoadedVerifiedGoldenRun = {
  run: VerifiedGoldenRun;
  source: GoldenSource;
  json: string;
};

function browserStorage(): StorageLike | null {
  if (typeof window === "undefined") return null;
  try { return window.localStorage; }
  catch { return null; }
}

function memoryStorage(raw: string): StorageLike {
  return {
    getItem: (key) => key === VERIFIED_GOLDEN_STORAGE_KEY ? raw : null,
    setItem: () => undefined,
    removeItem: () => undefined
  };
}

function assertSameOriginAssetPath(path: string): void {
  if (path !== VERIFIED_GOLDEN_ASSET_PATH) {
    throw new Error("Verified Golden must be loaded from a fixed same-origin static path.");
  }
}

export async function loadAvailableVerifiedGoldenRun(
  storage: StorageLike | null = browserStorage(),
  fetchImpl: typeof fetch = fetch,
  assetPath: string = VERIFIED_GOLDEN_ASSET_PATH
): Promise<LoadedVerifiedGoldenRun | null> {
  if (storage) {
    try {
      const cachedJson = storage.getItem(VERIFIED_GOLDEN_STORAGE_KEY);
      if (cachedJson) {
        const run = await loadVerifiedGoldenRun(memoryStorage(cachedJson));
        if (run) return { run, source: "browser-cache", json: cachedJson };
      }
    } catch {
      // A corrupted or inaccessible browser cache must not block the integrity-checked static fallback.
    }
  }

  assertSameOriginAssetPath(assetPath);
  const response = await fetchImpl(assetPath, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "force-cache",
    credentials: "same-origin"
  });
  if (!response.ok) throw new Error(`Bundled Verified Golden is unavailable (HTTP ${response.status}).`);
  const contentType = response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase();
  if (contentType !== "application/json") throw new Error("Bundled Verified Golden did not return application/json.");
  const json = await response.text();
  if (new TextEncoder().encode(json).byteLength > MAX_GOLDEN_BYTES) throw new Error("Bundled Verified Golden exceeds the safe download limit.");

  try {
    const run = await loadVerifiedGoldenRun(memoryStorage(json));
    if (!run) return null;
    return { run, source: "static-bundle", json };
  } catch (error) {
    throw new Error(`Bundled Verified Golden failed production validation: ${error instanceof Error ? error.message : "invalid record"}`);
  }
}

import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import path from "node:path";
import configuration from "../eslint.config.mjs";

test("Configured Next lint root resolution does not evaluate externally supplied brace/glob patterns", () => {
  const require = createRequire(import.meta.url);
  const glob = require("fast-glob");
  const original = glob.globSync;
  let calls = 0;
  glob.globSync = () => { calls += 1; throw new Error("Unexpected glob evaluation"); };
  try {
    const { getRootDirs } = require(path.resolve(import.meta.dirname, "../node_modules/@next/eslint-plugin-next/dist/utils/get-root-dirs.js"));
    for (const item of configuration) {
      assert.equal(item.settings?.next?.rootDir, undefined, "A glob-based Next root override needs a new security review.");
    }
    const cwd = "/reviewed-project/" + "{".repeat(1000) + "x" + "}".repeat(1000);
    assert.deepEqual(getRootDirs({ cwd, settings: {} }), [cwd]);
    assert.equal(calls, 0, "The configured lint path must not invoke the vulnerable expansion path.");
  } finally { glob.globSync = original; }
});

import js from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: [".next/**", "next-env.d.ts", "node_modules/**", "out/**", "artifacts/**"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  nextPlugin.flatConfig.coreWebVitals,
  { files: ["tests/**/*.mjs"], languageOptions: { globals: { structuredClone: "readonly", fetch: "readonly", setTimeout: "readonly", clearTimeout: "readonly" } } },
  {
    files: ["scripts/**/*.mjs"],
    languageOptions: { globals: { process: "readonly", console: "readonly", URL: "readonly" } }
  },
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-unused-vars": "error"
    }
  }
);

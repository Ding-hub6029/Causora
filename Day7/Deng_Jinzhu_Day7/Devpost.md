# Devpost Submission Draft

## Project name
Causora

## Tagline
Trace the choice before you make it.

## Inspiration
A cheaper quote can hide a more expensive commitment. A supplier renewal, a locked minimum purchase and falling demand can interact across finance, operations and contract risk. We built Causora to make these interactions inspectable before a person makes a decision.

## What it does
Causora turns a synthetic supplier decision into an evidence-to-decision workflow: source documents and reviewed variables, a 104-week simulation, a three-option scenario matrix, Formula Trace, bounded CFO/COO/Risk reviews, a Critic, and a run-bound Decision Brief. A person retains the final choice.

## How we built it
Next.js and TypeScript provide the workflow. A Python/FastAPI service computes numerical outputs over a 24-month horizon, with fixed-seed Monte Carlo sampling and constraint screening. OpenRouter provides real qualitative model responses. the primary model is GPT-5 mini and the preferred Critic is Gemini 3.1 Pro Preview, with validated fallback. Numerical claims are bound to computed references and checked before display. PostgreSQL preserves the public AI budget history. Vercel hosts the frontend. Render hosts the backend and database.

## Why not just ChatGPT and Excel?
An open-ended answer and a spreadsheet can help, but the user still has to reconcile citations, contract obligations, scenarios and recommendations. Causora binds all stages to the same simulation, scenario and data version and lets the user inspect the underlying formulas. We do not claim universal model superiority: our existing small comparison is prompt-sensitive and does not establish a fair mathematical accuracy benchmark or unseen Critic recall.

## Challenges
Real model outputs sometimes failed shape, numerical or semantic checks. We retained those failures, added bounded correction and fallback, and preserved the validated Matrix whenever the AI stage failed. Free-service cold starts required a clearly labelled, validated historical Golden cache. Public AI access needed persistent budget accounting and review admission protection.

## Accomplishments
Real Baseline and Demand −15% reviews completed with provider receipts. the current workflow displays matched Critic and Numeric Guardrail validation. The Day6 freeze includes regression logs, source hashes, Golden tamper rejection, nine-cell cost reconciliation and fixed-seed/cross-seed mathematical checks.

## What we learned
Traceability depends on identity and source integrity as much as output fluency. A low expected cost can conflict with stockout constraints. contractual minimums can retain exposure when demand changes. A human should be able to challenge an apparently persuasive recommendation.

## What's next
Independent unseen evaluation, more external users, broader source formats and multi-worker rate limiting. The MVP uses synthetic data and is not financial or legal advice. Browser-local approval is not a signed procurement action. AI and free hosting may fail. the cache is a historical replay rather than a new model call.

## Built with
Next.js, React, TypeScript, Python, FastAPI, NumPy, OpenRouter, OpenAI GPT-5 mini, Google Gemini 3.1 Pro Preview, PostgreSQL, Vercel, Render, PDF.js.

## Links and team
Live: https://causora-one.vercel.app/
GitHub: https://github.com/Ding-hub6029/Causora
Team display names to verify against actual accounts: Ding Xiangfeng / Deng Jinzhu / Wang Hao.
Demo video: https://www.youtube.com/watch?v=p5eHs-XzPVk

The team selected this video as the final demo on 2026-10-10. This text is ready-to-copy submission material. Actual Devpost submission and member-account confirmation are not recorded in this package.

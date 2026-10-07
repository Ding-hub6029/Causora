# Day 2 Preview and Acceptance

Complete frontend source and its static export are included in this historical Day 2 package. Extract, enter causora, and on Windows run START_PREVIEW.cmd; keep its window open and visit http://127.0.0.1:3000. Node.js 22 is required. If busy, set PORT=3012 in the terminal before starting; verify the preview is this version.

Source reproduction: `npm ci`, then `npm run check`. Installation/build need network. Included out/ can be previewed directly; deploy its contents at the static site root.

Historical checks: 25 tests including HTTP preview, typecheck, lint and production build passed. Shared v4.1 contracts/data unchanged. This frontend is static mock and does not include Deng's real engine or Wang's evidence service.

PDF Day 2 requires actual external user testing: follow USER_TESTING_KIT.md and record observations in USER_TEST_FEEDBACK_DAY2.csv. Prefer 2-3 external participants; record roles/tasks/feedback/issues. Without real feedback, do not claim personal Day 2 fully complete. Team G2 also requires working BusinessVariable fields and deterministic matrix.

Old V4/Day 1 documents are historical references. Current Day 2 runtime/testing status is in README, DAY2_TEST_REPORT and this note; current integrated status is in Day3_Integrated.zip.

# Reproducible checks

Node.js 22 and npm required. From a clean checkout:

```sh
npm ci
npm run check
```

check runs typecheck, lint, 24 source/data tests, production build, then one HTTP static-server test. The latter requires the freshly built out directory. For offline source iteration, npm test does not require a prior build.

See DAY2_TEST_REPORT.md for actual execution and USER_TESTING_KIT.md for external participant sessions. Browser QA by the builder is not a participant session.

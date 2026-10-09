# Test report index

The final verified report, including fresh-unzip installation, exact package versions, HTTP smoke captures, data reproduction and all regression results, is [TEST_REPORT_FINAL.md](TEST_REPORT_FINAL.md).

**Final result:** 63 passed, 37 subtests passed. The default local service intentionally returns a v1 503 until genuine Wang review, three-owner policy and v2 release records are configured. The separate `start_unreviewed_dev.py` launcher exercises the real v2 shape only with explicit `UNREVIEWED_DEV_ONLY` labels and `decisionReady:false`. It is not production evidence.

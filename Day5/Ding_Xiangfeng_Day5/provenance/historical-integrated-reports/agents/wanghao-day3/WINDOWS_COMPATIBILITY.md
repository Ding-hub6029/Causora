# Windows verification

Native Windows tests were independently executed using Python 3.12 and portalocker 3.2.0 with pywin32: 294 AI tests passed, including shared-journal preparation, multiprocess contention and bounded locking. See verification/wang_day4/codex_final_revision/logs/ai_tests_windows.log.

Both requirement files retain portalocker. Budget reservations, durable cumulative expense, unknown fees and atomic replacement remain enforced. No platform test is skipped. This validates the tested local Windows filesystem, not network shares or distributed storage. Cooperating service processes must share a persistent private budget journal.

"""Professional test report runner for the C formatter suite."""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from types import TracebackType


TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(TEST_DIR))


class ReportResult(unittest.TestResult):
    """Collect test outcomes and print a concise status table."""

    def __init__(self) -> None:
        super().__init__()
        self.started_at = 0.0
        self.test_started_at = 0.0
        self.records: list[tuple[str, str, float]] = []

    def startTestRun(self) -> None:
        """Print the report header."""

        self.started_at = time.perf_counter()
        print("C Formatter Test Report")
        print("=" * 72)
        print(f"{'Status':<8} {'Time':>8}  Test")
        print("-" * 72)

    def startTest(self, test: unittest.case.TestCase) -> None:
        """Record per-test start time."""

        super().startTest(test)
        self.test_started_at = time.perf_counter()

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        """Record and print a passing test."""

        super().addSuccess(test)
        self._record("PASS", test)

    def addFailure(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, TracebackType],
    ) -> None:
        """Record and print a failing test."""

        super().addFailure(test, err)
        self._record("FAIL", test)

    def addError(
        self,
        test: unittest.case.TestCase,
        err: tuple[type[BaseException], BaseException, TracebackType],
    ) -> None:
        """Record and print a test error."""

        super().addError(test, err)
        self._record("ERROR", test)

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
        """Record and print a skipped test."""

        super().addSkip(test, reason)
        self._record("SKIP", test)

    def stopTestRun(self) -> None:
        """Print summary and detailed failure diagnostics."""

        total_elapsed = time.perf_counter() - self.started_at
        print("-" * 72)
        print(
            f"Summary: {self.testsRun} tests, "
            f"{len(self.failures)} failures, {len(self.errors)} errors, "
            f"{len(self.skipped)} skipped in {total_elapsed:.3f}s"
        )
        self._print_performance_metrics()
        if self.failures or self.errors:
            self._print_diagnostics()

    def _record(self, status: str, test: unittest.case.TestCase) -> None:
        """Save one outcome and print it as a table row."""

        elapsed = time.perf_counter() - self.test_started_at
        name = test.shortDescription() or str(test)
        self.records.append((status, name, elapsed))
        print(f"{status:<8} {elapsed:>7.3f}s  {name}")

    def _print_performance_metrics(self) -> None:
        """Print formatter throughput measurements captured by tests."""

        try:
            from test_c_formatter import PERFORMANCE_RESULTS
        except ImportError:
            return

        if not PERFORMANCE_RESULTS:
            return

        print("\nPerformance")
        print("-" * 72)
        for metric in PERFORMANCE_RESULTS:
            print(
                f"{metric['name']}: "
                f"{metric['functions']:,} functions, "
                f"{metric['input_chars']:,} chars, "
                f"{metric['elapsed_seconds']:.3f}s, "
                f"{metric['chars_per_second']:,.0f} chars/s"
            )

    def _print_diagnostics(self) -> None:
        """Print failure and error tracebacks after the summary."""

        print("\nDiagnostics")
        print("-" * 72)
        for label, entries in (("FAIL", self.failures), ("ERROR", self.errors)):
            for test, traceback in entries:
                print(f"\n{label}: {test}")
                print(traceback.rstrip())


class ReportRunner:
    """Run a unittest suite with ReportResult."""

    resultclass = ReportResult

    def run(self, suite: unittest.TestSuite) -> ReportResult:
        """Execute the suite and return the result."""

        result = self.resultclass()
        result.startTestRun()
        try:
            suite.run(result)
        finally:
            result.stopTestRun()
        return result


def main() -> int:
    """Discover and run all formatter tests."""

    loader = unittest.TestLoader()
    suite = loader.discover(str(TEST_DIR), pattern="test_*.py")
    result = ReportRunner().run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

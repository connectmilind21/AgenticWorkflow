"""
Benchmarking suite for evaluating agent performance.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkCase:
    """A single benchmark test case."""

    id: str
    name: str
    task: str
    expected_output_contains: list[str] | None = None
    expected_status: str = "success"
    max_execution_time: float = 60.0
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark case."""

    case_id: str
    case_name: str
    passed: bool
    execution_time: float
    actual_status: str
    score: float = 0.0
    notes: list[str] = field(default_factory=list)
    error: str | None = None


class AgentBenchmark:
    """
    Benchmarks an agent against a set of test cases.

    Measures:
    - Task success rate
    - Average execution time
    - Output quality scores
    """

    def __init__(
        self,
        name: str,
        agent: Any,
        cases: list[BenchmarkCase] | None = None,
    ) -> None:
        self.name = name
        self.agent = agent
        self.cases = cases or []
        self._logger = logger.bind(benchmark=name)

    def add_case(self, case: BenchmarkCase) -> None:
        """Add a test case to the benchmark."""
        self.cases.append(case)

    def run(self) -> list[BenchmarkResult]:
        """Run all benchmark cases and return results."""
        results: list[BenchmarkResult] = []

        for case in self.cases:
            self._logger.info("Running case", case_id=case.id)
            result = self._run_case(case)
            results.append(result)
            self._logger.info(
                "Case complete",
                case_id=case.id,
                passed=result.passed,
                time=result.execution_time,
            )

        return results

    def _run_case(self, case: BenchmarkCase) -> BenchmarkResult:
        """Run a single benchmark case."""
        start = time.time()
        try:
            agent_result = self.agent.run(case.task, case.context)
            duration = time.time() - start

            actual_status = (
                agent_result.status.value
                if hasattr(agent_result, "status")
                else "unknown"
            )
            passed = actual_status == case.expected_status

            score = 1.0 if passed else 0.0
            notes: list[str] = []

            if duration > case.max_execution_time:
                notes.append(f"Exceeded time limit: {duration:.2f}s > {case.max_execution_time}s")
                score *= 0.5

            if case.expected_output_contains:
                output_str = str(getattr(agent_result, "output", ""))
                for expected in case.expected_output_contains:
                    if expected.lower() in output_str.lower():
                        score = min(1.0, score + 0.1)
                    else:
                        notes.append(f"Missing expected content: '{expected}'")

            return BenchmarkResult(
                case_id=case.id,
                case_name=case.name,
                passed=passed,
                execution_time=duration,
                actual_status=actual_status,
                score=score,
                notes=notes,
            )

        except Exception as exc:
            duration = time.time() - start
            return BenchmarkResult(
                case_id=case.id,
                case_name=case.name,
                passed=False,
                execution_time=duration,
                actual_status="error",
                score=0.0,
                error=str(exc),
            )


class BenchmarkSuite:
    """
    Collection of benchmarks for comprehensive agent evaluation.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.benchmarks: list[AgentBenchmark] = []

    def add_benchmark(self, benchmark: AgentBenchmark) -> None:
        """Add a benchmark to the suite."""
        self.benchmarks.append(benchmark)

    def run_all(self) -> dict[str, Any]:
        """Run all benchmarks and return a summary."""
        all_results: dict[str, list[BenchmarkResult]] = {}

        for benchmark in self.benchmarks:
            all_results[benchmark.name] = benchmark.run()

        return self._summarize(all_results)

    def _summarize(
        self, results: dict[str, list[BenchmarkResult]]
    ) -> dict[str, Any]:
        """Summarize benchmark results."""
        summary: dict[str, Any] = {
            "suite": self.name,
            "benchmarks": {},
            "overall": {},
        }

        all_passed = 0
        all_total = 0
        all_scores: list[float] = []

        for benchmark_name, benchmark_results in results.items():
            passed = sum(1 for r in benchmark_results if r.passed)
            total = len(benchmark_results)
            avg_score = (
                sum(r.score for r in benchmark_results) / total if total else 0.0
            )
            avg_time = (
                sum(r.execution_time for r in benchmark_results) / total if total else 0.0
            )

            summary["benchmarks"][benchmark_name] = {
                "passed": passed,
                "total": total,
                "pass_rate": passed / total if total else 0.0,
                "avg_score": avg_score,
                "avg_time_s": avg_time,
                "results": [
                    {
                        "id": r.case_id,
                        "name": r.case_name,
                        "passed": r.passed,
                        "score": r.score,
                        "time_s": r.execution_time,
                        "notes": r.notes,
                        "error": r.error,
                    }
                    for r in benchmark_results
                ],
            }

            all_passed += passed
            all_total += total
            all_scores.extend(r.score for r in benchmark_results)

        summary["overall"] = {
            "total_cases": all_total,
            "passed": all_passed,
            "pass_rate": all_passed / all_total if all_total else 0.0,
            "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0.0,
        }

        return summary

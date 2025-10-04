"""
Evaluation Harness

Standardized framework for evaluating agent performance.
"""

import time
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

console = Console()


@dataclass
class EvaluationResult:
    """Result of a single evaluation."""
    input: str
    expected: Optional[str]
    actual: str
    metrics: Dict[str, float]
    passed: bool
    duration: float
    metadata: Dict[str, Any]


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    total: int
    passed: int
    failed: int
    avg_duration: float
    aggregate_metrics: Dict[str, float]
    results: List[EvaluationResult]


class EvaluationHarness:
    """
    Evaluation harness for testing agent performance.
    
    Supports custom metrics and datasets.
    """
    
    def __init__(self, agent, metrics: Optional[List[Callable]] = None):
        """
        Initialize evaluation harness.
        
        Args:
            agent: Agent to evaluate
            metrics: List of metric functions
        """
        self.agent = agent
        self.metrics = metrics or []
    
    async def evaluate(
        self,
        dataset: List[Dict[str, Any]],
        show_progress: bool = True,
    ) -> EvaluationReport:
        """
        Run evaluation on dataset.
        
        Args:
            dataset: List of test cases with 'input' and 'expected' keys
            show_progress: Whether to show progress bar
            
        Returns:
            EvaluationReport with results
        """
        results = []
        
        with Progress() as progress:
            task = progress.add_task(
                "[cyan]Evaluating...",
                total=len(dataset)
            ) if show_progress else None
            
            for test_case in dataset:
                result = await self._evaluate_single(test_case)
                results.append(result)
                
                if task:
                    progress.update(task, advance=1)
        
        # Generate report
        report = self._generate_report(results)
        
        return report
    
    async def _evaluate_single(self, test_case: Dict[str, Any]) -> EvaluationResult:
        """Evaluate a single test case."""
        input_text = test_case["input"]
        expected = test_case.get("expected")
        
        # Time the agent
        start = time.time()
        actual = await self.agent.process(input_text)
        duration = time.time() - start
        
        # Calculate metrics
        metrics = {}
        for metric_fn in self.metrics:
            try:
                value = metric_fn(
                    input=input_text,
                    expected=expected,
                    actual=actual,
                    duration=duration
                )
                metrics[metric_fn.__name__] = value
            except Exception as e:
                console.print(f"[yellow]Warning: Metric {metric_fn.__name__} failed: {e}[/yellow]")
        
        # Determine pass/fail
        passed = True
        if expected is not None:
            passed = actual.strip().lower() == expected.strip().lower()
        
        return EvaluationResult(
            input=input_text,
            expected=expected,
            actual=actual,
            metrics=metrics,
            passed=passed,
            duration=duration,
            metadata=test_case.get("metadata", {})
        )
    
    def _generate_report(self, results: List[EvaluationResult]) -> EvaluationReport:
        """Generate evaluation report from results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        avg_duration = sum(r.duration for r in results) / total if total > 0 else 0
        
        # Aggregate metrics
        aggregate_metrics = {}
        if results and results[0].metrics:
            for metric_name in results[0].metrics.keys():
                values = [r.metrics[metric_name] for r in results if metric_name in r.metrics]
                if values:
                    aggregate_metrics[metric_name] = sum(values) / len(values)
        
        return EvaluationReport(
            total=total,
            passed=passed,
            failed=failed,
            avg_duration=avg_duration,
            aggregate_metrics=aggregate_metrics,
            results=results
        )
    
    def print_report(self, report: EvaluationReport):
        """Print evaluation report."""
        # Summary
        console.print()
        console.print("[bold]Evaluation Summary[/bold]")
        console.print(f"Total: {report.total}")
        console.print(f"Passed: [green]{report.passed}[/green]")
        console.print(f"Failed: [red]{report.failed}[/red]")
        console.print(f"Pass Rate: {report.passed / report.total * 100:.1f}%")
        console.print(f"Avg Duration: {report.avg_duration:.2f}s")
        
        # Metrics table
        if report.aggregate_metrics:
            console.print()
            console.print("[bold]Aggregate Metrics[/bold]")
            
            table = Table(show_header=True)
            table.add_column("Metric")
            table.add_column("Value", justify="right")
            
            for metric_name, value in report.aggregate_metrics.items():
                table.add_row(metric_name, f"{value:.4f}")
            
            console.print(table)
        
        # Failed cases
        failed_results = [r for r in report.results if not r.passed]
        if failed_results:
            console.print()
            console.print("[bold red]Failed Cases[/bold red]")
            
            for i, result in enumerate(failed_results, 1):
                console.print(f"\n{i}. Input: {result.input}")
                console.print(f"   Expected: {result.expected}")
                console.print(f"   Actual: {result.actual}")

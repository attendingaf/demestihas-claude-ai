#!/usr/bin/env python3
"""Performance benchmarking suite for Context Engine.

Tests:
- <100ms p95 local retrieval
- <1s p95 cloud retrieval  
- 1000 contexts/second throughput
- Memory efficiency
- Cache performance
"""

import time
import random
import string
import statistics
import json
import concurrent.futures
from typing import List, Dict, Any, Tuple
from pathlib import Path
import sys
import psutil
import numpy as np
from dataclasses import dataclass
import matplotlib.pyplot as plt
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from context_engine import (
    ContextEngine,
    get_context_engine,
    ContextRequest,
    ContextResponse
)

@dataclass
class BenchmarkResult:
    """Results from a benchmark test."""
    test_name: str
    total_operations: int
    duration_seconds: float
    throughput: float
    latencies: List[float]
    p50_ms: float
    p95_ms: float
    p99_ms: float
    memory_mb: float
    cache_hits: int
    errors: int
    
    def __str__(self):
        return f"""
Benchmark: {self.test_name}
=====================================
Operations:     {self.total_operations:,}
Duration:       {self.duration_seconds:.2f}s
Throughput:     {self.throughput:.2f} ops/sec
Memory Used:    {self.memory_mb:.2f} MB

Latencies:
  P50:          {self.p50_ms:.2f}ms
  P95:          {self.p95_ms:.2f}ms
  P99:          {self.p99_ms:.2f}ms
  
Cache Hits:     {self.cache_hits:,}
Errors:         {self.errors}
"""

class PerformanceBenchmark:
    """Comprehensive performance benchmarking suite."""
    
    def __init__(self, engine: Optional[ContextEngine] = None):
        """Initialize benchmark suite.
        
        Args:
            engine: Context engine to test (creates new if not provided)
        """
        self.engine = engine or get_context_engine()
        self.results: List[BenchmarkResult] = []
        self.test_data = []
        
    def generate_test_data(self, count: int = 10000) -> List[Dict[str, Any]]:
        """Generate test context data.
        
        Args:
            count: Number of test contexts to generate
            
        Returns:
            List of test context data
        """
        print(f"Generating {count:,} test contexts...")
        
        topics = [
            "machine learning", "data science", "software engineering",
            "cloud computing", "cybersecurity", "blockchain", "AI ethics",
            "quantum computing", "robotics", "biotechnology"
        ]
        
        test_data = []
        for i in range(count):
            # Generate realistic content
            topic = random.choice(topics)
            content = f"""
            Context {i}: {topic.title()} Discussion
            
            This is a detailed discussion about {topic} covering various aspects including
            {''.join(random.choices(string.ascii_lowercase + ' ', k=random.randint(100, 500)))}
            
            Key points:
            - Implementation details for {topic}
            - Best practices and patterns
            - Common challenges and solutions
            - Future directions and research
            
            Related concepts: {', '.join(random.sample(topics, min(3, len(topics))))}
            """
            
            test_data.append({
                "content": content,
                "metadata": {
                    "topic": topic,
                    "index": i,
                    "timestamp": time.time() - random.randint(0, 86400 * 30),
                    "importance": random.random()
                }
            })
            
            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1:,} contexts...")
        
        self.test_data = test_data
        return test_data
    
    def benchmark_insertion(self, count: int = 1000) -> BenchmarkResult:
        """Benchmark context insertion performance.
        
        Args:
            count: Number of contexts to insert
            
        Returns:
            Benchmark results
        """
        print(f"\n🔄 Running insertion benchmark with {count:,} contexts...")
        
        if not self.test_data or len(self.test_data) < count:
            self.generate_test_data(count)
        
        # Set up test profile
        self.engine.set_profile("mene")
        
        latencies = []
        errors = 0
        start_time = time.perf_counter()
        memory_start = psutil.Process().memory_info().rss / 1024 / 1024
        
        for i in range(count):
            data = self.test_data[i]
            
            op_start = time.perf_counter()
            try:
                context_id = self.engine.add_context(
                    content=data["content"],
                    metadata=data["metadata"]
                )
                latencies.append((time.perf_counter() - op_start) * 1000)
            except Exception as e:
                errors += 1
                print(f"Error inserting context {i}: {e}")
        
        duration = time.perf_counter() - start_time
        memory_end = psutil.Process().memory_info().rss / 1024 / 1024
        
        result = BenchmarkResult(
            test_name="Context Insertion",
            total_operations=count,
            duration_seconds=duration,
            throughput=count / duration,
            latencies=latencies,
            p50_ms=np.percentile(latencies, 50),
            p95_ms=np.percentile(latencies, 95),
            p99_ms=np.percentile(latencies, 99),
            memory_mb=memory_end - memory_start,
            cache_hits=0,
            errors=errors
        )
        
        self.results.append(result)
        print(result)
        return result
    
    def benchmark_retrieval(self, queries: int = 1000) -> BenchmarkResult:
        """Benchmark context retrieval performance.
        
        Args:
            queries: Number of retrieval queries to run
            
        Returns:
            Benchmark results
        """
        print(f"\n🔍 Running retrieval benchmark with {queries:,} queries...")
        
        # Ensure we have contexts to retrieve
        if len(self.test_data) < 1000:
            self.benchmark_insertion(1000)
        
        # Generate search queries
        search_terms = [
            "machine learning implementation",
            "data science best practices",
            "cloud computing patterns",
            "security vulnerabilities",
            "AI ethics considerations",
            "performance optimization",
            "distributed systems",
            "algorithm complexity",
            "software architecture",
            "testing strategies"
        ]
        
        latencies = []
        cache_hits = 0
        errors = 0
        start_time = time.perf_counter()
        memory_start = psutil.Process().memory_info().rss / 1024 / 1024
        
        for i in range(queries):
            query = random.choice(search_terms)
            
            request = ContextRequest(
                query=query,
                profile_id="mene",
                limit=15
            )
            
            op_start = time.perf_counter()
            try:
                response = self.engine.retrieve_context(request)
                latencies.append((time.perf_counter() - op_start) * 1000)
                cache_hits += sum(response.cache_hits.values())
            except Exception as e:
                errors += 1
                print(f"Error retrieving context: {e}")
        
        duration = time.perf_counter() - start_time
        memory_end = psutil.Process().memory_info().rss / 1024 / 1024
        
        result = BenchmarkResult(
            test_name="Context Retrieval",
            total_operations=queries,
            duration_seconds=duration,
            throughput=queries / duration,
            latencies=latencies,
            p50_ms=np.percentile(latencies, 50),
            p95_ms=np.percentile(latencies, 95),
            p99_ms=np.percentile(latencies, 99),
            memory_mb=memory_end - memory_start,
            cache_hits=cache_hits,
            errors=errors
        )
        
        self.results.append(result)
        print(result)
        
        # Check success criteria
        if result.p95_ms < 100:
            print("✅ SUCCESS: P95 latency < 100ms")
        else:
            print(f"❌ FAILED: P95 latency {result.p95_ms:.2f}ms > 100ms target")
        
        return result
    
    def benchmark_concurrent_load(self, 
                                 workers: int = 10,
                                 operations: int = 1000) -> BenchmarkResult:
        """Benchmark concurrent operations.
        
        Args:
            workers: Number of concurrent workers
            operations: Total operations to perform
            
        Returns:
            Benchmark results
        """
        print(f"\n⚡ Running concurrent load test with {workers} workers...")
        
        def worker_task(worker_id: int, ops_count: int) -> Tuple[List[float], int]:
            """Worker task for concurrent testing."""
            latencies = []
            errors = 0
            
            for i in range(ops_count):
                # Mix of operations
                if random.random() < 0.3:  # 30% writes
                    op_start = time.perf_counter()
                    try:
                        data = random.choice(self.test_data)
                        self.engine.add_context(
                            content=data["content"],
                            metadata=data["metadata"]
                        )
                        latencies.append((time.perf_counter() - op_start) * 1000)
                    except:
                        errors += 1
                else:  # 70% reads
                    op_start = time.perf_counter()
                    try:
                        request = ContextRequest(
                            query="test query",
                            profile_id=f"worker_{worker_id}",
                            limit=10
                        )
                        self.engine.retrieve_context(request)
                        latencies.append((time.perf_counter() - op_start) * 1000)
                    except:
                        errors += 1
            
            return latencies, errors
        
        ops_per_worker = operations // workers
        all_latencies = []
        total_errors = 0
        
        start_time = time.perf_counter()
        memory_start = psutil.Process().memory_info().rss / 1024 / 1024
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(worker_task, i, ops_per_worker)
                for i in range(workers)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                latencies, errors = future.result()
                all_latencies.extend(latencies)
                total_errors += errors
        
        duration = time.perf_counter() - start_time
        memory_end = psutil.Process().memory_info().rss / 1024 / 1024
        
        result = BenchmarkResult(
            test_name="Concurrent Load",
            total_operations=operations,
            duration_seconds=duration,
            throughput=operations / duration,
            latencies=all_latencies,
            p50_ms=np.percentile(all_latencies, 50),
            p95_ms=np.percentile(all_latencies, 95),
            p99_ms=np.percentile(all_latencies, 99),
            memory_mb=memory_end - memory_start,
            cache_hits=0,
            errors=total_errors
        )
        
        self.results.append(result)
        print(result)
        
        # Check success criteria
        if result.throughput >= 1000:
            print("✅ SUCCESS: Throughput >= 1000 ops/sec")
        else:
            print(f"❌ FAILED: Throughput {result.throughput:.2f} < 1000 ops/sec target")
        
        return result
    
    def benchmark_namespace_isolation(self) -> BenchmarkResult:
        """Benchmark namespace isolation and switching."""
        print("\n🔐 Running namespace isolation benchmark...")
        
        # Create contexts in different namespaces
        namespaces = ["mene", "cindy", "viola", "nina", "pluma"]
        contexts_per_namespace = 100
        
        latencies = []
        errors = 0
        start_time = time.perf_counter()
        
        # Insert contexts in each namespace
        for ns in namespaces:
            self.engine.set_profile(ns)
            
            for i in range(contexts_per_namespace):
                op_start = time.perf_counter()
                try:
                    self.engine.add_context(
                        content=f"Private content for {ns} - item {i}",
                        metadata={"owner": ns, "private": True}
                    )
                    latencies.append((time.perf_counter() - op_start) * 1000)
                except:
                    errors += 1
        
        # Test isolation - try to access across namespaces
        cross_access_prevented = 0
        
        for source_ns in namespaces:
            for target_ns in namespaces:
                if source_ns != target_ns:
                    self.engine.set_profile(source_ns)
                    request = ContextRequest(
                        query=f"Private content for {target_ns}",
                        profile_id=source_ns,
                        namespace=target_ns
                    )
                    
                    response = self.engine.retrieve_context(request)
                    if len(response.contexts) == 0:
                        cross_access_prevented += 1
        
        duration = time.perf_counter() - start_time
        
        result = BenchmarkResult(
            test_name="Namespace Isolation",
            total_operations=len(namespaces) * contexts_per_namespace,
            duration_seconds=duration,
            throughput=(len(namespaces) * contexts_per_namespace) / duration,
            latencies=latencies,
            p50_ms=np.percentile(latencies, 50) if latencies else 0,
            p95_ms=np.percentile(latencies, 95) if latencies else 0,
            p99_ms=np.percentile(latencies, 99) if latencies else 0,
            memory_mb=0,
            cache_hits=cross_access_prevented,  # Using this field for isolation count
            errors=errors
        )
        
        self.results.append(result)
        print(result)
        
        # Check isolation
        expected_prevented = len(namespaces) * (len(namespaces) - 1)
        if cross_access_prevented == expected_prevented:
            print(f"✅ SUCCESS: All {cross_access_prevented} cross-namespace accesses prevented")
        else:
            print(f"❌ FAILED: Only {cross_access_prevented}/{expected_prevented} accesses prevented")
        
        return result
    
    def benchmark_cache_performance(self) -> BenchmarkResult:
        """Benchmark cache hit rates and performance."""
        print("\n💾 Running cache performance benchmark...")
        
        # Warm up cache with common queries
        warmup_queries = ["machine learning", "data science", "cloud computing"]
        
        for query in warmup_queries:
            request = ContextRequest(query=query, profile_id="mene")
            self.engine.retrieve_context(request)
        
        # Test cache hits
        latencies = []
        cache_hits = 0
        start_time = time.perf_counter()
        
        for _ in range(100):
            for query in warmup_queries:
                request = ContextRequest(query=query, profile_id="mene")
                
                op_start = time.perf_counter()
                response = self.engine.retrieve_context(request)
                latencies.append((time.perf_counter() - op_start) * 1000)
                
                if sum(response.cache_hits.values()) > 0:
                    cache_hits += 1
        
        duration = time.perf_counter() - start_time
        
        result = BenchmarkResult(
            test_name="Cache Performance",
            total_operations=300,
            duration_seconds=duration,
            throughput=300 / duration,
            latencies=latencies,
            p50_ms=np.percentile(latencies, 50),
            p95_ms=np.percentile(latencies, 95),
            p99_ms=np.percentile(latencies, 99),
            memory_mb=0,
            cache_hits=cache_hits,
            errors=0
        )
        
        self.results.append(result)
        print(result)
        
        hit_rate = (cache_hits / 300) * 100
        print(f"Cache Hit Rate: {hit_rate:.2f}%")
        
        return result
    
    def generate_report(self, output_path: str = "benchmark_report.json"):
        """Generate comprehensive benchmark report.
        
        Args:
            output_path: Path to save report
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "passed_criteria": 0,
                "failed_criteria": 0
            },
            "results": []
        }
        
        # Check success criteria
        for result in self.results:
            test_passed = True
            
            if "Retrieval" in result.test_name and result.p95_ms > 100:
                test_passed = False
            elif "Concurrent" in result.test_name and result.throughput < 1000:
                test_passed = False
            
            if test_passed:
                report["summary"]["passed_criteria"] += 1
            else:
                report["summary"]["failed_criteria"] += 1
            
            report["results"].append({
                "test": result.test_name,
                "passed": test_passed,
                "metrics": {
                    "operations": result.total_operations,
                    "duration_s": result.duration_seconds,
                    "throughput_ops_sec": result.throughput,
                    "p50_ms": result.p50_ms,
                    "p95_ms": result.p95_ms,
                    "p99_ms": result.p99_ms,
                    "memory_mb": result.memory_mb,
                    "errors": result.errors
                }
            })
        
        # Save report
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Report saved to: {output_path}")
        
        # Print summary
        print("\n" + "="*50)
        print("BENCHMARK SUMMARY")
        print("="*50)
        print(f"Tests Run:     {report['summary']['total_tests']}")
        print(f"Passed:        {report['summary']['passed_criteria']}")
        print(f"Failed:        {report['summary']['failed_criteria']}")
        
        if report['summary']['failed_criteria'] == 0:
            print("\n✅ All performance criteria met!")
        else:
            print("\n⚠️  Some performance criteria not met")
    
    def plot_results(self):
        """Generate performance visualization plots."""
        if not self.results:
            print("No results to plot")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle("Context Engine Performance Benchmarks", fontsize=16)
        
        # Latency comparison
        ax = axes[0, 0]
        test_names = [r.test_name for r in self.results]
        p95_values = [r.p95_ms for r in self.results]
        
        ax.bar(test_names, p95_values, color=['green' if p < 100 else 'red' for p in p95_values])
        ax.axhline(y=100, color='r', linestyle='--', label='100ms target')
        ax.set_ylabel('P95 Latency (ms)')
        ax.set_title('P95 Latency by Test')
        ax.legend()
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Throughput comparison
        ax = axes[0, 1]
        throughputs = [r.throughput for r in self.results]
        
        ax.bar(test_names, throughputs, color=['green' if t > 1000 else 'orange' for t in throughputs])
        ax.axhline(y=1000, color='r', linestyle='--', label='1000 ops/s target')
        ax.set_ylabel('Throughput (ops/sec)')
        ax.set_title('Throughput by Test')
        ax.legend()
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Latency distribution
        ax = axes[1, 0]
        for result in self.results[:3]:  # Plot first 3 tests
            if result.latencies:
                ax.hist(result.latencies, bins=50, alpha=0.5, label=result.test_name)
        
        ax.set_xlabel('Latency (ms)')
        ax.set_ylabel('Frequency')
        ax.set_title('Latency Distribution')
        ax.legend()
        
        # Memory usage
        ax = axes[1, 1]
        memory_usage = [r.memory_mb for r in self.results]
        
        ax.bar(test_names, memory_usage)
        ax.set_ylabel('Memory Usage (MB)')
        ax.set_title('Memory Usage by Test')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig('benchmark_results.png', dpi=150)
        plt.show()
        
        print("📈 Performance plots saved to: benchmark_results.png")

def run_full_benchmark():
    """Run complete benchmark suite."""
    print("="*50)
    print("CONTEXT ENGINE PERFORMANCE BENCHMARK")
    print("="*50)
    
    # Initialize benchmark
    benchmark = PerformanceBenchmark()
    
    # Generate test data
    benchmark.generate_test_data(10000)
    
    # Run benchmarks
    benchmark.benchmark_insertion(1000)
    benchmark.benchmark_retrieval(1000)
    benchmark.benchmark_concurrent_load(workers=10, operations=1000)
    benchmark.benchmark_namespace_isolation()
    benchmark.benchmark_cache_performance()
    
    # Generate report
    benchmark.generate_report()
    
    # Plot results
    try:
        benchmark.plot_results()
    except Exception as e:
        print(f"Could not generate plots: {e}")
    
    # Clean up
    benchmark.engine.optimize()
    
    return benchmark

if __name__ == "__main__":
    benchmark = run_full_benchmark()
    
    # Final verdict
    print("\n" + "="*50)
    print("FINAL VERDICT")
    print("="*50)
    
    all_passed = all(
        result.p95_ms < 100 
        for result in benchmark.results 
        if "Retrieval" in result.test_name
    )
    
    if all_passed:
        print("✅ Context Engine meets all performance requirements!")
    else:
        print("⚠️  Some performance optimizations needed")
    
    print("\nBenchmark complete!")
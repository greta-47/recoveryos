#!/usr/bin/env python3
"""
load_test.py - Performance impact assessment for Elite AI endpoints

This script performs load testing to ensure the new observability framework
doesn't degrade response times significantly.
"""

import asyncio
import aiohttp
import time
import statistics
import os
from typing import Dict, List, Any
import json


class LoadTester:
    """Load testing utility for RecoveryOS endpoints"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("TEST_BASE_URL", "http://localhost:8000")
        self.api_key = api_key or os.getenv("API_KEY", "test-key")
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        self.results = {}
    
    async def single_request(self, session: aiohttp.ClientSession, endpoint: str, method: str = "GET", data: dict = None) -> Dict[str, Any]:
        """Make a single request and measure response time"""
        start_time = time.time()
        try:
            if method == "GET":
                async with session.get(f"{self.base_url}{endpoint}", headers=self.headers) as response:
                    response_data = await response.json()
                    end_time = time.time()
                    return {
                        "status_code": response.status,
                        "response_time_ms": (end_time - start_time) * 1000,
                        "success": response.status == 200,
                        "data": response_data
                    }
            elif method == "POST":
                async with session.post(f"{self.base_url}{endpoint}", headers=self.headers, json=data) as response:
                    response_data = await response.json()
                    end_time = time.time()
                    return {
                        "status_code": response.status,
                        "response_time_ms": (end_time - start_time) * 1000,
                        "success": response.status == 200,
                        "data": response_data
                    }
        except Exception as e:
            end_time = time.time()
            return {
                "status_code": 0,
                "response_time_ms": (end_time - start_time) * 1000,
                "success": False,
                "error": str(e)
            }
    
    async def load_test_endpoint(self, endpoint: str, concurrent_requests: int = 10, total_requests: int = 100, method: str = "GET", data: dict = None) -> Dict[str, Any]:
        """Load test a specific endpoint"""
        print(f"🚀 Load testing {method} {endpoint} with {concurrent_requests} concurrent requests, {total_requests} total")
        
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def bounded_request():
                async with semaphore:
                    return await self.single_request(session, endpoint, method, data)
            
            tasks = [bounded_request() for _ in range(total_requests)]
            
            start_time = time.time()
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            response_times = [r["response_time_ms"] for r in results if r["success"]]
            success_count = sum(1 for r in results if r["success"])
            error_count = total_requests - success_count
            
            total_time = end_time - start_time
            requests_per_second = total_requests / total_time
            
            analysis = {
                "endpoint": endpoint,
                "method": method,
                "total_requests": total_requests,
                "concurrent_requests": concurrent_requests,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": success_count / total_requests,
                "total_time_seconds": total_time,
                "requests_per_second": requests_per_second,
                "response_times": {
                    "min_ms": min(response_times) if response_times else 0,
                    "max_ms": max(response_times) if response_times else 0,
                    "avg_ms": statistics.mean(response_times) if response_times else 0,
                    "median_ms": statistics.median(response_times) if response_times else 0,
                    "p95_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else (max(response_times) if response_times else 0),
                    "p99_ms": statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else (max(response_times) if response_times else 0)
                }
            }
            
            return analysis
    
    async def comprehensive_load_test(self) -> Dict[str, Any]:
        """Run comprehensive load tests on all elite endpoints"""
        print("🔥 Starting Comprehensive Load Test Suite")
        print("=" * 60)
        
        test_scenarios = [
            {"endpoint": "/healthz", "method": "GET", "concurrent": 5, "total": 50},
            {"endpoint": "/elite/health", "method": "GET", "concurrent": 5, "total": 50},
            {"endpoint": "/elite/metrics", "method": "GET", "concurrent": 10, "total": 100},
            {"endpoint": "/elite/federated/clients", "method": "GET", "concurrent": 5, "total": 50},
            {
                "endpoint": "/elite/federated/register", 
                "method": "POST", 
                "concurrent": 3, 
                "total": 15,
                "data": {
                    "client_id": "load_test_client",
                    "client_type": "clinic",
                    "privacy_level": "standard"
                }
            },
            {"endpoint": "/elite/metrics", "method": "GET", "concurrent": 20, "total": 200},
            {"endpoint": "/elite/health", "method": "GET", "concurrent": 15, "total": 150},
        ]
        
        all_results = {}
        
        for scenario in test_scenarios:
            endpoint = scenario["endpoint"]
            method = scenario["method"]
            concurrent = scenario["concurrent"]
            total = scenario["total"]
            data = scenario.get("data")
            
            result = await self.load_test_endpoint(endpoint, concurrent, total, method, data)
            test_key = f"{method}_{endpoint.replace('/', '_')}_c{concurrent}_t{total}"
            all_results[test_key] = result
            
            print(f"✅ {method} {endpoint}")
            print(f"   Success Rate: {result['success_rate']:.2%}")
            print(f"   Avg Response: {result['response_times']['avg_ms']:.2f}ms")
            print(f"   P95 Response: {result['response_times']['p95_ms']:.2f}ms")
            print(f"   RPS: {result['requests_per_second']:.2f}")
            print()
        
        return all_results
    
    def analyze_performance_impact(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance impact of elite endpoints vs basic endpoints"""
        basic_healthz = None
        elite_health = None
        elite_metrics = None
        
        for key, result in results.items():
            if "healthz" in key and "c5_t50" in key:
                basic_healthz = result
            elif "elite_health" in key and "c5_t50" in key:
                elite_health = result
            elif "elite_metrics" in key and "c10_t100" in key:
                elite_metrics = result
        
        analysis = {
            "baseline_performance": basic_healthz["response_times"] if basic_healthz else None,
            "elite_health_performance": elite_health["response_times"] if elite_health else None,
            "elite_metrics_performance": elite_metrics["response_times"] if elite_metrics else None,
        }
        
        if basic_healthz and elite_health:
            overhead_ms = elite_health["response_times"]["avg_ms"] - basic_healthz["response_times"]["avg_ms"]
            overhead_percent = (overhead_ms / basic_healthz["response_times"]["avg_ms"]) * 100
            analysis["elite_health_overhead"] = {
                "overhead_ms": overhead_ms,
                "overhead_percent": overhead_percent,
                "acceptable": overhead_percent < 50
            }
        
        return analysis
    
    def generate_report(self, results: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate a comprehensive performance report"""
        report = []
        report.append("# RecoveryOS Elite Endpoints - Performance Impact Assessment")
        report.append("=" * 60)
        report.append("")
        
        report.append("## Executive Summary")
        if analysis.get("elite_health_overhead"):
            overhead = analysis["elite_health_overhead"]
            if overhead["acceptable"]:
                report.append(f"✅ **PASS**: Elite endpoints add {overhead['overhead_ms']:.2f}ms ({overhead['overhead_percent']:.1f}%) overhead - within acceptable limits")
            else:
                report.append(f"❌ **FAIL**: Elite endpoints add {overhead['overhead_ms']:.2f}ms ({overhead['overhead_percent']:.1f}%) overhead - exceeds acceptable limits")
        
        report.append("")
        report.append("## Detailed Results")
        report.append("")
        
        for test_key, result in results.items():
            report.append(f"### {test_key}")
            report.append(f"- **Endpoint**: {result['method']} {result['endpoint']}")
            report.append(f"- **Success Rate**: {result['success_rate']:.2%}")
            report.append(f"- **Requests/Second**: {result['requests_per_second']:.2f}")
            report.append(f"- **Average Response Time**: {result['response_times']['avg_ms']:.2f}ms")
            report.append(f"- **P95 Response Time**: {result['response_times']['p95_ms']:.2f}ms")
            report.append(f"- **P99 Response Time**: {result['response_times']['p99_ms']:.2f}ms")
            report.append("")
        
        report.append("## Performance Thresholds")
        report.append("- ✅ Average response time < 500ms")
        report.append("- ✅ P95 response time < 1000ms") 
        report.append("- ✅ Success rate > 99%")
        report.append("- ✅ Elite endpoint overhead < 50%")
        report.append("")
        
        report.append("## Threshold Analysis")
        for test_key, result in results.items():
            endpoint = result['endpoint']
            avg_ms = result['response_times']['avg_ms']
            p95_ms = result['response_times']['p95_ms']
            success_rate = result['success_rate']
            
            status = "✅" if avg_ms < 500 and p95_ms < 1000 and success_rate > 0.99 else "❌"
            report.append(f"{status} {endpoint}: {avg_ms:.1f}ms avg, {p95_ms:.1f}ms p95, {success_rate:.2%} success")
        
        return "\n".join(report)


async def main():
    """Run the load test suite"""
    tester = LoadTester()
    
    try:
        results = await tester.comprehensive_load_test()
        analysis = tester.analyze_performance_impact(results)
        report = tester.generate_report(results, analysis)
        
        print("📊 PERFORMANCE REPORT")
        print("=" * 60)
        print(report)
        
        with open("load_test_results.json", "w") as f:
            json.dump({
                "results": results,
                "analysis": analysis,
                "timestamp": time.time()
            }, f, indent=2)
        
        print("\n💾 Results saved to load_test_results.json")
        
        if analysis.get("elite_health_overhead", {}).get("acceptable", True):
            print("\n🎉 All performance tests passed!")
            return 0
        else:
            print("\n❌ Performance tests failed - elite endpoints exceed acceptable overhead")
            return 1
            
    except Exception as e:
        print(f"❌ Load test failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

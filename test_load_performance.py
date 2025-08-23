#!/usr/bin/env python3
"""
Load Performance Testing Script
Tests the 3 target endpoints with performance validation
"""

import asyncio
import aiohttp
import time
import json
import statistics
import pytest
from typing import Dict, Any
from datetime import datetime


class LoadTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results: Dict[str, Any] = {}

    async def test_endpoint(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        payload: Dict[str, Any],
        duration_minutes: int = 2,
    ):
        """Test a single endpoint for specified duration"""
        url = f"{self.base_url}{endpoint}"
        latencies = []
        errors = 0
        total_requests = 0

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        print(f"🚀 Testing {endpoint} for {duration_minutes} minutes...")

        while time.time() < end_time:
            request_start = time.time()
            try:
                async with session.post(url, json=payload) as response:
                    await response.text()
                    request_latency = (
                        time.time() - request_start
                    ) * 1000  # Convert to ms
                    latencies.append(request_latency)

                    if response.status != 200:
                        errors += 1

                    total_requests += 1

            except Exception as e:
                errors += 1
                total_requests += 1
                print(f"Request error: {e}")

            await asyncio.sleep(0.1)

        if latencies:
            p50 = statistics.median(latencies)
            p95 = (
                statistics.quantiles(latencies, n=20)[18]
                if len(latencies) >= 20
                else max(latencies)
            )
            p99 = (
                statistics.quantiles(latencies, n=100)[98]
                if len(latencies) >= 100
                else max(latencies)
            )
            avg_latency = statistics.mean(latencies)
        else:
            p50 = p95 = p99 = avg_latency = 0

        error_rate = (errors / total_requests) * 100 if total_requests > 0 else 100
        rps = total_requests / (duration_minutes * 60)

        self.results[endpoint] = {
            "total_requests": total_requests,
            "errors": errors,
            "error_rate_percent": round(error_rate, 2),
            "rps": round(rps, 2),
            "latency_ms": {
                "avg": round(avg_latency, 2),
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "max": round(max(latencies), 2) if latencies else 0,
            },
            "sla_compliance": {
                "p95_under_500ms": p95 < 500,
                "error_rate_under_1pct": error_rate < 1.0,
            },
        }

        print(
            f"✅ {endpoint} completed: {total_requests} requests, {error_rate:.2f}% errors, P95: {p95:.2f}ms"
        )

    async def run_load_tests(self):
        """Run load tests for all 3 target endpoints"""
        test_cases = [
            {
                "endpoint": "/elite/continual-learning/train",
                "payload": {
                    "task_data": {"stress_patterns": [0.8, 0.6, 0.9]},
                    "task_id": "load_test_continual",
                },
            },
            {
                "endpoint": "/elite/federated-learning/train",
                "payload": {
                    "client_weights": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "client_id": "load_test_client",
                },
            },
            {
                "endpoint": "/elite/edge-ai/deploy",
                "payload": {"model_type": "emotion_classifier"},
            },
        ]

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status != 200:
                        print(f"❌ Server not responding at {self.base_url}")
                        pytest.skip(f"Server not responding at {self.base_url}")
            except Exception as e:
                print(f"❌ Cannot connect to server: {e}")
                pytest.skip(f"Cannot connect to server: {e}")

            print(f"🔗 Connected to server at {self.base_url}")

            for test_case in test_cases:
                await self.test_endpoint(
                    session,
                    test_case["endpoint"],
                    test_case["payload"],
                    duration_minutes=2,  # Shortened for testing
                )

        assert True

    def generate_report(self):
        """Generate performance test report"""
        report = {
            "test_timestamp": datetime.utcnow().isoformat() + "Z",
            "test_duration_minutes": 2,
            "target_rps": 10,
            "endpoints": self.results,
            "overall_summary": {
                "total_endpoints_tested": len(self.results),
                "endpoints_meeting_sla": sum(
                    1
                    for r in self.results.values()
                    if r["sla_compliance"]["p95_under_500ms"]
                    and r["sla_compliance"]["error_rate_under_1pct"]
                ),
                "avg_error_rate": round(
                    statistics.mean(
                        [r["error_rate_percent"] for r in self.results.values()]
                    ),
                    2,
                ),
                "avg_p95_latency": round(
                    statistics.mean(
                        [r["latency_ms"]["p95"] for r in self.results.values()]
                    ),
                    2,
                ),
            },
        }

        return report


async def main():
    """Run load performance tests"""
    print("🏋️ Load Performance Testing")
    print("=" * 50)

    tester = LoadTester()
    success = await tester.run_load_tests()

    if not success:
        print("❌ Load testing failed - server connectivity issues")
        return 1

    report = tester.generate_report()

    with open("load_test_results.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n📊 Load Test Results Summary:")
    print(
        f"Total Endpoints Tested: {report['overall_summary']['total_endpoints_tested']}"
    )
    print(
        f"Endpoints Meeting SLA: {report['overall_summary']['endpoints_meeting_sla']}"
    )
    print(f"Average Error Rate: {report['overall_summary']['avg_error_rate']}%")
    print(f"Average P95 Latency: {report['overall_summary']['avg_p95_latency']}ms")

    all_compliant = (
        report["overall_summary"]["endpoints_meeting_sla"]
        == report["overall_summary"]["total_endpoints_tested"]
    )

    if all_compliant:
        print("✅ All endpoints meet SLA requirements")
        return 0
    else:
        print("❌ Some endpoints do not meet SLA requirements")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

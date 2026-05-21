#!/usr/bin/env python3
"""
Cross-Platform Test Runner for Coordinate Transformation

Runs test vectors from test_vectors.json against the Python implementation.
C# implementation should run the same tests in Unity.
"""

import json
import sys
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.transform.transform_core import (
    CoordinateTransformer, ScaleMode, Bounds
)


def load_test_vectors():
    """Load test vectors from JSON file."""
    test_file = Path(__file__).parent / "test_vectors.json"
    with open(test_file, 'r') as f:
        return json.load(f)


def run_test_suite(suite: dict, tolerance: float = 0.01) -> dict:
    """Run a test suite and return results."""
    config = suite["config"]
    bounds = Bounds.from_dict(config["bounds"])
    
    # Determine scale mode (simplified - default to FIT_CONTAIN)
    mode = ScaleMode.FIT_CONTAIN
    
    # Note: test vectors use normalized output (0-1) not SiteOwl (0-100)
    # We need to adjust our transformer or the expected values
    transformer = CoordinateTransformer(
        mode=mode,
        artboard_size=1000,
        floorplan_size=1000,  # Use full artboard for these tests
        flip_y=config.get("flip_y", True),
        rotation_deg=config.get("rotation_deg", 0)
    )
    transformer.set_bounds(bounds)
    
    results = {
        "suite": suite["suite"],
        "passed": 0,
        "failed": 0,
        "errors": [],
        "details": []
    }
    
    for case in suite["cases"]:
        case_id = case["id"]
        input_pt = case["input"]
        expected = case["expected"]
        
        try:
            # Transform
            result = transformer.transform(input_pt["x"], input_pt["y"])
            
            # Normalize to 0-1 range for comparison with test vectors
            actual_x = result.site_x / 100.0
            actual_y = result.site_y / 100.0
            
            # Check within tolerance
            x_ok = abs(actual_x - expected["x"]) <= tolerance
            y_ok = abs(actual_y - expected["y"]) <= tolerance
            
            if x_ok and y_ok:
                results["passed"] += 1
                status = "PASS"
            else:
                results["failed"] += 1
                status = "FAIL"
                results["errors"].append({
                    "case": case_id,
                    "expected": expected,
                    "actual": {"x": actual_x, "y": actual_y}
                })
            
            results["details"].append({
                "case": case_id,
                "status": status,
                "input": input_pt,
                "expected": expected,
                "actual": {"x": round(actual_x, 4), "y": round(actual_y, 4)}
            })
            
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "case": case_id,
                "error": str(e)
            })
    
    return results


def run_all_tests():
    """Run all test suites."""
    print("=" * 60)
    print("Cross-Platform Transform Test Runner (Python)")
    print("=" * 60)
    
    vectors = load_test_vectors()
    tolerance = vectors["metadata"]["tolerance"]
    
    print(f"Test vectors version: {vectors['metadata']['version']}")
    print(f"Tolerance: {tolerance}")
    print()
    
    total_passed = 0
    total_failed = 0
    
    for suite in vectors["test_suites"]:
        print(f"--- Suite: {suite['suite']} ---")
        print(f"    {suite['description']}")
        
        # Skip suites that need special handling
        if suite["suite"] == "inverse_transform":
            print("    [SKIP] Inverse transform tests need separate handling")
            continue
        
        results = run_test_suite(suite, tolerance)
        
        total_passed += results["passed"]
        total_failed += results["failed"]
        
        for detail in results["details"]:
            status_icon = "[OK]" if detail["status"] == "PASS" else "[FAIL]"
            print(f"    {status_icon} {detail['case']}: {detail['input']} -> {detail['actual']}")
        
        if results["errors"]:
            for err in results["errors"]:
                print(f"    [ERR] {err}")
        
        print()
    
    # Summary
    print("=" * 60)
    print(f"SUMMARY: {total_passed} passed, {total_failed} failed")
    print("=" * 60)
    
    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

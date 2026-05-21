# Cross-Platform Test Harness

## Purpose

Ensure Python and C# implementations produce **identical results** for all coordinate transformations.

## Test Vector Format

`test_vectors.json` contains standardized test cases:

```json
{
  "suite": "suite_name",
  "config": { /* transformation config */ },
  "cases": [
    {
      "id": "unique_id",
      "description": "what this tests",
      "input": { "x": 0, "y": 0 },
      "expected": { "x": 0.5, "y": 0.5 }
    }
  ]
}
```

## Tolerance

**0.001** (0.1% of normalized range)

This means:
- Expected `x: 0.500` passes if actual is `0.499` to `0.501`
- For a 100ft floor, that's ±0.1ft or ±1.2 inches

## Running Tests

### Python
```bash
cd CadOwl
python -m pytest shared/tests/test_transform.py -v
```

### C# (Unity)
```bash
# From Unity project
dotnet test Tests/TestTransform.cs
```

### Cross-Validation Script
```bash
# Compare outputs from both implementations
python shared/tests/cross_validate.py
```

## Adding Test Cases

1. Add case to `test_vectors.json`
2. Run Python tests - should fail
3. Implement feature
4. Run Python tests - should pass
5. Run C# tests - should pass
6. Commit

## Coverage Goals

| Feature | Test Suite |
|---------|------------|
| Basic normalization | `basic_transform` |
| Non-zero origin | `with_offset` |
| Rotation | `with_rotation` |
| VIVE coordinates | `vive_transform` |
| Inverse transform | `inverse_transform` |
| Edge cases | `edge_cases` |
| Calibration | `calibration` (TBD) |

## CI Integration

Both test suites should run in CI:
- Python tests in Python job
- C# tests in Unity job
- Cross-validation as integration test

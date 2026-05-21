# 🧠 ForgeSight AutoDesign

> **ML Design Recommendation Engine**

AI-powered design assistance using Element AI for intelligent recommendations, anomaly detection, and optimization.

---

## Overview

ForgeSight AutoDesign brings machine learning to security design:

- **Design Recommendations** — Suggest optimal device placement
- **Anomaly Detection** — Flag unusual patterns
- **Cost Optimization** — Balance coverage vs. budget
- **Compliance Checking** — Validate against standards
- **Natural Language** — Query designs conversationally

---

## Status: 🔴 Alpha

ForgeSight AutoDesign is in early development. Features may change.

---

## Features

### 💡 Design Recommendations

```python
from forgesight.autodesign import DesignAdvisor

advisor = DesignAdvisor()

# Get recommendations for a floor plan
recommendations = advisor.recommend(
    floor_plan=floor_plan,
    existing_devices=devices,
    design_type="cctv",
    constraints={
        "max_devices": 50,
        "min_coverage": 95,
        "budget": 75000
    }
)

for rec in recommendations:
    print(f"Add {rec.device_type} at ({rec.x}, {rec.y})")
    print(f"  Reason: {rec.explanation}")
    print(f"  Coverage gain: +{rec.coverage_delta}%")
    print(f"  Cost: ${rec.estimated_cost}")
```

### 🔍 Anomaly Detection

```python
from forgesight.autodesign import AnomalyDetector

detector = AnomalyDetector()

anomalies = detector.analyze(design)

for anomaly in anomalies:
    print(f"⚠️ {anomaly.severity}: {anomaly.description}")
    print(f"   Location: ({anomaly.x}, {anomaly.y})")
    print(f"   Suggestion: {anomaly.suggestion}")
```

**Detected Anomalies:**
- Overlapping coverage (redundant cameras)
- Blind spots > threshold
- Unusual device spacing
- Missing standard locations (entrances, registers)
- Device type mismatches

### 💰 Cost Optimization

```python
from forgesight.autodesign import CostOptimizer

optimizer = CostOptimizer()

# Find cheapest design meeting requirements
result = optimizer.optimize(
    floor_plan=floor_plan,
    requirements={
        "min_coverage": 95,
        "required_zones": ["entrance", "registers", "pharmacy"]
    },
    device_catalog=catalog
)

print(f"Optimal design: {len(result.devices)} devices")
print(f"Total cost: ${result.total_cost}")
print(f"Coverage: {result.coverage}%")
```

### ✅ Compliance Checking

```python
from forgesight.autodesign import ComplianceChecker

checker = ComplianceChecker(standard="walmart_security_v2")

report = checker.check(design)

print(f"Compliance: {report.score}%")
for violation in report.violations:
    print(f"❌ {violation.rule}: {violation.description}")
for warning in report.warnings:
    print(f"⚠️ {warning.rule}: {warning.description}")
```

### 💬 Natural Language Queries

```python
from forgesight.autodesign import DesignAssistant

assistant = DesignAssistant()

# Ask questions about designs
response = assistant.query(
    design=design,
    question="Why are there so many cameras in the grocery section?"
)
print(response.answer)
# "The grocery section has 12 cameras because it's a high-shrink area 
#  with multiple aisles requiring overlapping coverage..."

# Get suggestions
response = assistant.query(
    design=design,
    question="How can I reduce costs without losing coverage?"
)
print(response.suggestions)
```

---

## Element AI Integration

ForgeSight AutoDesign uses [Element AI](https://gecgithub01.walmart.com/pages/MLPlatforms/elementGenAI/) for ML capabilities.

### Configuration

```bash
# .env
ELEMENT_API_URL=https://element.walmart.com/api/v1
ELEMENT_API_KEY=your-api-key
ELEMENT_MODEL=gpt-4-turbo
```

### Pydantic AI Integration

```python
from pydantic_ai import Agent
from forgesight.autodesign.prompts import DESIGN_REVIEW_PROMPT

agent = Agent(
    model="element:gpt-4-turbo",
    system_prompt=DESIGN_REVIEW_PROMPT
)

result = await agent.run(
    f"Review this security design: {design.to_json()}"
)
```

---

## API Endpoints

### Get Recommendations

```http
POST /api/v1/autodesign/recommend
Content-Type: application/json

{
  "floor_plan_id": "uuid",
  "design_type": "cctv",
  "constraints": {
    "max_devices": 50,
    "min_coverage": 95
  }
}
```

### Check Anomalies

```http
POST /api/v1/autodesign/anomalies
Content-Type: application/json

{
  "design_id": "uuid"
}
```

### Natural Language Query

```http
POST /api/v1/autodesign/query
Content-Type: application/json

{
  "design_id": "uuid",
  "question": "How can I improve coverage in the back room?"
}
```

---

## Training Data

AutoDesign learns from:

- 10,000+ historical designs
- Expert review feedback
- Coverage analysis results
- Installation outcomes

### Contributing Training Data

```python
from forgesight.autodesign import TrainingData

# Submit expert feedback
TrainingData.submit_feedback(
    design_id="uuid",
    feedback_type="recommendation_used",
    recommendation_id="rec-123",
    outcome="improved_coverage"
)
```

---

## Roadmap

| Feature | Status | ETA |
|:--------|:-------|:----|
| Basic recommendations | 🔴 Alpha | Q2 2026 |
| Anomaly detection | 🔴 Alpha | Q2 2026 |
| Cost optimization | 🟡 Planned | Q3 2026 |
| Compliance checking | 🟡 Planned | Q3 2026 |
| NL queries | 🟡 Planned | Q4 2026 |

---

## Related

- [ForgeSight Vision](ForgeSight-Vision.md) — Coverage analysis
- [ForgeSight CAD](ForgeSight-CAD.md) — Design extraction
- [Element AI Docs](https://gecgithub01.walmart.com/pages/MLPlatforms/elementGenAI/)

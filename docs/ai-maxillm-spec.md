# MAXILLM Intelligence Spec

## Role
MAXILLM is a design review and recommendation system, not an unchecked mutation engine.

## Core Functions
- Review imports and validation failures
- Review design topology and coordinates
- Suggest fixes with confidence + rationale
- Draft safe recommendations for approval

## Guardrails
- Direct production mutation disabled by default
- Dangerous actions require approval artifact
- Every suggestion must include evidence references

## Inputs
- Project data
- Validation results
- Import reports
- Rules and standards corpus
- Historical approved corrections

## Outputs
- QA findings
- Ranked suggestions
- Confidence scores
- Executive summary

## Audit
All AI requests/responses must be event logged with model metadata.

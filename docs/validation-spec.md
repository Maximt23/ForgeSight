# Validation & Self-Healing Spec

## Severity
- Critical
- High
- Medium
- Low
- Info

## Categories
- Schema
- Required fields
- Coordinate
- Device
- Cable
- Zone
- Duplicate
- Import
- Export

## Validation Result Contract
- `severity`
- `category`
- `field`
- `record_id`
- `message`
- `technical_reason`
- `suggested_fix`
- `autofix_eligible`
- `confidence_score`
- `source_evidence`

## Safe Auto-Fixes (No Approval)
- Casing normalization
- Known manufacturer normalization
- Alias mapping for column names
- Status normalization

## Approval Required
- DORIS change
- Device move/delete/merge
- Cable change
- Final export mutation

# DORIS Intelligence Spec

## Objective
Represent DORIS identifiers and rules as first-class domain intelligence.

## Capabilities
- DORIS lookup and normalization
- Device-type compatibility checks
- Rule-driven recommendations
- Assignment validation

## Data Requirements
- DORIS catalog
- Device compatibility matrix
- Rule precedence model
- Change history

## API Concepts
- `POST /api/v1/doris/validate`
- `POST /api/v1/doris/recommend`
- `GET /api/v1/doris/catalog`

## Safety
DORIS reassignment is approval-required and must include an audit event.

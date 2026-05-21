# Import Spec

## Import Batch Lifecycle
1. Uploaded
2. Fingerprinted
3. Parsed
4. Mapped
5. Validated
6. Previewed
7. Approved
8. Committed
9. Reported

## Required Metadata
- `import_batch_id`
- `source_file_name`
- `source_file_hash`
- `performed_by`
- `created_at`

## Validation Buckets
- Valid
- Warning
- Failed (quarantine)

## Commit Rule
Only valid rows are committed. Warnings require explicit user approval mode. Failed rows never commit.

## Rollback Rule
Every commit creates rollback checkpoint and event references.

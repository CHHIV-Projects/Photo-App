# Cross-Operation Guardrail Enforcement 12.62.5 (Implementation Closeout)

## 1. Purpose
Enforce a shared cross-operation ingestion guardrail at start time and align readiness conflict visibility with the same backend helper.

## 2. Implemented Scope
Implemented:

1. Added shared read-only guardrail snapshot service in backend/app/services/admin/ingestion_operation_guardrail_service.py.
2. Applied guardrail-first checks to:
  - POST /api/admin/icloud-acquisition/run
  - POST /api/admin/source-intake/run
  - POST /api/admin/icloud-staging-cleanup/run
3. Reused shared guardrail helper in readiness:
  - backend/app/services/admin/icloud_readiness_service.py now derives operation_conflicts and active-operation blocking reasons from the same helper.
4. Added tests for helper and API payload behavior.

Not changed (hard boundaries preserved):

1. stop/status behavior
2. iCloud launch from Ingestion UI
3. iCloud Source Intake handoff logic
4. cleanup launch from Ingestion UI
5. credentials/session behavior
6. path repair or source-registration mutation flows

## 3. Shared Guardrail Behavior
Policy enforced:

1. Only one ingestion-related operation may be active at a time.
2. Active operations considered:
  - iCloud acquisition
  - Source Intake
  - iCloud staging cleanup
3. If any of the above is active, starts for the others are blocked with HTTP 409.

Guardrail snapshot includes:

1. operation_conflicts flags
2. source-specific flags (nullable when source context is unknown)
3. blocking_reasons (code + message)
4. active_operation and active_source_id metadata for service consumers

## 4. Conflict Payload Behavior
iCloud acquisition start:

1. Guardrail conflict returns HTTP 409 with:
  - error_code = INGESTION_OPERATION_ACTIVE
  - blocking_reasons
  - operation_conflicts
2. Non-conflict launch errors remain HTTP 400.

Source Intake start:

1. Guardrail conflict returns HTTP 409 with additive compatibility payload:
  - detail
  - error_code = INGESTION_OPERATION_ACTIVE
  - current (existing compatibility field retained)
  - blocking_reasons
  - operation_conflicts

iCloud cleanup start:

1. Guardrail conflict returns HTTP 409.
2. Preserves endpoint-specific error code behavior where applicable:
  - CLEANUP_ALREADY_RUNNING when cleanup is active
  - SOURCE_INTAKE_ACTIVE when active Source Intake is for the same source
3. Uses INGESTION_OPERATION_ACTIVE for other cross-operation guardrail conflicts.
4. Includes blocking_reasons and operation_conflicts.

## 5. No Run-Row Creation for Guardrail Blocks
Guardrail checks run before operation launch calls. Blocked starts return 409 and do not create new run rows.

## 6. Files Changed
1. backend/app/services/admin/ingestion_operation_guardrail_service.py (new)
2. backend/app/services/admin/icloud_readiness_service.py
3. backend/app/api/admin.py
4. backend/tests/test_ingestion_operation_guardrail_service.py (new)
5. backend/tests/test_admin_ingestion_guardrails_api.py (new)
6. backend/tests/test_icloud_readiness_service.py
7. backend/tests/test_icloud_acquisition_service.py

## 7. Validation
Passed:

1. backend/tests/test_ingestion_operation_guardrail_service.py
2. backend/tests/test_admin_ingestion_guardrails_api.py
3. backend/tests/test_icloud_readiness_service.py
4. backend/tests/test_icloud_acquisition_service.py

## 8. Compatibility Notes
1. Source Intake conflict payload keeps current field and adds guardrail fields.
2. Cleanup keeps existing endpoint-specific conflict codes where they already apply.
3. Readiness conflict state and start-time enforcement now share one helper to reduce drift risk.

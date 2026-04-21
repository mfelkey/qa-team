---
QA VERDICT: FAIL  
BLOCKING ISSUES: 4  
NON-BLOCKING ISSUES: 3  
SIGN-OFF STATUS: DO NOT SHIP  
---

### **1. StatsBomb xG ingestion pipeline (ds/pipelines/01_ingest_statsbomb.py)**

#### **Issue QA-001**  
- **Severity:** CRITICAL  
- **Category:** data  
- **Description:** The pipeline does not implement idempotency checks, meaning re-running the pipeline on the same data may result in duplicate rows in the sb_shots and sb_matches tables.  
- **Expected vs Actual:** Expected: Pipeline should be idempotent and prevent duplicate inserts. Actual: No checks for existing records before insert.  
- **Remediation:** Add unique constraints or upsert logic (e.g., `ON CONFLICT DO NOTHING` in PostgreSQL) to prevent duplicate data.  
- **Blocking:** YES  

#### **Issue QA-002**  
- **Severity:** CRITICAL  
- **Category:** data  
- **Description:** The pipeline lacks error handling for malformed or missing StatsBomb JSON data, which may cause pipeline failures or data loss.  
- **Expected vs Actual:** Expected: Pipeline should gracefully handle malformed data and log errors. Actual: No error handling for JSON parsing or missing fields.  
- **Remediation:** Implement try-except blocks around data parsing and add error logging with retry mechanisms or data quarantine.  
- **Blocking:** YES  

#### **Issue QA-003**  
- **Severity:** CRITICAL  
- **Category:** data  
- **Description:** Schema design does not enforce data integrity constraints (e.g., foreign keys, NOT NULL, unique constraints).  
- **Expected vs Actual:** Expected: Schema should enforce data integrity. Actual: No schema-level constraints for referential integrity or required fields.  
- **Remediation:** Add NOT NULL, UNIQUE, and FOREIGN KEY constraints to the schema.  
- **Blocking:** YES  

#### **Issue QA-004**  
- **Severity:** HIGH  
- **Category:** data  
- **Description:** No test coverage for the pipeline logic, making it difficult to validate correctness or detect regressions.  
- **Expected vs Actual:** Expected: Unit and integration tests covering pipeline logic. Actual: No test files or test suite for this pipeline.  
- **Remediation:** Write unit tests for parsing logic, integration tests for data ingestion, and include in CI pipeline.  
- **Blocking:** NO  

#### **Issue QA-005**  
- **Severity:** MEDIUM  
- **Category:** performance  
- **Description:** Pipeline uses inefficient bulk inserts instead of batched operations, which may lead to performance degradation at scale.  
- **Expected vs Actual:** Expected: Use `executemany()` or `COPY` for bulk inserts. Actual: Individual `INSERT` statements used.  
- **Remediation:** Replace individual inserts with `executemany()` or `COPY` for better performance.  
- **Blocking:** NO  

#### **Issue QA-006**  
- **Severity:** MEDIUM  
- **Category:** security  
- **Description:** Pipeline accesses StatsBomb API without rate-limiting or retry logic, increasing risk of API throttling or failure.  
- **Expected vs Actual:** Expected: Implement exponential backoff and rate-limiting. Actual: No retry or throttling logic.  
- **Remediation:** Add retry logic with exponential backoff using `tenacity` or similar library.  
- **Blocking:** NO  

#### **Issue QA-007**  
- **Severity:** LOW  
- **Category:** data  
- **Description:** No logging of pipeline execution status or progress for debugging or monitoring.  
- **Expected vs Actual:** Expected: Logs should be present at key steps (start, finish, errors). Actual: Minimal or no logging.  
- **Remediation:** Add structured logging with levels (INFO, ERROR) at key stages of pipeline execution.  
- **Blocking:** NO  

---

### **2. Project Instructions update (2026-03-30)**

#### **Issue QA-008**  
- **Severity:** HIGH  
- **Category:** compliance  
- **Description:** The update does not explicitly mention the need for accessibility review in the hybrid workflow, which is required for legal compliance.  
- **Expected vs Actual:** Expected: Accessibility review process should be included in workflow documentation. Actual: No mention of accessibility checks or WCAG compliance in the update.  
- **Remediation:** Add a section to the workflow doc requiring WCAG AA compliance checks and accessibility reviews before code merge.  
- **Blocking:** NO  

#### **Issue QA-009**  
- **Severity:** MEDIUM  
- **Category:** compliance  
- **Description:** The update does not specify how code reviews will enforce TDD and coding standards in a distributed team environment.  
- **Expected vs Actual:** Expected: Clear guidance on how TDD and standards are enforced during peer review. Actual: No such guidance provided.  
- **Remediation:** Add a code review checklist that includes TDD verification and adherence to coding standards.  
- **Blocking:** NO  

---

### **3. PDB-02 and PDB-03 decisions**

#### **Issue QA-010**  
- **Severity:** HIGH  
- **Category:** data  
- **Description:** The decision to accept StatsBomb Open Data as the xG source lacks risk assessment for data quality or consistency over time.  
- **Expected vs Actual:** Expected: Risk assessment and data validation criteria should be documented. Actual: No such documentation provided.  
- **Remediation:** Add a data quality review checklist for StatsBomb Open Data, including consistency checks and validation against known benchmarks.  
- **Blocking:** NO  

#### **Issue QA-011**  
- **Severity:** HIGH  
- **Category:** data  
- **Description:** API-Football is used as a UCL xG source without verifying data freshness or reliability of the API endpoint.  
- **Expected vs Actual:** Expected: API reliability and data freshness should be verified before decision. Actual: No such verification documented.  
- **Remediation:** Conduct API health check and data freshness test for API-Football before use.  
- **Blocking:** NO  

---

### **4. LESSONS_LEARNED.md entry LL-012**

#### **Issue QA-012**  
- **Severity:** MEDIUM  
- **Category:** compliance  
- **Description:** The entry LL-012 correctly identifies the psycopg2 DDL transaction ordering bug but lacks a detailed fix plan or code example.  
- **Expected vs Actual:** Expected: A fix plan or code snippet should be included. Actual: Only the bug is described, no remediation guidance.  
- **Remediation:** Add a code example showing correct transaction ordering for DDL operations in psycopg2.  
- **Blocking:** NO  

---

### **RECOMMENDATIONS**

- **DS Team:** Implement schema constraints, idempotency, and error handling for the StatsBomb pipeline.  
- **Dev Team:** Add unit and integration tests for the pipeline and improve logging.  
- **Training Team:** Update workflow documentation to include accessibility review steps and clarify TDD enforcement.  
- **All Teams:** Review PDB-02 and PDB-03 decisions with data quality and reliability checks before finalizing.

### **RETEST REQUIREMENTS**

- Re-execution of the StatsBomb pipeline with idempotency and error handling implemented.
- Validation of schema constraints and data integrity.
- Evidence of unit/integration test coverage.
- Review of updated workflow documentation for accessibility inclusion.
- Confirmation of data quality checks for StatsBomb and API-Football sources.

---
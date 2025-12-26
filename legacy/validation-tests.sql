-- DispoAssist V0 Validation Tests
-- ===================================

-- Test 1: INSERT test call
INSERT INTO calls (
  scenario_id,
  call_duration,
  patient_age,
  insurance_type,
  admission_diagnosis,
  current_location
) VALUES (
  'TEST-001',
  45,
  65,
  'Medicare',
  'Pneumonia',
  'ICU Room 302'
) RETURNING call_id;

-- Store the call_id for reference (it should be 1)
-- Test 2: INSERT barrier referencing call_id
INSERT INTO barriers (
  call_id,
  barrier_type,
  barrier_description,
  severity,
  resolution_status,
  estimated_delay_hours
) VALUES (
  1,
  'Medical',
  'Waiting for lab results',
  'Medium',
  'Pending',
  24
) RETURNING barrier_id;

-- Test 3: Verify both records exist
SELECT 'Test 3: Verify records exist' AS test_name;
SELECT call_id, scenario_id FROM calls WHERE scenario_id = 'TEST-001';
SELECT barrier_id, barrier_type FROM barriers WHERE call_id = 1;

-- Test 4: CASCADE delete test - delete call and verify barrier is deleted
DELETE FROM calls WHERE scenario_id = 'TEST-001';

-- Test 5: Verify CASCADE worked (should return 0 rows)
SELECT 'Test 5: Verify CASCADE delete worked (expect 0 rows)' AS test_name;
SELECT COUNT(*) as barrier_count FROM barriers WHERE call_id = 1;

-- Test 6: CHECK constraint test - attempt invalid call_duration (should FAIL)
-- This should produce an error
SELECT 'Test 6: Testing CHECK constraint for call_duration > 180 (should FAIL)' AS test_name;
\set ON_ERROR_STOP off
INSERT INTO calls (
  scenario_id,
  call_duration,
  insurance_type,
  admission_diagnosis,
  current_location
) VALUES (
  'TEST-002',
  200,  -- Invalid: exceeds 180
  'Medicare',
  'Test Diagnosis',
  'Test Location'
);
\set ON_ERROR_STOP on

-- Test 7: CHECK constraint test - attempt invalid patient_age (should FAIL)
SELECT 'Test 7: Testing CHECK constraint for patient_age < 18 (should FAIL)' AS test_name;
\set ON_ERROR_STOP off
INSERT INTO calls (
  scenario_id,
  call_duration,
  patient_age,
  insurance_type,
  admission_diagnosis,
  current_location
) VALUES (
  'TEST-003',
  30,
  15,  -- Invalid: less than 18
  'Private',
  'Test Diagnosis',
  'Test Location'
);
\set ON_ERROR_STOP on

-- Test 8: Valid inserts for all tables
SELECT 'Test 8: Insert valid data across all tables' AS test_name;

-- Insert valid call
INSERT INTO calls (
  scenario_id,
  call_duration,
  patient_age,
  insurance_type,
  admission_diagnosis,
  current_location,
  target_discharge_date
) VALUES (
  'TEST-VALID-001',
  60,
  72,
  'Medicare',
  'Hip Replacement Recovery',
  'Orthopedic Floor Room 215',
  CURRENT_DATE + INTERVAL '3 days'
) RETURNING call_id;

-- Insert task (assuming call_id = 2)
INSERT INTO tasks (
  call_id,
  task_type,
  priority,
  completion_status,
  due_date
) VALUES (
  2,
  'Arrange Home Health',
  'High',
  'In Progress',
  CURRENT_DATE + INTERVAL '2 days'
) RETURNING task_id;

-- Insert medication
INSERT INTO medications (
  call_id,
  medication_name,
  current_status,
  issue_type,
  pharmacist_contacted
) VALUES (
  2,
  'Warfarin 5mg',
  'Needs Prior Auth',
  'Insurance Issue',
  true
) RETURNING med_id;

-- Insert appointment
INSERT INTO appointments (
  call_id,
  appointment_type,
  scheduled_date,
  location,
  confirmation_status,
  transportation_arranged
) VALUES (
  2,
  'Follow-up with Orthopedic Surgeon',
  CURRENT_DATE + INTERVAL '7 days',
  'Orthopedic Clinic - Building B',
  'Confirmed',
  true
) RETURNING appt_id;

-- Test 9: Verify all data
SELECT 'Test 9: Verify all inserted data' AS test_name;
SELECT
  c.call_id,
  c.scenario_id,
  c.patient_age,
  c.insurance_type,
  COUNT(DISTINCT t.task_id) as task_count,
  COUNT(DISTINCT m.med_id) as med_count,
  COUNT(DISTINCT a.appt_id) as appt_count
FROM calls c
LEFT JOIN tasks t ON c.call_id = t.call_id
LEFT JOIN medications m ON c.call_id = m.call_id
LEFT JOIN appointments a ON c.call_id = a.call_id
WHERE c.scenario_id = 'TEST-VALID-001'
GROUP BY c.call_id, c.scenario_id, c.patient_age, c.insurance_type;

-- Test 10: Verify RLS is enabled
SELECT 'Test 10: Verify RLS is enabled on all tables' AS test_name;
SELECT
  schemaname,
  tablename,
  rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('calls', 'barriers', 'tasks', 'medications', 'appointments')
ORDER BY tablename;

-- Test 11: Verify RLS policies exist
SELECT 'Test 11: Verify RLS policies exist' AS test_name;
SELECT
  tablename,
  policyname,
  cmd,
  qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd;

-- Test 12: Verify foreign key constraints
SELECT 'Test 12: Verify foreign key constraints' AS test_name;
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table_name,
  ccu.column_name AS foreign_column_name,
  rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
  ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- Validation Summary
SELECT 'VALIDATION SUMMARY' AS summary;
SELECT
  'Total Tables Created' as metric,
  COUNT(*) as value
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('calls', 'barriers', 'tasks', 'medications', 'appointments');

SELECT
  'Total Indexes Created' as metric,
  COUNT(*) as value
FROM pg_indexes
WHERE schemaname = 'public';

SELECT
  'Total RLS Policies' as metric,
  COUNT(*) as value
FROM pg_policies
WHERE schemaname = 'public';

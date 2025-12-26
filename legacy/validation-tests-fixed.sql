-- DispoAssist V0 Validation Tests (Fixed)
-- ==========================================

-- Clean up any existing test data first
DELETE FROM calls WHERE scenario_id LIKE 'TEST%';

-- Test 1: INSERT test call and store the ID
DO $$
DECLARE
  test_call_id INTEGER;
BEGIN
  -- Insert test call
  INSERT INTO calls (
    scenario_id,
    call_duration,
    patient_age,
    insurance_type,
    admission_diagnosis,
    current_location
  ) VALUES (
    'TEST-CASCADE',
    45,
    65,
    'Medicare',
    'Pneumonia',
    'ICU Room 302'
  ) RETURNING call_id INTO test_call_id;

  RAISE NOTICE 'Test 1: Created call with ID %', test_call_id;

  -- Insert barrier referencing the call
  INSERT INTO barriers (
    call_id,
    barrier_type,
    barrier_description,
    severity,
    resolution_status,
    estimated_delay_hours
  ) VALUES (
    test_call_id,
    'Medical',
    'Waiting for lab results',
    'Medium',
    'Pending',
    24
  );

  RAISE NOTICE 'Test 2: Created barrier for call ID %', test_call_id;

  -- Verify both exist
  RAISE NOTICE 'Test 3: Verifying records exist...';
  PERFORM * FROM calls WHERE call_id = test_call_id;
  PERFORM * FROM barriers WHERE call_id = test_call_id;

  -- DELETE call (should CASCADE delete barrier)
  DELETE FROM calls WHERE call_id = test_call_id;
  RAISE NOTICE 'Test 4: Deleted call ID %', test_call_id;

  -- Verify CASCADE worked
  IF NOT EXISTS (SELECT 1 FROM barriers WHERE call_id = test_call_id) THEN
    RAISE NOTICE 'Test 5: CASCADE DELETE verified - barrier successfully deleted';
  ELSE
    RAISE EXCEPTION 'Test 5 FAILED: Barrier still exists after call deletion';
  END IF;
END $$;

-- Test 6: CHECK constraint for call_duration
DO $$
BEGIN
  BEGIN
    INSERT INTO calls (
      scenario_id, call_duration, insurance_type,
      admission_diagnosis, current_location
    ) VALUES (
      'TEST-INVALID-DURATION', 200, 'Medicare',
      'Test', 'Test Location'
    );
    RAISE EXCEPTION 'Test 6 FAILED: Invalid call_duration was accepted';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'Test 6: CHECK constraint for call_duration PASSED (correctly rejected 200)';
  END;
END $$;

-- Test 7: CHECK constraint for patient_age
DO $$
BEGIN
  BEGIN
    INSERT INTO calls (
      scenario_id, call_duration, patient_age, insurance_type,
      admission_diagnosis, current_location
    ) VALUES (
      'TEST-INVALID-AGE', 30, 15, 'Private',
      'Test', 'Test Location'
    );
    RAISE EXCEPTION 'Test 7 FAILED: Invalid patient_age was accepted';
  EXCEPTION WHEN check_violation THEN
    RAISE NOTICE 'Test 7: CHECK constraint for patient_age PASSED (correctly rejected 15)';
  END;
END $$;

-- Test 8: Valid inserts across all tables
DO $$
DECLARE
  new_call_id INTEGER;
BEGIN
  -- Insert valid call
  INSERT INTO calls (
    scenario_id, call_duration, patient_age, insurance_type,
    admission_diagnosis, current_location, target_discharge_date
  ) VALUES (
    'TEST-VALID-COMPLETE',
    60, 72, 'Medicare',
    'Hip Replacement Recovery',
    'Orthopedic Floor Room 215',
    CURRENT_DATE + INTERVAL '3 days'
  ) RETURNING call_id INTO new_call_id;

  RAISE NOTICE 'Test 8: Created valid call with ID %', new_call_id;

  -- Insert task
  INSERT INTO tasks (
    call_id, task_type, priority, completion_status, due_date
  ) VALUES (
    new_call_id, 'Arrange Home Health', 'High',
    'In Progress', CURRENT_DATE + INTERVAL '2 days'
  );

  -- Insert medication
  INSERT INTO medications (
    call_id, medication_name, current_status, issue_type, pharmacist_contacted
  ) VALUES (
    new_call_id, 'Warfarin 5mg', 'Needs Prior Auth',
    'Insurance Issue', true
  );

  -- Insert appointment
  INSERT INTO appointments (
    call_id, appointment_type, scheduled_date, location,
    confirmation_status, transportation_arranged
  ) VALUES (
    new_call_id, 'Follow-up with Orthopedic Surgeon',
    CURRENT_DATE + INTERVAL '7 days', 'Orthopedic Clinic - Building B',
    'Confirmed', true
  );

  RAISE NOTICE 'Test 8: Successfully inserted data across all child tables';
END $$;

-- Display verification queries
SELECT '=== VERIFICATION RESULTS ===' AS section;

SELECT 'Current Test Data:' AS info;
SELECT
  c.call_id,
  c.scenario_id,
  c.patient_age,
  c.insurance_type,
  COUNT(DISTINCT t.task_id) as tasks,
  COUNT(DISTINCT m.med_id) as meds,
  COUNT(DISTINCT a.appt_id) as appts
FROM calls c
LEFT JOIN tasks t ON c.call_id = t.call_id
LEFT JOIN medications m ON c.call_id = m.call_id
LEFT JOIN appointments a ON c.call_id = a.call_id
WHERE c.scenario_id LIKE 'TEST%'
GROUP BY c.call_id, c.scenario_id, c.patient_age, c.insurance_type;

SELECT 'RLS Status on Tables:' AS info;
SELECT
  tablename,
  rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('calls', 'barriers', 'tasks', 'medications', 'appointments')
ORDER BY tablename;

SELECT 'RLS Policies Count by Table:' AS info;
SELECT
  tablename,
  COUNT(*) as policy_count
FROM pg_policies
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

SELECT 'Foreign Key Constraints:' AS info;
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS references_table,
  rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
  ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;

SELECT '=== VALIDATION SUMMARY ===' AS section;
SELECT 'Tables Created' as metric, COUNT(*)::text as value
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('calls', 'barriers', 'tasks', 'medications', 'appointments')
UNION ALL
SELECT 'Indexes Created', COUNT(*)::text
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('calls', 'barriers', 'tasks', 'medications', 'appointments')
UNION ALL
SELECT 'RLS Policies', COUNT(*)::text
FROM pg_policies
WHERE schemaname = 'public'
UNION ALL
SELECT 'Foreign Keys', COUNT(*)::text
FROM information_schema.table_constraints
WHERE table_schema = 'public'
  AND constraint_type = 'FOREIGN KEY';

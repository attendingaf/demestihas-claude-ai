-- DispoAssist V0 Database Schema
-- Created: 2025-11-15
-- Description: Complete schema for DispoAssist V0 with RLS policies

-- =======================
-- DROP EXISTING TABLES (if any)
-- =======================
DROP TABLE IF EXISTS appointments CASCADE;
DROP TABLE IF EXISTS medications CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS barriers CASCADE;
DROP TABLE IF EXISTS calls CASCADE;

-- =======================
-- CREATE TABLES
-- =======================

-- Parent table: calls
CREATE TABLE calls (
  call_id SERIAL PRIMARY KEY,
  scenario_id TEXT NOT NULL,
  call_date TIMESTAMPTZ DEFAULT NOW(),
  call_duration INTEGER CHECK (call_duration BETWEEN 1 AND 180) NOT NULL,
  expeditor_name TEXT DEFAULT 'Mene',
  patient_age INTEGER CHECK (patient_age BETWEEN 18 AND 120),
  insurance_type TEXT NOT NULL,
  admission_diagnosis TEXT NOT NULL,
  current_location TEXT NOT NULL,
  target_discharge_date DATE,
  overall_status TEXT DEFAULT 'Active',
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Child table: barriers
CREATE TABLE barriers (
  barrier_id SERIAL PRIMARY KEY,
  call_id INTEGER REFERENCES calls(call_id) ON DELETE CASCADE NOT NULL,
  barrier_type TEXT NOT NULL,
  barrier_description TEXT NOT NULL,
  severity TEXT NOT NULL,
  identified_by TEXT,
  resolution_status TEXT NOT NULL,
  estimated_delay_hours INTEGER CHECK (estimated_delay_hours BETWEEN 0 AND 720),
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Child table: tasks
CREATE TABLE tasks (
  task_id SERIAL PRIMARY KEY,
  call_id INTEGER REFERENCES calls(call_id) ON DELETE CASCADE NOT NULL,
  task_type TEXT NOT NULL,
  assigned_to TEXT,
  priority TEXT NOT NULL,
  due_date DATE,
  completion_status TEXT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Child table: medications
CREATE TABLE medications (
  med_id SERIAL PRIMARY KEY,
  call_id INTEGER REFERENCES calls(call_id) ON DELETE CASCADE NOT NULL,
  medication_name TEXT NOT NULL,
  current_status TEXT NOT NULL,
  issue_type TEXT,
  resolution_needed TEXT,
  pharmacist_contacted BOOLEAN DEFAULT FALSE,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Child table: appointments
CREATE TABLE appointments (
  appt_id SERIAL PRIMARY KEY,
  call_id INTEGER REFERENCES calls(call_id) ON DELETE CASCADE NOT NULL,
  appointment_type TEXT NOT NULL,
  scheduled_date DATE NOT NULL,
  location TEXT,
  confirmation_status TEXT NOT NULL,
  transportation_arranged BOOLEAN DEFAULT FALSE,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =======================
-- ENABLE ROW LEVEL SECURITY
-- =======================

ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE barriers ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE medications ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- =======================
-- CREATE RLS POLICIES (Permissive for V0)
-- =======================

-- Policies for calls table
CREATE POLICY "Enable read access for authenticated users" ON calls
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON calls
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users" ON calls
  FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Enable delete access for authenticated users" ON calls
  FOR DELETE TO authenticated USING (true);

-- Policies for barriers table
CREATE POLICY "Enable read access for authenticated users" ON barriers
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON barriers
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users" ON barriers
  FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Enable delete access for authenticated users" ON barriers
  FOR DELETE TO authenticated USING (true);

-- Policies for tasks table
CREATE POLICY "Enable read access for authenticated users" ON tasks
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON tasks
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users" ON tasks
  FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Enable delete access for authenticated users" ON tasks
  FOR DELETE TO authenticated USING (true);

-- Policies for medications table
CREATE POLICY "Enable read access for authenticated users" ON medications
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON medications
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users" ON medications
  FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Enable delete access for authenticated users" ON medications
  FOR DELETE TO authenticated USING (true);

-- Policies for appointments table
CREATE POLICY "Enable read access for authenticated users" ON appointments
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "Enable insert access for authenticated users" ON appointments
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "Enable update access for authenticated users" ON appointments
  FOR UPDATE TO authenticated USING (true);

CREATE POLICY "Enable delete access for authenticated users" ON appointments
  FOR DELETE TO authenticated USING (true);

-- =======================
-- CREATE INDEXES FOR PERFORMANCE
-- =======================

CREATE INDEX idx_barriers_call_id ON barriers(call_id);
CREATE INDEX idx_tasks_call_id ON tasks(call_id);
CREATE INDEX idx_medications_call_id ON medications(call_id);
CREATE INDEX idx_appointments_call_id ON appointments(call_id);
CREATE INDEX idx_calls_scenario_id ON calls(scenario_id);
CREATE INDEX idx_calls_call_date ON calls(call_date);

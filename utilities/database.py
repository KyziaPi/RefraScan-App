import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import Error
from flask import jsonify
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

def create_database():
    # 1. Initialize variables to None to prevent UnboundLocalError
    connection = None
    cursor = None
    new_conn = None
    new_cursor = None
    
    try:
        # Connect to PostgreSQL server
        connection = psycopg2.connect(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname="postgres"  # Connect to the default database
        )
        
        # Enable autocommit (PostgreSQL requires this to run CREATE DATABASE)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        
        
        # Check if database exists, create if missing
        DB_NAME = os.getenv("DB_NAME")
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}';")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {DB_NAME};")
        
        # Clean up first connection
        cursor.close()
        connection.close()
        
        # Connect to the newly created database
        new_conn = get_db_connection()
        
        # 2. Create a NEW cursor for the new connection
        new_cursor = new_conn.cursor()
        
        # 3. Removed the trailing comma after PRIMARY KEY
        create_table_query = """
        -- =========================================================
        -- 1) PATIENTS (Master Demographics - 1 per person)
        -- =========================================================
        CREATE TABLE IF NOT EXISTS patients (
            id SERIAL PRIMARY KEY,
            patient_code VARCHAR(50) UNIQUE NOT NULL, -- Human-readable ID
            last_name VARCHAR(100) NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            middle_name VARCHAR(100),
            gender VARCHAR(20) CHECK (gender IN ('Male', 'Female', 'Other')),
            birthdate DATE,
            age INTEGER,
            referred_from VARCHAR(255),
            location VARCHAR(255),
            phone VARCHAR(50),
            email VARCHAR(255),
            date DATE NOT NULL DEFAULT CURRENT_DATE,
            occupation VARCHAR(255),
            language_spoken VARCHAR(100),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- =========================================================
        -- 2) PATIENT MEDICAL HISTORY (Background/Allergies)
        -- =========================================================
        CREATE TABLE IF NOT EXISTS patient_medical_history (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            drug_allergy_present BOOLEAN DEFAULT FALSE,
            drug_allergy_info TEXT,
            pregnancy_status TEXT[],
            pregnancy_info TEXT,
            family_history TEXT[],
            family_history_info TEXT,
            past_history TEXT[],
            past_history_info TEXT,
            medications TEXT[],
            medications_info TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- =========================================================
        -- 3) CLINICAL ENCOUNTERS (1 per Clinic Visit)
        -- =========================================================
        CREATE TABLE IF NOT EXISTS clinical_encounters (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
            pd INTEGER, -- Pupillary Distance in mm 
            manifest_ou VARCHAR(50),
            manifest_ou_details TEXT,
            master_eye VARCHAR(10) CHECK (master_eye IN ('OD', 'OS')),
            rifle_eye VARCHAR(10) CHECK (rifle_eye IN ('OD', 'OS')),
            flucaine_test VARCHAR(100),
            schirmers_test VARCHAR(100),
            additional_details TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        
        -- =========================================================
        -- DIAGNOSES (1:N relationship per Clinical Encounter)
        -- =========================================================
        CREATE TABLE IF NOT EXISTS patient_diagnoses (
            id SERIAL PRIMARY KEY,
            encounter_id INTEGER NOT NULL REFERENCES clinical_encounters(id) ON DELETE CASCADE,
            diagnosis VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        
        -- =========================================================
        -- 4) EYE EXAMINATIONS (1 entry per eye per encounter)
        -- =========================================================
        CREATE TABLE IF NOT EXISTS eye_examinations (
            id SERIAL PRIMARY KEY,
            encounter_id INTEGER NOT NULL REFERENCES clinical_encounters(id) ON DELETE CASCADE,
            eye_side VARCHAR(2) NOT NULL CHECK (eye_side IN ('OD', 'OS')),
            
            -- Slit Lamp & Anterior Segment
            visual_acuity VARCHAR(50),
            pinhole VARCHAR(50),
            eye_movements VARCHAR(255),
            cover_testing VARCHAR(255),
            lids VARCHAR(255),
            conjunctiva VARCHAR(255),
            cornea VARCHAR(255),
            anterior_chamber VARCHAR(255),
            light_reflexes VARCHAR(255),
            eye_pressure VARCHAR(255),
            lens VARCHAR(255),
            nifbut VARCHAR(255),

            -- Topography & Biometry Measurements
            k1 NUMERIC(6,2),
            k2 NUMERIC(6,2),
            axis INTEGER,
            white_to_white NUMERIC(6,2),
            scotopic_pupil NUMERIC(6,2),
            pachymetry INTEGER,

            -- MS-39 Advanced Topography
            ms39_k1 NUMERIC(6,2),
            ms39_k2 NUMERIC(6,2),
            ms39_axis INTEGER,
            ms39_pachy INTEGER,
            ms39_class VARCHAR(50),
            ms39_epi VARCHAR(50),

            UNIQUE(encounter_id, eye_side)
        );

        -- =========================================================
        -- 5) REFRACTION RECORDS (Captures AR, Old, Manifest, Cyclo)
        -- =========================================================
        CREATE TABLE IF NOT EXISTS refractions (
            id SERIAL PRIMARY KEY,
            encounter_id INTEGER NOT NULL REFERENCES clinical_encounters(id) ON DELETE CASCADE,
            refraction_type VARCHAR(20) NOT NULL CHECK (
                refraction_type IN ('Autorefraction', 'Old_Prescription', 'Manifest', 'Cycloplegic')
            ),
            eye_side VARCHAR(2) NOT NULL CHECK (eye_side IN ('OD', 'OS')),
            
            sphere NUMERIC(6,2),        -- DS
            cylinder NUMERIC(6,2),      -- CYL
            axis INTEGER,               -- AXIS
            add_sphere NUMERIC(6,2),    -- ADD
            near_va VARCHAR(50),        -- N or J values
            distance_va VARCHAR(50),    -- Vision / VA
            
            performed_by VARCHAR(255),
            signature_path TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- =========================================================
        -- 6) AI INFERENCE HISTORY (Linked to Patient & Encounter)
        -- =========================================================
        CREATE TABLE IF NOT EXISTS inference_history (
            id SERIAL PRIMARY KEY,
            inference_id VARCHAR(50) UNIQUE NOT NULL DEFAULT 'INF-' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDDHH24MISS'),
            
            patient_id INTEGER REFERENCES patients(id) ON DELETE SET NULL,
            encounter_id INTEGER REFERENCES clinical_encounters(id) ON DELETE SET NULL,
            
            last_name VARCHAR(100) NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            middle_name VARCHAR(100),
            phone VARCHAR(50) NOT NULL,
            age INTEGER NOT NULL,
            email VARCHAR(255),
            
            eye_side VARCHAR(10) CHECK (eye_side IN ('Right', 'Left', 'OD', 'OS')),
            screening_date DATE NOT NULL DEFAULT CURRENT_DATE,
            prediction_label VARCHAR(50) NOT NULL,
            myopia_probability NUMERIC(5,2) NOT NULL DEFAULT 0,
            hyperopia_probability NUMERIC(5,2) NOT NULL DEFAULT 0,
            normal_probability NUMERIC(5,2) NOT NULL DEFAULT 0,
            
            image_name TEXT,
            original_image_path TEXT,
            heatmap_image_path TEXT,
            
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        -- =========================================================
        -- 7) FOLLOW-UPS (Tied to Encounters or Patients)
        -- =========================================================
        CREATE TABLE IF NOT EXISTS patient_follow_ups (
            id SERIAL PRIMARY KEY,
            encounter_id INTEGER NOT NULL REFERENCES clinical_encounters(id) ON DELETE CASCADE,
            follow_up_number INTEGER NOT NULL,
            follow_up_date DATE DEFAULT CURRENT_DATE,
            details TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (encounter_id, follow_up_number)
        );
                                """
        new_cursor.execute(create_table_query)
        new_conn.commit()
        print("Table created successfully in PostgreSQL")
        
    except (Exception, Error) as error:
        print(f"Error while connecting to PostgreSQL: {error}")
        
    finally:
        # 4. Safely check if variables exist before closing
        if new_cursor:
            new_cursor.close()
        if new_conn:
            new_conn.close()
            print("PostgreSQL new_conn is closed")
            
        # Also clean up the first connection if it failed early
        if cursor and not cursor.closed:
            cursor.close()
        if connection and connection.closed == 0:
            connection.close()
            print("PostgreSQL initial connection is closed")


def select_rows(query, params=None, single=False):
    """
    Executes dynamic SELECT queries for both multiple rows and single records.
    
    :param query: SQL query string with %s placeholders
    :param params: Tuple or dict of parameters for the query
    :param single: If True, fetches a single object and returns 404 if missing.
                   If False, fetches a list of objects.
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params or ())
            
            if single:
                row = cursor.fetchone()
                if not row:
                    return jsonify({"message": "Record not found"}), 404
                return jsonify(row), 200
            
            rows = cursor.fetchall()
            return jsonify(rows), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()


def add_row(purpose, query, values):
    """Executes dynamic INSERT queries with automatic rollback on error."""
    connection = None
    try:
        connection = get_db_connection()
        with connection:  # Automatically handles commit/rollback context
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, values)
                
                # If query includes RETURNING, fetch and return that value
                returned_data = None
                if cursor.description:
                    returned_data = cursor.fetchone()
                    
        return jsonify({
            "purpose": purpose,
            "message": "Row inserted successfully!",
            "data": returned_data
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()

def update_row(purpose, query, values):
    """Executes dynamic UPDATE queries with automatic rollback on error."""
    connection = None
    try:
        connection = get_db_connection()
        with connection:  # Automatically handles commit/rollback context
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, values)
                
                # If query includes RETURNING, fetch and return that value
                returned_data = None
                if cursor.description:
                    returned_data = cursor.fetchone()
                    
        return jsonify({
            "purpose": purpose,
            "message": "Row updated successfully!",
            "data": returned_data
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()

def delete_row(purpose, query, params):
    """Executes dynamic DELETE queries safely with automatic rollback and row-count check."""
    connection = None
    try:
        connection = get_db_connection()
        with connection:  # Automatically commits on success, rolls back on error
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                deleted_count = cursor.rowcount  # Tracks how many rows were removed

        # Handle case where SQL ran fine, but no matching record was found
        if deleted_count == 0:
            return jsonify({
                "purpose": purpose,
                "message": "No matching record found to delete."
            }), 404

        return jsonify({
            "purpose": purpose,
            "message": f"Successfully deleted {deleted_count} record(s)."
        }), 200

    except Exception as e:
        return jsonify({"purpose": purpose, "error": str(e)}), 500
    finally:
        if connection:
            connection.close()

  
# For Testing: Delete Table Function          
def delete_table():
    connection = None
    cursor = None
    
    # List tables in strict child-to-parent deletion order
    tables_to_drop = [
        "patient_follow_ups",
        "refractions",
        "eye_examinations",
        "patient_medical_history",
        "inference_history",
        "clinical_encounters",
        "patients"
    ]
    
    try:
        # Connect directly to your specific database
        connection = get_db_connection()
        
        cursor = connection.cursor()

        # Iterate and drop each table in order
        for table in tables_to_drop:
            drop_query = f"DROP TABLE IF EXISTS {table} CASCADE;"
            cursor.execute(drop_query)
            print(f"Dropped table: {table}")

        connection.commit()
        print("\nAll database tables successfully dropped.")

    except (Exception, Error) as error:
        print(f"Error dropping tables: {error}")
        if connection:
            connection.rollback()  # Rollback changes if an error occurs

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            
# For Testing: Add Dummy Data Function
def add_dummy_data():
    connection = None
    cursor = None
    
    try:
        # Connect to your specific database
        connection = get_db_connection()
        
        cursor = connection.cursor()

        # Insert dummy patient data
        insert_patient_query = """
        BEGIN;

        -- 1. Truncate all tables and reset primary key auto-increment sequences
        TRUNCATE TABLE 
            patient_follow_ups,
            refractions,
            eye_examinations,
            clinical_encounters,
            patient_medical_history,
            patients 
        RESTART IDENTITY CASCADE;

        -- 2. Insert Patients
        INSERT INTO patients (patient_code, last_name, first_name, middle_name, gender, birthdate, age, referred_from, location, phone, email, date, occupation, language_spoken) VALUES
        ('25-00001', 'Santos', 'Maria', 'Clara', 'Female', '1988-04-12', 38, 'Dr. Cruz - General Health', 'Quezon City', '09171234567', 'maria.santos@email.com', '2026-01-10', 'Software Engineer', 'Tagalog, English'),
        ('25-00002', 'Reyes', 'Juan', 'Dela Cruz', 'Male', '1975-11-23', 50, 'Walk-in', 'Makati City', '09189876543', 'juan.reyes@email.com', '2026-01-12', 'Accountant', 'Tagalog, English'),
        ('25-00003', 'Tan', 'Grace', 'Lim', 'Female', '1995-02-08', 31, 'Dr. Sy - Ophthalmology', 'Manila', '09223334444', 'gtan95@email.com', '2026-01-15', 'Graphic Designer', 'English, Hokkien'),
        ('26-00004', 'Dizon', 'Mark', 'Bautista', 'Male', '2001-09-15', 24, 'Walk-in', 'Pasig City', '09156667777', 'mark.dizon@email.com', '2026-01-18', 'Student', 'Tagalog'),
        ('26-00005', 'Mendoza', 'Elena', 'Ramos', 'Female', '1962-07-03', 64, 'Barangay Health Center', 'Caloocan', '09391112223', NULL, '2026-01-20', 'Retired Teacher', 'Tagalog'),
        ('26-00006', 'Garcia', 'Carlos', 'Torres', 'Male', '1990-12-30', 35, 'Dr. Cruz - General Health', 'Mandaluyong', '09175558888', 'carlos.garcia@email.com', '2026-02-01', 'Civil Engineer', 'Tagalog, English'),
        ('26-00007', 'Aquino', 'Sophia', 'Hernandez', 'Female', '2010-05-18', 16, 'School Nurse', 'Taguig City', NULL, NULL, '2026-02-03', 'Student', 'English, Tagalog'),
        ('26-00008', 'Villanueva', 'Roberto', 'Navarro', 'Male', '1958-01-20', 68, 'Dr. Sy - Ophthalmology', 'Paranaque', '09204445555', 'rvillanueva@email.com', '2026-02-05', 'Consultant', 'Tagalog, English'),
        ('26-00009', 'Cruz', 'Ana', 'Gonzales', 'Female', '2003-10-05', 22, 'Walk-in', 'San Juan', '09178889999', 'ana.cruz@email.com', '2026-02-10', 'Student', 'Tagalog, English'),
        ('26-00010', 'Bautista', 'Jose', 'Mercado', 'Male', '1982-03-14', 44, 'Walk-in', 'Valenzuela', '09087776666', 'jbautista@email.com', '2026-02-14', 'Driver', 'Tagalog');

        -- 3. Insert Medical History
        INSERT INTO patient_medical_history (patient_id, drug_allergy_present, drug_allergy_info, pregnancy_status, pregnancy_info, family_history, family_history_info, past_history, past_history_info, medications, medications_info) VALUES
        (1, TRUE, 'Penicillin - hives', ARRAY['Not Pregnant'], NULL, ARRAY['Glaucoma', 'Diabetes'], 'Mother had glaucoma at age 60', ARRAY['Astigmatism'], NULL, ARRAY['Multivitamins'], 'Daily morning'),
        (2, FALSE, NULL, NULL, NULL, ARRAY['Hypertension'], 'Father side', ARRAY['Laser Eye Surgery'], 'LASIK OD 2018', ARRAY['Maintenance BP meds'], 'Amlodipine 5mg'),
        (3, TRUE, 'Sulfa drugs', ARRAY['Not Pregnant'], NULL, NULL, NULL, ARRAY['Dry Eye Syndrome'], 'Diagnosed 2023', ARRAY['Artificial Tears'], 'QID PRN'),
        (4, FALSE, NULL, NULL, NULL, ARRAY['Myopia'], 'Both parents high myopes', NULL, NULL, NULL, NULL),
        (5, FALSE, NULL, ARRAY['Not Applicable'], NULL, ARRAY['Cataract', 'Hypertension'], 'Mother had dense cataracts', ARRAY['Cataract Surgery', 'Hypertension'], 'Phaco OS 2021', ARRAY['Losartan 50mg'], 'Daily'),
        (6, FALSE, NULL, NULL, NULL, ARRAY['Diabetes'], NULL, ARRAY['Trauma'], 'Blunt trauma OD 2015', NULL, NULL),
        (7, FALSE, NULL, ARRAY['Not Pregnant'], NULL, ARRAY['Myopia'], 'Sister wears glasses', NULL, NULL, NULL, NULL),
        (8, TRUE, 'Aspirin', NULL, NULL, ARRAY['Glaucoma'], 'Strong family history of POAG', ARRAY['Glaucoma Suspect', 'Cataract'], 'Borderline IOP', ARRAY['Latanoprost'], '1 drop OU at bedtime'),
        (9, FALSE, NULL, ARRAY['Pregnant'], 'First trimester - 10 weeks', NULL, NULL, ARRAY['Contact Lens Wearer'], 'Soft toric lenses 3 years', NULL, NULL),
        (10, FALSE, NULL, NULL, NULL, NULL, NULL, ARRAY['Hypertension'], 'Uncontrolled', ARRAY['Amlodipine'], 'Non-compliant');

        -- 4. Insert Clinical Encounters
        INSERT INTO clinical_encounters (patient_id, master_eye, rifle_eye, flucaine_test, schirmers_test, additional_details, pd, manifest_ou, manifest_ou_details) VALUES
        (1, 'OD', 'OD', 'Negative', '15mm OU', 'Routine vision check for new computer glasses', 62, '20/30', 'J+1.00'),
        (2, 'OS', 'OS', 'Negative', '12mm OD, 10mm OS', 'Post-LASIK checkup and mild glare complaint', 62, '20/20', 'dfgd'),
        (3, 'OD', 'OD', 'Positive OD (Mild staining)', '5mm OD, 4mm OS', 'Complaining of dry, gritty eyes after prolonged computer use', 62, '20/20', NULL),
        (4, 'OD', 'OD', 'Negative', '18mm OU', 'Student complaining of blurry distance vision', 62, '20/200', 'dfgdg'),
        (5, 'OS', 'OS', 'Negative', '8mm OU', 'Decreased visual acuity OD over past 6 months', 62, '20/150', NULL),
        (6, 'OD', 'OD', 'Negative', '14mm OU', 'Follow-up on old blunt trauma OD, no active pain', 62, '20/20', 'SFSDF'),
        (7, 'OD', 'OD', 'Negative', '20mm OU', 'Failed school vision screening', 62, '20/20', NULL),
        (8, 'OS', 'OD', 'Negative', '10mm OU', 'Routine POAG suspect check, pressure monitoring', 62, '20/20', 'SDFSDF'),
        (9, 'OD', 'OD', 'Positive OS (TBUT reduced)', '7mm OS', 'Pregnancy eye consult, soft lens discomfort', 62, '20/20', NULL),
        (10, 'OD', 'OD', 'Negative', NULL, 'General checkup, headache associated with reading', 62, '20/20', NULL);


        -- 5. Insert Patient Diagnoses
        INSERT INTO patient_diagnoses (encounter_id, diagnosis) VALUES
        (1, 'Mild Myopia'),
        (1, 'Astigmatism'),
        (2, 'Post-LASIK Status'),
        (2, 'Mild Glare'),
        (2, 'Dry Eye Syndrome'),
        (3, 'Dry Eye Syndrome'),
        (4, 'High Myopia'),
        (5, 'Cataract'),
        (5, 'Hypertension'),
        (6, 'Old Blunt Trauma OD'),
        (7, 'School Vision Screening Failure'),
        (7, 'Mild Myopia'),
        (7, 'Astigmatism'),
        (7, 'Hyperopia'),
        (8, 'POAG Suspect'),
        (9, 'Pregnancy-related Visual Discomfort'),
        (10, 'Tension Headache with Visual Strain'),
        (10, 'Mild Hyperopia');    
        

        -- 5. Insert Eye Examinations
        INSERT INTO eye_examinations (
            encounter_id, eye_side, visual_acuity, pinhole, eye_movements, cover_testing, lids, conjunctiva, cornea, anterior_chamber, light_reflexes, eye_pressure, lens, nifbut,
            k1, k2, axis, white_to_white, scotopic_pupil, pachymetry, ms39_k1, ms39_k2, ms39_axis, ms39_pachy, ms39_class, ms39_epi
        ) VALUES
        (1, 'OD', '20/30', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '14 mmHg', 'Clear', '12s', 43.25, 44.00, 90, 11.8, 5.2, 545.0, 43.30, 44.10, 88, 546.0, 'Normal', '52um'),
        (1, 'OS', '20/25', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '15 mmHg', 'Clear', '11s', 43.50, 44.25, 85, 11.8, 5.1, 542.0, 43.55, 44.30, 84, 540.0, 'Normal', '51um'),
        (2, 'OD', '20/20', '20/20', 'Full', 'Exophoria 2PD', 'Clear', 'Mild injection', 'LASIK flap intact', 'Deep and clear', 'Brisk', '12 mmHg', 'Clear', '9s', 39.50, 40.25, 180, 12.0, 6.0, 480.0, NULL, NULL, NULL, NULL, NULL, NULL),
        (2, 'OS', '20/20', '20/20', 'Full', 'Exophoria 2PD', 'Clear', 'Mild injection', 'LASIK flap intact', 'Deep and clear', 'Brisk', '12 mmHg', 'Clear', '9s', 39.75, 40.50, 175, 12.0, 6.1, 485.0, NULL, NULL, NULL, NULL, NULL, NULL),
        (3, 'OD', '20/20', '20/20', 'Full', 'Orthophoria', 'MGD Grade 1', 'Hyperemic', 'SPK Inferior', 'Deep and clear', 'Brisk', '16 mmHg', 'Clear', '4s', 42.00, 43.00, 15, 11.5, 4.8, 520.0, 42.10, 43.05, 12, 518.0, 'Dry Eye', '48um'),
        (3, 'OS', '20/20', '20/20', 'Full', 'Orthophoria', 'MGD Grade 1', 'Hyperemic', 'SPK Inferior', 'Deep and clear', 'Brisk', '15 mmHg', 'Clear', '3s', 42.25, 43.25, 170, 11.5, 4.9, 522.0, 42.30, 43.30, 168, 520.0, 'Dry Eye', '47um'),
        (4, 'OD', '20/200', '20/25', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '13 mmHg', 'Clear', '15s', 44.50, 46.00, 95, 12.1, 5.8, 530.0, 44.60, 46.10, 95, 532.0, 'Myopic', '55um'),
        (4, 'OS', '20/150', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '14 mmHg', 'Clear', '14s', 44.25, 45.75, 88, 12.1, 5.7, 535.0, 44.30, 45.80, 89, 536.0, 'Myopic', '54um'),
        (5, 'OD', '20/80', '20/60', 'Full', 'Orthophoria', 'Dermatochalasis', 'Clear', 'Arcus senilis', 'Shallow', 'Sluggish', '18 mmHg', 'NS Grade 3', '8s', 43.00, 43.50, 45, 11.2, 3.5, 510.0, NULL, NULL, NULL, NULL, 'Cataract', NULL),
        (5, 'OS', '20/30', '20/25', 'Full', 'Orthophoria', 'Dermatochalasis', 'Clear', 'Arcus senilis', 'Shallow', 'Brisk', '17 mmHg', 'PCIOL in bag', '10s', 43.25, 43.75, 135, 11.2, 3.6, 515.0, NULL, NULL, NULL, NULL, 'Pseudophakic', NULL),
        (6, 'OD', '20/25', '20/20', 'Full', 'Orthophoria', 'Old scar lid', 'Clear', 'Iris sphincter tear 6 oclock', 'Deep and clear', 'Brisk', '15 mmHg', 'Clear', '11s', 42.75, 43.25, 100, 11.9, 5.6, 560.0, 42.80, 43.30, 98, 558.0, 'Post-Trauma', '58um'),
        (6, 'OS', '20/20', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '14 mmHg', 'Clear', '12s', 42.80, 43.10, 80, 11.9, 5.5, 558.0, 42.85, 43.15, 82, 559.0, 'Normal', '57um'),
        (7, 'OD', '20/50', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '12 mmHg', 'Clear', '15s', 43.00, 44.50, 90, 11.7, 6.2, 540.0, 43.10, 44.60, 90, 539.0, 'Myopic', '53um'),
        (7, 'OS', '20/40', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '13 mmHg', 'Clear', '15s', 43.25, 44.25, 85, 11.7, 6.1, 542.0, 43.30, 44.30, 86, 541.0, 'Myopic', '53um'),
        (8, 'OD', '20/25', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep', 'Sluggish', '21 mmHg', 'NS Grade 1', '7s', 44.00, 44.50, 30, 11.4, 5.0, 505.0, 44.05, 44.55, 32, 504.0, 'Glaucoma Suspect', '50um'),
        (8, 'OS', '20/25', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep', 'Sluggish', '22 mmHg', 'NS Grade 1', '8s', 44.10, 44.60, 150, 11.4, 5.0, 502.0, 44.15, 44.65, 148, 501.0, 'Glaucoma Suspect', '49um'),
        (9, 'OD', '20/20', '20/20', 'Full', 'Orthophoria', 'Clear', 'Mild hyperemia', 'Clear', 'Deep and clear', 'Brisk', '13 mmHg', 'Clear', '6s', 42.50, 43.50, 175, 11.8, 5.3, 530.0, 42.55, 43.55, 172, 528.0, 'Normal', '52um'),
        (9, 'OS', '20/25', '20/20', 'Full', 'Orthophoria', 'Clear', 'Mild hyperemia', 'Clear', 'Deep and clear', 'Brisk', '12 mmHg', 'Clear', '5s', 42.75, 43.75, 5, 11.8, 5.4, 532.0, 42.80, 43.80, 3, 530.0, 'Normal', '51um'),
        (10, 'OD', '20/30', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '16 mmHg', 'Clear', '10s', 43.75, 44.25, 60, 11.6, 4.9, 550.0, NULL, NULL, NULL, NULL, NULL, NULL),
        (10, 'OS', '20/30', '20/20', 'Full', 'Orthophoria', 'Clear', 'Clear', 'Clear', 'Deep and clear', 'Brisk', '15 mmHg', 'Clear', '10s', 43.80, 44.30, 120, 11.6, 5.0, 552.0, NULL, NULL, NULL, NULL, NULL, NULL);

        -- 6. Insert Refractions
        INSERT INTO refractions (encounter_id, refraction_type, eye_side, sphere, cylinder, axis, add_sphere, near_va, distance_va, performed_by) VALUES
        (1, 'Autorefraction', 'OD', -0.75, -0.50, 85, NULL, NULL, '20/30', 'Optician Sarah'),
        (1, 'Autorefraction', 'OS', -0.50, -0.50, 80, NULL, NULL, '20/25', 'Optician Sarah'),
        (1, 'Manifest', 'OD', -0.75, -0.50, 90, +1.25, 'J1', '20/20', 'Dr. Sy'),
        (1, 'Manifest', 'OS', -0.50, -0.50, 85, +1.25, 'J1', '20/20', 'Dr. Sy'),
        (2, 'Old_Prescription', 'OD', -3.25, -0.75, 180, NULL, NULL, '20/20', 'Self-reported'),
        (2, 'Old_Prescription', 'OS', -3.00, -0.50, 175, NULL, NULL, '20/20', 'Self-reported'),
        (2, 'Manifest', 'OD', +0.25, -0.25, 180, +1.75, 'J1', '20/20', 'Dr. Sy'),
        (2, 'Manifest', 'OS', +0.00, -0.25, 175, +1.75, 'J1', '20/20', 'Dr. Sy'),
        (3, 'Autorefraction', 'OD', +0.50, -0.75, 15, NULL, NULL, '20/20', 'Tech Alex'),
        (3, 'Autorefraction', 'OS', +0.50, -1.00, 170, NULL, NULL, '20/20', 'Tech Alex'),
        (3, 'Manifest', 'OD', +0.25, -0.75, 12, NULL, 'J1', '20/20', 'Dr. Cruz'),
        (3, 'Manifest', 'OS', +0.25, -0.75, 168, NULL, 'J1', '20/20', 'Dr. Cruz'),
        (4, 'Autorefraction', 'OD', -5.25, -1.25, 95, NULL, NULL, '20/200', 'Tech Alex'),
        (4, 'Autorefraction', 'OS', -4.75, -1.00, 88, NULL, NULL, '20/150', 'Tech Alex'),
        (4, 'Manifest', 'OD', -5.00, -1.25, 95, NULL, 'J1', '20/25', 'Dr. Sy'),
        (4, 'Manifest', 'OS', -4.50, -1.00, 89, NULL, 'J1', '20/20', 'Dr. Sy'),
        (4, 'Cycloplegic', 'OD', -4.75, -1.25, 95, NULL, NULL, '20/25', 'Dr. Sy'),
        (4, 'Cycloplegic', 'OS', -4.25, -1.00, 89, NULL, NULL, '20/20', 'Dr. Sy'),
        (5, 'Manifest', 'OD', +1.50, -1.00, 45, +2.50, 'J3', '20/60', 'Dr. Sy'),
        (5, 'Manifest', 'OS', +0.25, -0.50, 135, +2.50, 'J1', '20/25', 'Dr. Sy'),
        (6, 'Autorefraction', 'OD', -0.50, -0.75, 100, NULL, NULL, '20/25', 'Optician Sarah'),
        (6, 'Autorefraction', 'OS', -0.25, -0.25, 80, NULL, NULL, '20/20', 'Optician Sarah'),
        (6, 'Manifest', 'OD', -0.50, -0.50, 98, +1.00, 'J1', '20/20', 'Dr. Cruz'),
        (6, 'Manifest', 'OS', -0.25, -0.25, 82, +1.00, 'J1', '20/20', 'Dr. Cruz'),
        (7, 'Autorefraction', 'OD', -1.75, -1.00, 90, NULL, NULL, '20/50', 'Tech Alex'),
        (7, 'Autorefraction', 'OS', -1.50, -0.75, 85, NULL, NULL, '20/40', 'Tech Alex'),
        (7, 'Cycloplegic', 'OD', -1.50, -1.00, 90, NULL, 'J1', '20/20', 'Dr. Sy'),
        (7, 'Cycloplegic', 'OS', -1.25, -0.75, 86, NULL, 'J1', '20/20', 'Dr. Sy'),
        (8, 'Manifest', 'OD', +0.75, -0.50, 32, +2.25, 'J1', '20/20', 'Dr. Sy'),
        (8, 'Manifest', 'OS', +0.75, -0.50, 148, +2.25, 'J1', '20/20', 'Dr. Sy'),
        (9, 'Manifest', 'OD', -0.25, -0.75, 172, NULL, 'J1', '20/20', 'Dr. Cruz'),
        (9, 'Manifest', 'OS', -0.50, -0.75, 3, NULL, 'J1', '20/20', 'Dr. Cruz'),
        (10, 'Autorefraction', 'OD', +1.00, -0.50, 60, NULL, NULL, '20/30', 'Optician Sarah'),
        (10, 'Autorefraction', 'OS', +1.00, -0.50, 120, NULL, NULL, '20/30', 'Optician Sarah'),
        (10, 'Manifest', 'OD', +1.00, -0.50, 60, +1.50, 'J1', '20/20', 'Dr. Cruz'),
        (10, 'Manifest', 'OS', +1.00, -0.50, 120, +1.50, 'J1', '20/20', 'Dr. Cruz');

        -- 7. Insert Follow-Ups
        INSERT INTO patient_follow_ups (encounter_id, follow_up_number, follow_up_date, details) VALUES
        (1, 1, '2026-07-10', '6-month prescription review and optical adaptation check.'),
        (3, 1, '2026-02-15', '1-month re-evaluation for dry eye symptoms post-lubricant therapy.'),
        (4, 1, '2026-04-18', '3-month myopic progression check and lens fitting verification.'),
        (5, 1, '2026-03-20', 'Pre-operative evaluation for OD Phacoemulsification.'),
        (8, 1, '2026-05-05', '3-month IOP check and visual field testing repeat.'),
        (8, 2, '2026-08-05', '6-month OCT and glaucoma follow-up.');

        COMMIT;
                                """
        
        
        cursor.execute(insert_patient_query)
        connection.commit()
        print("Dummy data inserted successfully in PostgreSQL")
    except (Exception, Error) as error:
        print(f"Error inserting dummy data: {error}")
        if connection:
            connection.rollback()  # Rollback changes if an error occurs

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
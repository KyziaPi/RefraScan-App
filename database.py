import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import Error

def create_database():
    # 1. Initialize variables to None to prevent UnboundLocalError
    connection = None
    cursor = None
    new_conn = None
    new_cursor = None
    
    try:
        # Connect to PostgreSQL server
        connection = psycopg2.connect(
            user="postgres",
            password="DONOTUSE",
            host="localhost",
            port="5432",
            dbname="postgres"  # Connect to the default database
        )
        
        # Enable autocommit (PostgreSQL requires this to run CREATE DATABASE)
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        
        # Check if database exists, create if missing
        db_to_create = "refrascandb"
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_to_create}';")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {db_to_create};")
        
        # Clean up first connection
        cursor.close()
        connection.close()
        
        # Connect to the newly created database
        new_conn = psycopg2.connect(
            dbname=db_to_create,
            user="postgres",
            password="DONOTUSE", # Make sure this matches your actual password
            host="localhost"
        )
        
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
            phone VARCHAR(50),
            email VARCHAR(255),
            location VARCHAR(255),
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
            exam_date DATE NOT NULL DEFAULT CURRENT_DATE,
            referred_from VARCHAR(255),
            master_eye VARCHAR(10) CHECK (master_eye IN ('OD', 'OS')),
            rifle_eye VARCHAR(10) CHECK (rifle_eye IN ('OD', 'OS')),
            flucaine_test VARCHAR(100),
            schirmers_test VARCHAR(100),
            additional_details TEXT,
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
            pachymetry NUMERIC(6,2),

            -- MS-39 Advanced Topography
            ms39_k1 NUMERIC(6,2),
            ms39_k2 NUMERIC(6,2),
            ms39_axis INTEGER,
            ms39_pachy NUMERIC(6,2),
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
            screening_id VARCHAR(50) UNIQUE NOT NULL DEFAULT 'INF-' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDDHH24MISS'),
            
            -- Optional links to full clinical records (NULL for quick walk-ins)
            patient_id INTEGER REFERENCES patients(id) ON DELETE SET NULL,
            encounter_id INTEGER REFERENCES clinical_encounters(id) ON DELETE SET NULL,
            
            -- Walk-in / Unlinked Metadata (Used when patient_id IS NULL)
            patient_name VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            email VARCHAR(255),
            age INTEGER,
            
            -- Inference Data
            eye_side VARCHAR(10) CHECK (eye_side IN ('Right', 'Left', 'OD', 'OS')),
            screening_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            prediction_label VARCHAR(50) NOT NULL,
            myopia_probability NUMERIC(5,2) NOT NULL DEFAULT 0,
            hyperopia_probability NUMERIC(5,2) NOT NULL DEFAULT 0,
            normal_probability NUMERIC(5,2) NOT NULL DEFAULT 0,
            
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
            
  
# For Testing: Delete Table Function          
def delete_table():
    connection = None
    cursor = None
    
    try:
        # Connect directly to your specific database
        connection = psycopg2.connect(
            dbname="refrascandb",      # Make sure this matches your lowercase db name
            user="postgres",
            password="DONOTUSE",  # Replace with your actual password
            host="localhost",
            port="5432"
        )
        
        cursor = connection.cursor()
        
        # SQL query to delete the table safely
        delete_table_query = """
                            DROP TABLE IF EXISTS patient_follow_ups;
                            DROP TABLE IF EXISTS inference_results;
                            DROP TABLE IF EXISTS patient_records;
                            """
        
        cursor.execute(delete_table_query)
        connection.commit()  # You must commit the changes for the drop to take effect
        
        print("Table 'inference_results' deleted successfully.")
        
    except (Exception, Error) as error:
        print(f"Error while connecting to PostgreSQL: {error}")
        
    finally:
        # Safely close the cursor and connection
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            print("PostgreSQL connection is closed.")
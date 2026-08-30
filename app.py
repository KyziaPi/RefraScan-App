import os

# 1. Suppress TensorFlow C++ logging (3 = hide INFO, WARNING, and ERROR logs)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# 2. (Optional) Turn off the oneDNN notice explicitly
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from flask import Flask, Response, request, jsonify, render_template, redirect, url_for, send_file
import cv2
import numpy as np
from tensorflow import keras
import joblib
from werkzeug.utils import secure_filename
from datetime import datetime
from email.utils import parsedate_to_datetime
import re
import io
import pandas as pd

import utilities.database as db
from utilities.preprocessing import load_and_preprocess_image
from utilities.explainability import generate_and_save_gradcam


# Create database 
#db.delete_table()
db.create_database()
#db.add_dummy_data()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- MONKEY-PATCH FOR KERAS 3 VERSION MISMATCH ---
_original_dense_init = keras.layers.Dense.__init__

def _patched_dense_init(self, *args, quantization_config=None, **kwargs):
    # Intercept and ignore quantization_config, then pass remaining args to original __init__
    _original_dense_init(self, *args, **kwargs)

keras.layers.Dense.__init__ = _patched_dense_init
# --------------------------------------------------

UPLOAD_FOLDER = os.path.join('static/uploads', 'images')
HEATMAP_FOLDER = os.path.join('static/uploads', 'heatmaps')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HEATMAP_FOLDER, exist_ok=True)

# Refractive Error class labels
CLASS_NAMES = ["Emmetropia", "Myopia", "Hyperopia"]

# Load Model and Scaler
model = keras.models.load_model("static/models/resnet50.keras",
                                compile=False  # Bypasses custom loss (SparseCategoricalFocalLoss) & optimizer loading
                                )
scaler = joblib.load("static/models/scaler.joblib")

input_names = [inp.name for inp in model.inputs]
print(f"Model's input names: {input_names}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def inference_engine():
    """Inference Engine"""
    return render_template("inference-engine.html", page="inference_engine")

@app.route("/about-the-study")
def about_the_study():
    """About The Study"""
    return render_template("about-the-study.html", page="about_the_study")

def format_middle_initial(middle_name):
    """Converts 'Santiago' or 's' to 'S.'"""
    if not middle_name:
        return ""
    clean = str(middle_name).strip()
    if not clean:
        return ""
    return f"{clean[0].upper()}."

@app.route('/submit-inference', methods=['POST'])
def submit_inference():
    if request.method == 'POST':
        # 0. Check the submission type (new patient vs existing patient)
        submission_type = request.form.get('submission_type')
        
        # Check if file is present
        file = request.files.get('file')
        if not file or file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid or missing file format. Allowed: png, jpg, jpeg'}), 400
        
        # Check if shared fields are present
        required_fields = ['age', 'eye_side']
        if not all(request.form.get(field) for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Safely parse numeric fields
        try:
            age = int(request.form.get('age'))
        except (ValueError, TypeError):
            return jsonify({'error': 'Age must be a valid integer'}), 400
        
        eye_side = request.form.get('eye_side')
        
        # 3. Save Original Upload file
        img_filename = secure_filename(file.filename)
        img_filepath = os.path.join(UPLOAD_FOLDER, img_filename)
        file.save(img_filepath)
        
        # Initialize variables
        patient_id = None
        encounter_id = None
        last_name = None
        first_name = None
        middle_name = None
        phone = None
        email = None
            
        # -------------------------------------------------------------
        # BRANCH 1: NEW PATIENT / WALK-IN
        # -------------------------------------------------------------
        if submission_type == 'new':
            # Check if required input fields are present in request
            required_fields = ['last_name', 'first_name', 'phone']
            if not all(request.form.get(field) for field in required_fields):
                return jsonify({'error': 'Missing new patient required fields'}), 400
            
            # Extract Form Fields
            last_name = request.form.get('last_name')
            first_name = request.form.get('first_name')
            middle_name = request.form.get('middle_name', None)
            phone = request.form.get('phone')
            email = request.form.get('email', None)
            
        # -------------------------------------------------------------
        # BRANCH 2: EXISTING PATIENT
        # -------------------------------------------------------------
        else:
            patient_id_str = request.form.get('patient_id')
            if not patient_id_str:
                return jsonify({'error': 'Missing existing patient ID'}), 400
            
            try:
                patient_id = int(patient_id_str)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid patient ID format'}), 400
            
            encounter_id_str = request.form.get('encounter_id')
            if not encounter_id_str:
                return jsonify({'error': 'Missing existing encounter ID'}), 400
            
            try:
                encounter_id = int(encounter_id_str)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid encounter ID format'}), 400
            
            # Fetch existing patient details from the database based on patient ID
            patient_query = "SELECT last_name, first_name, middle_name, phone, email FROM patients WHERE id = %s;"
            patient_res, status = db.select_rows(patient_query, (patient_id,), single=True)
            
            patient_data = patient_res.get_json() if status == 200 else {}
            if isinstance(patient_data, dict) and 'data' in patient_data:
                patient_data = patient_data['data'] or {}
                
            if not patient_data:
                return jsonify({'error': 'Patient record not found in database'}), 404
                
            last_name = patient_data.get('last_name')
            first_name = patient_data.get('first_name')
            middle_name = patient_data.get('middle_name')
            phone = patient_data.get('phone')
            email = patient_data.get('email')
        
        # -------------------------------------------------------------
        # RUN AI INFERENCE & SAVE RESULT
        # -------------------------------------------------------------
        try:
            # 4. Preprocess image
            display_img, processed_img = load_and_preprocess_image(img_filepath, (224, 224))
            
            # Overwrite the saved file with the preprocessed display image (convert RGB -> BGR for OpenCV)
            cv2.imwrite(img_filepath, cv2.cvtColor(display_img, cv2.COLOR_RGB2BGR))
            
            # Ensure batch dimension: shape becomes (1, Height, Width, Channels)
            if len(processed_img.shape) == 3:
                processed_img = np.expand_dims(processed_img, axis=0)
                
            # Preprocess Age for model input
            age_array = np.array([[age]], dtype=np.float32)
            scaled_age = scaler.transform(age_array)
            age_input = scaled_age
        
            # 5. Run inference
            raw_preds = model.predict({"image_input": processed_img, "meta_input": age_input}, verbose=0)                   
            # 6. Extract predictions & probabilities
            pred_idx = int(np.argmax(raw_preds))
                        
            class_probabilities = {
                name: round(float(prob) * 100, 2)
                for name, prob in zip(CLASS_NAMES, raw_preds[0])
            }
                        
            # Map probabilities for PostgreSQL insertion
            myopia_prob = class_probabilities.get("Myopia", 0.0)
            hyperopia_prob = class_probabilities.get("Hyperopia", 0.0)
            normal_prob = class_probabilities.get("Emmetropia", 0.0)
            
            # 5. Return relative path for web rendering
            relative_img_filepath = os.path.join('uploads/images', img_filename).replace("\\", "/")
            
            # 6. Prepare heatmap file path for cleanup in case of error or deletion
            heatmap_filepath = os.path.join(HEATMAP_FOLDER, f"heatmap_{img_filename}")
            
            # 7. Generate and Save Grad-CAM Heatmap
            relative_heatmap_filepath = generate_and_save_gradcam(
                model=model,
                processed_img=processed_img, # Goes into the model for gradients
                display_img=display_img,     # Used as the background canvas
                output_folder=HEATMAP_FOLDER,
                filename=img_filename,
                metadata=scaled_age,
                class_index=pred_idx,
                alpha=0.4
            )
                        
            # 8. Insert Record into PostgreSQL via add_row()
            insert_sql = """
                INSERT INTO inference_history (
                    patient_id, encounter_id, last_name, first_name, middle_name, phone, age, email,
                    eye_side, prediction_label, myopia_probability,
                    hyperopia_probability, normal_probability,
                    image_name, original_image_path, heatmap_image_path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING inference_id;
            """
                        
            db_values = (
                patient_id, encounter_id, last_name, first_name, middle_name, phone, age, email,
                eye_side, CLASS_NAMES[pred_idx], myopia_prob,
                hyperopia_prob, normal_prob,
                img_filename, relative_img_filepath, relative_heatmap_filepath
            )
        
            # Call add_row function
            db_response, status_code =db.add_row(
                purpose="Log AI Inference Result",
                query=insert_sql,
                values=db_values
            )
            
            # Extract JSON payload from Flask Response object
            db_data = db_response.get_json() if hasattr(db_response, 'get_json') else db_response
            
            if status_code != 201:
                error_msg = db_data.get("error", "Database insertion failed") if isinstance(db_data, dict) else "Database insertion failed"
                raise Exception(error_msg)

            new_inference_id = db_data["data"]["inference_id"]

            # 6. Redirect to GET route using returned primary key ID
            return redirect(url_for("inference_results", inference_id=new_inference_id))
        
        except Exception as e:
            if os.path.exists(img_filepath):
                os.remove(img_filepath)
            if os.path.exists(heatmap_filepath):
                os.remove(heatmap_filepath)
            return render_template('index.html', error=f'Inference failed: {str(e)}')
        
@app.route('/api/search-patients', methods=['GET'])
def api_search_patients():
    """API endpoint for live-searching existing patients."""
    query = request.args.get('q', '').lower()
    if not query or len(query) < 2:
        return jsonify([])

    search_term = f"%{query}%"
    
    # Search by First Name, Last Name, Patient Code, or Phone
    sql = """
        SELECT 
            p.id, 
            p.patient_code, 
            p.first_name, 
            p.last_name, 
            p.phone, 
            p.age, 
            p.email,
            (
                SELECT id 
                FROM clinical_encounters 
                WHERE patient_id = p.id 
                ORDER BY id DESC 
                LIMIT 1
            ) AS encounter_id
        FROM patients p 
        WHERE LOWER(p.first_name) LIKE %s 
           OR LOWER(p.last_name) LIKE %s 
           OR LOWER(p.patient_code) LIKE %s 
           OR p.phone LIKE %s
        ORDER BY p.last_name ASC;
    """
    res, status = db.select_rows(sql, (search_term, search_term, search_term, search_term), single=False)
    
    if status == 200:
        data = res.get_json() if hasattr(res, 'get_json') else res
        
        # Extract the list from the "data" wrapper if it exists (matching your db.select_rows pattern)
        patients = data.get('data', []) if isinstance(data, dict) else data
        return jsonify(patients)
        
    return jsonify([])

@app.route("/inference-results/<string:inference_id>", methods=["GET"])
def inference_results(inference_id):
    """Inference Results"""
    select_sql = """
        SELECT 
            inference_id, patient_id, encounter_id, last_name, first_name, middle_name,
            last_name || ', ' || first_name || COALESCE(' ' || LEFT(NULLIF(middle_name, ''), 1) || '.', '') AS "FullName",
            phone, age, email, eye_side, 
            TO_CHAR(screening_date, 'MM-DD-YYYY') AS screening_date, prediction_label, myopia_probability, 
            hyperopia_probability, normal_probability, original_image_path, heatmap_image_path
        FROM inference_history
        WHERE inference_id = %s;
    """
    
    # Call your exact helper function
    response, status_code = db.select_rows(query=select_sql, params=(inference_id,), single=True)

    if status_code != 200:
        return render_template('index.html', error='Inference record not found.'), 404

    # Extract dictionary payload from the Flask JSON response
    record = response.get_json()

    # Reconstruct probabilities map for template
    class_probabilities = {
        'Myopia': float(record['myopia_probability']),
        'Hyperopia': float(record['hyperopia_probability']),
        'Emmetropia': float(record['normal_probability'])
    }

    pred_label = record['prediction_label']
    confidence = class_probabilities.get(pred_label, 0.0)

    return render_template(
        'inference-results.html',
        page="inference_results",
        inference_id=record.get('inference_id'),
        name=record.get('FullName') or record.get('fullname') or "N/A",
        first_name=record.get('first_name', ''),
        last_name=record.get('last_name', ''),
        middle_name=record.get('middle_name', ''),
        date=record.get('screening_date'),
        phone=record.get('phone', ''),
        email=record.get('email', ''),
        age=record.get('age', ''),
        eye_side=record.get('eye_side'),
        prediction=pred_label,
        confidence=f"{confidence:.2f}%",
        probabilities=class_probabilities,
        image_path=record.get('original_image_path'),
        heatmap_path=record.get('heatmap_image_path'),
        patient_id=record.get('patient_id'),
    )


@app.route("/inference-history", methods=["GET"])
def inference_history():
    """Inference History View"""
    select_sql = """
        SELECT
            inference_id, age, eye_side, 
            TO_CHAR(screening_date, 'MM-DD-YYYY') AS screening_date, 
            prediction_label,
            last_name || ', ' || first_name || COALESCE(' ' || LEFT(NULLIF(middle_name, ''), 1) || '.', '') AS "FullName",
            CASE LOWER(prediction_label)
                WHEN 'myopia' THEN myopia_probability
                WHEN 'hyperopia' THEN hyperopia_probability
                WHEN 'normal' THEN normal_probability
                WHEN 'emmetropia' THEN normal_probability
                ELSE 0
            END AS predicted_probability
        FROM inference_history
        ORDER BY screening_date DESC;
    """
    response, status_code = db.select_rows(query=select_sql, params=())
    
    formatted_records = []
    
    if status_code == 200:
        raw_records = response.get_json() or []
        
        for record in raw_records:
            # Parse & Format Date safely
            raw_date = record.get('screening_date')
            if isinstance(raw_date, str):
                try:
                    formatted_date = datetime.fromisoformat(raw_date.replace('Z', '')).strftime("%m-%d-%Y")
                except ValueError:
                    formatted_date = raw_date
            elif hasattr(raw_date, 'strftime'):
                formatted_date = raw_date.strftime("%m-%d-%Y")
            else:
                formatted_date = "N/A"

            # Parse & Format Confidence Percentage
            prob = float(record.get('predicted_probability') or 0.0)
            confidence_str = f"{prob:.2f}%"

            formatted_records.append({
                'inference_id': record.get('inference_id'),
                'name': record.get('fullname') or record.get('FullName') or 'N/A',
                'age': record.get('age'),
                'eye_side': record.get('eye_side'),
                'date': formatted_date,
                'prediction': record.get('prediction_label'),
                'confidence': confidence_str
            })

    return render_template(
        "inference-history.html", 
        page="inference_history", 
        records=formatted_records
    )


@app.route('/api/delete-inference/<string:inference_id>', methods=['DELETE'])
def delete_inference(inference_id):
    """API Endpoint to delete an inference record by ID."""
    
    # Select the record to get file paths before deletion
    select_sql = "SELECT image_name FROM inference_history WHERE inference_id = %s;"
    response, status_code = db.select_rows(query=select_sql, params=(inference_id,), single=True)
    
    record = response.get_json() if response else None
    if status_code != 200 or not response.get_json():
        return jsonify({"error": "Inference record not found."}), 404

    # Delete the record from the database
    delete_sql = "DELETE FROM inference_history WHERE inference_id = %s;"
    db_response, db_status = db.delete_row(
        purpose="Delete Inference Record",
        query=delete_sql,
        params=(inference_id,)
    )
    
    # Clean up physical files ONLY if DB deletion succeeded
    if db_status == 200:
        img_filename = record.get('image_name')
        if img_filename:
            img_filepath = os.path.join(UPLOAD_FOLDER, f"{img_filename}")
            heatmap_filepath = os.path.join(HEATMAP_FOLDER, f"heatmap_{img_filename}")
            
            if os.path.exists(img_filepath):
                os.remove(img_filepath)
            if os.path.exists(heatmap_filepath):
                os.remove(heatmap_filepath)

    return db_response, db_status
    

@app.route("/patient-records", methods=["GET"])
def patient_records():
    """Patient Records View with dynamic list formatting and pagination"""
    select_sql = """
        SELECT 
            p.id,
            p.patient_code,
            p.last_name || ', ' || p.first_name || COALESCE(' ' || LEFT(NULLIF(p.middle_name, ''), 1) || '.', '') AS "full_name",
            p.age,
            COALESCE(p.referred_from, '—') AS referred_from,
            TO_CHAR(p.date, 'MM-DD-YYYY') AS date
        FROM patients p
        ORDER BY p.id DESC;
    """
    response, status_code = db.select_rows(query=select_sql, params=())
    
    formatted_records = []
    
    if status_code == 200:
        raw_records = response.get_json() or []
        
        for record in raw_records:
            formatted_records.append({
                'id': record.get('id'),
                'patient_code': record.get('patient_code') or f"{record.get('id'):05d}",
                'date': record.get('date') or 'N/A',
                'name': record.get('full_name') or 'N/A',
                'age': record.get('age') if record.get('age') is not None else 'N/A',
                'referred_from': record.get('referred_from') or '—'
            })

    return render_template(
        "patient-records.html", 
        page="patient_records", 
        records=formatted_records
    )

def clean_date(val):
    """Parses GMT/ISO date strings or datetime objects and formats as 'Mon DD, YYYY' (e.g., Feb 14, 2026)."""
    if not val:
        return '—'
    if isinstance(val, str):
        # 1. Try parsing GMT HTTP RFC 2822 format (e.g. Sat, 14 Feb 2026 00:00:00 GMT)
        try:
            return parsedate_to_datetime(val).strftime("%b %d, %Y")
        except Exception:
            pass
        # 2. Try parsing ISO string format (e.g. 2026-02-14)
        try:
            return datetime.fromisoformat(val.replace('Z', '')).strftime("%b %d, %Y")
        except Exception:
            return val
    if hasattr(val, 'strftime'):
        return val.strftime("%b %d, %Y")
    return val

def fmt_val(val):
    """Converts values to string so 0 or 0.00 aren't treated as Falsy by Jinja."""
    if val is None or str(val).strip() == "":
        return None
    return str(val)

# ==========================================
# HELPER: Fetch Patient Data by ID
# ==========================================
def fetch_patient_data_by_id(patient_id):
    """Reusable function to gather all patient details from multiple tables."""
    # Helper to parse DB responses safely
    def parse_data(res, status, single=False):
        if status != 200 or not res:
            return None if single else []
        body = res.get_json() if hasattr(res, 'get_json') else res
        if isinstance(body, dict) and 'data' in body:
            return body['data']
        return body

    # 1. Fetch Master Demographics
    p_query = "SELECT * FROM patients WHERE id = %s;"
    p_response, p_status = db.select_rows(p_query, (patient_id,), single=True)
    patient_data = parse_data(p_response, p_status, single=True) or {}

    if not patient_data:
        return None

    # Defaults
    patient_data["follow_ups"] = []
    patient_data["diagnosis"] = []
    patient_data["inferences"] = []  # Added default for AI Inferences

    # 2. Fetch Medical History
    mh_query = "SELECT * FROM patient_medical_history WHERE patient_id = %s;"
    mh_response, mh_status = db.select_rows(mh_query, (patient_id,), single=True)
    mh_data = parse_data(mh_response, mh_status, single=True)
    if mh_data:
        patient_data.update(mh_data)
        if 'drug_allergy_present' in patient_data and isinstance(patient_data['drug_allergy_present'], bool):
            patient_data['drug_allergy_present'] = 'Yes' if patient_data['drug_allergy_present'] else 'No'

    # 3. Fetch Latest Clinical Encounter
    ce_query = "SELECT * FROM clinical_encounters WHERE patient_id = %s ORDER BY id DESC LIMIT 1;"
    ce_response, ce_status = db.select_rows(ce_query, (patient_id,), single=True)
    encounter = parse_data(ce_response, ce_status, single=True)
    
    if encounter:
        patient_data.update(encounter)
        encounter_id = encounter.get('id')
        
        # Map Encounter Column Name Mismatches
        patient_data['manifest_ou_num'] = fmt_val(encounter.get('manifest_ou'))
        patient_data['manifest_ou_details'] = fmt_val(encounter.get('manifest_ou_details'))
        patient_data['pd'] = fmt_val(encounter.get('pd'))
        
        if encounter_id:
            # 4. Fetch Eye Examinations
            ee_query = "SELECT * FROM eye_examinations WHERE encounter_id = %s;"
            ee_response, ee_status = db.select_rows(ee_query, (encounter_id,), single=False)
            ee_list = parse_data(ee_response, ee_status, single=False) or []
            
            if isinstance(ee_list, list):
                for eye in ee_list:
                    side = eye.get('eye_side', '').lower()
                    if not side: 
                        continue
                    
                    for key in ['visual_acuity', 'pinhole', 'eye_movements', 'cover_testing', 'lids', 'conjunctiva', 'cornea', 'anterior_chamber', 'light_reflexes', 'eye_pressure', 'lens', 'nifbut', 'k1', 'k2', 'axis', 'white_to_white', 'scotopic_pupil', 'pachymetry', 'ms39_k1', 'ms39_k2', 'ms39_axis', 'ms39_pachy', 'ms39_class', 'ms39_epi']:
                        mapped_key = f"{side}_{key}" if not key.startswith('ms39') and not key in ['white_to_white', 'scotopic_pupil', 'pachymetry'] else f"ms39_{side}_{key.split('_', 1)[1]}" if key.startswith('ms39') else f"ww_{side}" if key == "white_to_white" else f"scotopic_{side}" if key == "scotopic_pupil" else f"pachy_{side}"
                        if key == 'visual_acuity': mapped_key = f"{side}_va"
                        if key == 'pinhole': mapped_key = f"{side}_ph"
                        if key == 'axis': mapped_key = f"{side}_ax"
                        
                        patient_data[mapped_key] = fmt_val(eye.get(key))

            # 5. Fetch Refractions
            ref_query = "SELECT * FROM refractions WHERE encounter_id = %s;"
            ref_response, ref_status = db.select_rows(ref_query, (encounter_id,), single=False)
            ref_list = parse_data(ref_response, ref_status, single=False) or []
            
            if isinstance(ref_list, list):
                for ref in ref_list:
                    rtype = ref.get('refraction_type')
                    side = ref.get('eye_side', '').lower()
                    
                    prefix_map = {'Autorefraction': 'ar', 'Old_Prescription': 'old', 'Manifest': 'manifest', 'Cycloplegic': 'cyclo'}
                    prefix = prefix_map.get(rtype, '')
                    if not prefix or not side: continue
                    
                    if prefix in ['manifest', 'cyclo'] and ref.get('performed_by'):
                        patient_data[f"{prefix}_by"] = fmt_val(ref.get('performed_by'))
                        
                    patient_data[f"{prefix}_{side}_ds"] = fmt_val(ref.get('sphere'))
                    patient_data[f"{prefix}_{side}_cyl"] = fmt_val(ref.get('cylinder'))
                    patient_data[f"{prefix}_{side}_axis"] = fmt_val(ref.get('axis'))
                    
                    if prefix == "cyclo":
                        patient_data[f"{prefix}_{side}_vision"] = fmt_val(ref.get('distance_va'))
                        patient_data[f"{prefix}_{side}_j"] = fmt_val(ref.get('near_va'))
                    else:
                        patient_data[f"{prefix}_{side}_j"] = fmt_val(ref.get('near_va'))
                        
                    if ref.get('add_sphere') is not None:
                        patient_data[f"{prefix}_add_{side}_ds"] = fmt_val(ref.get('add_sphere'))
                        patient_data[f"{prefix}_add_{side}_n"] = fmt_val(ref.get('near_va'))

            # 6. Fetch Diagnoses
            diag_query = "SELECT diagnosis FROM patient_diagnoses WHERE encounter_id = %s ORDER BY id ASC;"
            diag_res, diag_status = db.select_rows(diag_query, (encounter_id,), single=False)
            raw_diags = parse_data(diag_res, diag_status, single=False) or []
            if isinstance(raw_diags, list):
                patient_data["diagnosis"] = [d.get('diagnosis') for d in raw_diags if isinstance(d, dict) and d.get('diagnosis')]
                    
            # 7. Fetch Follow-Ups
            fu_query = "SELECT * FROM patient_follow_ups WHERE encounter_id = %s ORDER BY follow_up_number ASC;"
            fu_response, fu_status = db.select_rows(fu_query, (encounter_id,), single=False)
            patient_data["follow_ups"] = parse_data(fu_response, fu_status, single=False) or []

    # 8. Fetch AI Inference History
    inf_query = "SELECT * FROM inference_history WHERE patient_id = %s ORDER BY created_at DESC;"
    inf_response, inf_status = db.select_rows(inf_query, (patient_id,), single=False)
    patient_data["inferences"] = parse_data(inf_response, inf_status, single=False) or []

    # 9. Date Cleaning
    for date_key in ['birthdate', 'date', 'created_at', 'updated_at']:
        if date_key in patient_data and patient_data[date_key]:
            patient_data[date_key] = clean_date(patient_data[date_key])
            
    for fu in patient_data.get("follow_ups", []):
        if 'follow_up_date' in fu and fu['follow_up_date']:
            fu['follow_up_date'] = clean_date(fu['follow_up_date'])

    for inf in patient_data.get("inferences", []):
        if 'screening_date' in inf and inf['screening_date']:
            inf['screening_date'] = clean_date(inf['screening_date'])

    return patient_data

# ==========================================
# NEW API ROUTE: Get JSON data for JS Autofill
# ==========================================
@app.route("/api/get-patient/<int:patient_id>", methods=["GET"])
def api_get_patient(patient_id):
    patient_data = fetch_patient_data_by_id(patient_id)
    if not patient_data:
        return jsonify({"error": "Patient not found"}), 404
    return jsonify(patient_data), 200

# ==========================================
# Add/Edit/Prefill Route
# ==========================================
@app.route("/add-patient", methods=["GET", "POST"])
def add_patient():
    """Add Patient Record, Load Edit View, or Pre-fill Screening Data"""
    edit_id = ""
    prefill = {}

    if request.method == "POST":
        # Extract ID passed from Edit buttons
        edit_id = request.form.get("id", "") or request.form.get("patient_id", "")

        # Extract pre-fill demographic values passed from screening/inference results
        prefill = {
            "first_name": request.form.get("first_name", ""),
            "last_name": request.form.get("last_name", ""),
            "middle_name": request.form.get("middle_name", ""),
            "age": request.form.get("age", ""),
            "phone": request.form.get("phone", ""),
            "email": request.form.get("email", "")
        }

    return render_template(
        "add-patient.html", 
        page="add_patient", 
        edit_id=edit_id, 
        prefill=prefill
    )

# ==========================================
# Detailed Record Route
# ==========================================
@app.route("/patient-record-detailed", methods=["POST"])
def patient_record_detailed():
    patient_id = request.form.get("id") or request.form.get("patient_id")
    if not patient_id:
        return redirect("/patient-records") 
        
    patient_data = fetch_patient_data_by_id(patient_id)
    
    if not patient_data:
        return redirect("/patient-records")
        
    return render_template("patient-record-detailed.html", page="patient_record_detailed", patient=patient_data)


def to_num(val):
    """Converts empty string inputs to None for NUMERIC/INTEGER DB columns."""
    if val is not None and str(val).strip() != "":
        try:
            return float(val) if "." in str(val) else int(val)
        except ValueError:
            return None
    return None

def map_eye_side(val):
    """Maps Right/Left form selections to OD/OS DB constraint."""
    if val == 'Right': return 'OD'
    if val == 'Left': return 'OS'
    return val

@app.route("/api/add-patient", methods=["POST"])
def api_add_patient():
    """Handles saving or updating a full patient record across all database tables."""
    data = request.json if request.is_json else (request.form or {})

    # 1. HELPER: Safely extract arrays for checkboxes and dynamic fields
    def get_list_param(key):
        if hasattr(data, 'getlist'):
            return data.getlist(f"{key}[]") or data.getlist(key)
        
        val = data.get(f"{key}[]") or data.get(key)
        if isinstance(val, list):
            return val
        return [val] if val else []

    # 2. HELPER: Map 'Left'/'Right' to 'OS'/'OD' for PostgreSQL constraints
    def map_eye(val):
        val = str(val).lower() if val else ""
        if "left" in val: return "OS"
        if "right" in val: return "OD"
        return None

    # Track if this is an Edit or a New Record
    patient_id = data.get('patient_id')
    encounter_id = data.get('id')
    patient_code = data.get('patient_code')

    # =========================================================
    # 1. PATIENTS (Master Demographics)
    # =========================================================
    if not patient_code:
        # Generate new Patient Code if completely blank
        last_patient_response, status = db.select_rows("""
            SELECT patient_code
            FROM patients
            ORDER BY CAST(SPLIT_PART(patient_code, '-', 2) AS INTEGER) DESC
            LIMIT 1
        """, single=True)

        if status == 200:
            last_patient_code = last_patient_response.json["patient_code"]

            # Get the number after "-"
            last_number = int(last_patient_code.split("-")[1])

            # Increment the latest number
            next_number = last_number + 1
        else:
            # First patient
            next_number = 1

        # Current year, last 2 digits
        current_year = datetime.now().strftime("%y")

        # Generate patient code
        patient_code = f"{current_year}-{next_number:05d}"
        
        print(f"Generated new patient_code: {patient_code}")

    patient_values = (
        patient_code, data.get('last_name'), data.get('first_name'), data.get('middle_name', ''), 
        data.get('gender', 'Other'), data.get('birthdate') or None, to_num(data.get('age')), 
        data.get('phone', ''), data.get('email', ''), data.get('occupation', ''), 
        data.get('referred_from', ''), data.get('location', ''), data.get('language_spoken', ''), 
        data.get('date') or None
    )

    if patient_id:
        # UPDATE Existing Patient
        print(f"Updating existing patient with ID: {patient_id}")
        patient_query = """
            UPDATE patients SET
                patient_code = %s, last_name = %s, first_name = %s, middle_name = %s, 
                gender = %s, birthdate = %s, age = %s, phone = %s, email = %s, occupation = %s, 
                referred_from = %s, location = %s, language_spoken = %s, date = COALESCE(CAST(%s AS DATE), CURRENT_DATE)
            WHERE id = %s;
        """
        response, status = db.update_row("Update Patient", patient_query, patient_values + (patient_id,))
        if status not in [200, 201]: return response, status
    else:
        # INSERT New Patient
        print(f"Inserting new patient with code: {patient_code}")
        patient_query = """
            INSERT INTO patients (
                patient_code, last_name, first_name, middle_name, gender, birthdate, age, phone, email, 
                occupation, referred_from, location, language_spoken, date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(CAST(%s AS DATE), CURRENT_DATE))
            RETURNING id;
        """
        response, status = db.add_row("Add New Patient", patient_query, patient_values)
        if status != 201: return response, status
        
        res_json = response.get_json() or {}
        patient_id = res_json.get('data', {}).get('id') if 'data' in res_json else res_json.get('id')


    # =========================================================
    # 2. PATIENT MEDICAL HISTORY
    # =========================================================
    mh_values = (
        data.get('drug_allergy_present') == 'Yes', data.get('drug_allergy_info', ''),
        get_list_param('pregnancy_status'), data.get('pregnancy_info', ''),
        get_list_param('family_history'), data.get('family_history_info', ''),
        get_list_param('past_history'), data.get('past_history_info', ''),
        get_list_param('medications'), data.get('medications_info', '')
    )
    
    if data.get('id'):
        mh_query = """
            UPDATE patient_medical_history SET
                drug_allergy_present = %s, drug_allergy_info = %s, pregnancy_status = %s, pregnancy_info = %s,
                family_history = %s, family_history_info = %s, past_history = %s, past_history_info = %s,
                medications = %s, medications_info = %s
            WHERE patient_id = %s;
        """
        db.update_row("Update Medical History", mh_query, mh_values + (patient_id,))
    else:
        mh_query = """
            INSERT INTO patient_medical_history (
                drug_allergy_present, drug_allergy_info, pregnancy_status, pregnancy_info,
                family_history, family_history_info, past_history, past_history_info,
                medications, medications_info, patient_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        db.add_row("Add Medical History", mh_query, mh_values + (patient_id,))


    # =========================================================
    # 3. CLINICAL ENCOUNTERS
    # =========================================================
    ce_values = (
        to_num(data.get('pd')), data.get('manifest_ou', ''), data.get('manifest_ou_details', ''),
        map_eye(data.get('master_eye')), map_eye(data.get('rifle_eye')),
        data.get('flucaine_test', ''), data.get('schirmers_test', '')
    )
    
    if encounter_id:
        ce_query = """
            UPDATE clinical_encounters SET
                pd = %s, manifest_ou = %s, manifest_ou_details = %s, master_eye = %s,
                rifle_eye = %s, flucaine_test = %s, schirmers_test = %s
            WHERE id = %s;
        """
        ce_response, ce_status = db.update_row("Update Encounter", ce_query, ce_values + (encounter_id,))
        if ce_status not in [200, 201]: return ce_response, ce_status
        
        # [CRITICAL FIX]: Wipe old sub-records so they can be freshly inserted cleanly below
        db.delete_row("Wipe Old Exams", "DELETE FROM eye_examinations WHERE encounter_id = %s;", (encounter_id,))
        db.delete_row("Wipe Old Refractions", "DELETE FROM refractions WHERE encounter_id = %s;", (encounter_id,))
        db.delete_row("Wipe Old Diagnoses", "DELETE FROM patient_diagnoses WHERE encounter_id = %s;", (encounter_id,))
    else:
        ce_query = """
            INSERT INTO clinical_encounters (
                pd, manifest_ou, manifest_ou_details, master_eye, rifle_eye, flucaine_test, schirmers_test, patient_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        ce_response, ce_status = db.add_row("Add Encounter", ce_query, ce_values + (patient_id,))
        if ce_status != 201: return ce_response, ce_status
        
        ce_json = ce_response.get_json() or {}
        encounter_id = ce_json.get('data', {}).get('id') if 'data' in ce_json else ce_json.get('id')


    # =========================================================
    # 4. SUB-RECORDS (Identical execution for both Edit and New)
    # =========================================================
    if encounter_id:
        
        # A. EYE EXAMINATIONS (OD & OS)
        ee_query = """
            INSERT INTO eye_examinations (
                encounter_id, eye_side, visual_acuity, pinhole, eye_movements, cover_testing,
                lids, conjunctiva, cornea, anterior_chamber, light_reflexes, eye_pressure,
                lens, nifbut, k1, k2, axis, white_to_white, scotopic_pupil, pachymetry,
                ms39_k1, ms39_k2, ms39_axis, ms39_pachy, ms39_class, ms39_epi
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
        """
        for side in ['od', 'os']:
            side_upper = side.upper()
            ee_values = (
                encounter_id, side_upper,
                data.get(f'{side}_va', ''), data.get(f'{side}_ph', ''), data.get(f'{side}_eye_movements', ''),
                data.get(f'{side}_cover_testing', ''), data.get(f'{side}_lids', ''), data.get(f'{side}_conjunctiva', ''),
                data.get(f'{side}_cornea', ''), data.get(f'{side}_anterior_chamber', ''), data.get(f'{side}_light_reflexes', ''),
                data.get(f'{side}_eye_pressure', ''), data.get(f'{side}_lens', ''), data.get(f'{side}_nifbut', ''),
                to_num(data.get(f'{side}_k1')), to_num(data.get(f'{side}_k2')), to_num(data.get(f'{side}_ax')),
                to_num(data.get(f'ww_{side}')), to_num(data.get(f'scotopic_{side}')), to_num(data.get(f'pachy_{side}')),
                to_num(data.get(f'ms39_{side}_k1')), to_num(data.get(f'ms39_{side}_k2')), to_num(data.get(f'ms39_{side}_axis')),
                to_num(data.get(f'ms39_{side}_pachy')), data.get(f'ms39_{side}_class', ''), data.get(f'ms39_{side}_epi', '')
            )
            db.add_row(f"Add Eye Exam ({side_upper})", ee_query, ee_values)

        # B. REFRACTIONS (Autorefraction, Old, Manifest, Cycloplegic)
        ref_query = """
            INSERT INTO refractions (
                encounter_id, refraction_type, eye_side, sphere, cylinder, axis,
                add_sphere, near_va, distance_va, performed_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        refraction_types = [
            ('Autorefraction', 'ar'), ('Old_Prescription', 'old'), 
            ('Manifest', 'manifest'), ('Cycloplegic', 'cyclo')
        ]

        for ref_name, prefix in refraction_types:
            performed_by = data.get(f'{prefix}_by', '') if prefix in ['manifest', 'cyclo'] else ''
            for side in ['od', 'os']:
                side_upper = side.upper()
                ref_values = (
                    encounter_id, ref_name, side_upper,
                    to_num(data.get(f'{prefix}_{side}_ds')), to_num(data.get(f'{prefix}_{side}_cyl')),
                    to_num(data.get(f'{prefix}_{side}_axis')), to_num(data.get(f'{prefix}_add_{side}_ds')),
                    data.get(f'{prefix}_add_{side}_n') or data.get(f'{prefix}_{side}_j', ''),
                    data.get(f'{prefix}_{side}_vision', ''), performed_by
                )
                db.add_row(f"Add Refraction ({ref_name} - {side_upper})", ref_query, ref_values)

        # C. DIAGNOSIS
        diag_query = """
            INSERT INTO patient_diagnoses (encounter_id, diagnosis)
            VALUES (%s, %s);
        """
        raw_diagnoses = get_list_param('diagnosis')
        for diag in raw_diagnoses:
            diag_clean = str(diag).strip() if diag else ""
            if diag_clean:
                db.add_row("Add Diagnosis", diag_query, (encounter_id, diag_clean))

    return jsonify({"success": True, "patient_id": patient_id}), 201

@app.route('/api/delete-patient/<int:patient_id>', methods=['DELETE'])
def api_delete_patient(patient_id):
    """API Endpoint to delete a patient record by ID."""
    
    # 1. Verify the patient exists before attempting deletion
    check_sql = "SELECT id FROM patients WHERE id = %s;"
    res, status = db.select_rows(check_sql, (patient_id,), single=True)
    
    if status != 200 or not res.get_json():
        return jsonify({"error": "Patient record not found."}), 404

    # 2. Delete the record from the database
    # ON DELETE CASCADE in your schema automatically removes all 
    # linked medical history, clinical encounters, refractions, and eye exams.
    delete_sql = "DELETE FROM patients WHERE id = %s;"
    db_response, db_status = db.delete_row(
        purpose="Delete Patient Record",
        query=delete_sql,
        params=(patient_id,)
    )
    
    if db_status == 200:
        return jsonify({"success": True, "message": "Patient record deleted successfully."}), 200
    else:
        return jsonify({"error": "Failed to delete patient record."}), 500

@app.route('/api/save-follow-up', methods=['POST'])
def api_save_follow_up():
    """Handles adding a new follow-up or updating an existing one."""
    data = request.json or {}
    fu_id = data.get('fu_id')
    encounter_id = data.get('encounter_id')
    follow_up_date = data.get('follow_up_date') or None
    details = data.get('details')

    if not encounter_id:
        return jsonify({"error": "No clinical encounter found to attach follow-up to."}), 400

    if fu_id: 
        # Update existing follow-up date and details
        query = """
            UPDATE patient_follow_ups 
            SET details = %s, follow_up_date = COALESCE(CAST(%s AS DATE), CURRENT_DATE) 
            WHERE id = %s;
        """
        res, status = db.update_row("Update Follow Up", query, (details, follow_up_date, fu_id))
    else:
        # Insert new follow-up - calculate next follow_up_number for this encounter
        max_q = "SELECT COALESCE(MAX(follow_up_number), 0) AS max_num FROM patient_follow_ups WHERE encounter_id = %s;"
        max_res, _ = db.select_rows(max_q, (encounter_id,), single=True)
        
        max_data = max_res.get_json() if hasattr(max_res, 'get_json') else {}
        if isinstance(max_data, dict) and 'data' in max_data:
            next_num = max_data['data'].get('max_num', 0) + 1
        else:
            next_num = max_data.get('max_num', 0) + 1 if isinstance(max_data, dict) else 1
        
        query = """
            INSERT INTO patient_follow_ups (encounter_id, follow_up_number, follow_up_date, details) 
            VALUES (%s, %s, COALESCE(CAST(%s AS DATE), CURRENT_DATE), %s);
        """
        res, status = db.add_row("Add Follow Up", query, (encounter_id, next_num, follow_up_date, details))

    if status in [200, 201]:
        return jsonify({"success": True}), 200
    return jsonify({"error": "Failed to save follow up."}), 500

@app.route('/api/delete-follow-up/<int:fu_id>', methods=['DELETE'])
def api_delete_follow_up(fu_id):
    """API Endpoint to delete a follow-up record by ID."""
    query = "DELETE FROM patient_follow_ups WHERE id = %s;"
    res, status = db.delete_row("Delete Follow Up", query, (fu_id,))
    if status == 200:
        return jsonify({"success": True, "message": "Follow-up deleted successfully."}), 200
    return jsonify({"error": "Failed to delete follow-up."}), 500

# ==========================================
# EXPORT EXCEL ROUTE (All Tables)
# ==========================================
@app.route("/export-excel", methods=["POST"])
def export_excel():
    """Generates and downloads an Excel file based on selected fields."""
    selected_fields = request.form.getlist("export_fields[]")
    if not selected_fields:
        return redirect("/patient-records")
    
    # 1. Fetch all patient IDs
    res, status = db.select_rows("SELECT id FROM patients ORDER BY id DESC;", ())
    raw_data = res.get_json() if hasattr(res, 'get_json') else res
    p_ids = [row['id'] for row in (raw_data.get('data', []) if isinstance(raw_data, dict) else raw_data)]
    
    # 2. Gather Data
    export_data = []
    for pid in p_ids:
        p_data = fetch_patient_data_by_id(pid)
        if not p_data: continue
        
        row_dict = {}
        for field in selected_fields:
            val = p_data.get(field, "")
            
            # Formatter for Follow Ups (List of Dictionaries)
            if field == 'follow_ups' and isinstance(val, list):
                fu_strings = []
                for fu in val:
                    fu_date = fu.get('follow_up_date', 'No Date')
                    fu_detail = fu.get('details', 'No Details')
                    fu_strings.append(f"[{fu_date}] {fu_detail}")
                
                # Joins multiple follow ups with a clean divider
                row_dict[field] = "  |  ".join(fu_strings)
            
            # Formatter for other lists (like Diagnosis)
            elif isinstance(val, list):
                row_dict[field] = ", ".join(str(v) for v in val)
                
            else:
                row_dict[field] = val
            
        export_data.append(row_dict)
        
    # 3. Create Excel File
    df = pd.DataFrame(export_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Patient_Records')
    output.seek(0)
    
    return send_file(
        output,
        download_name="RefraScan_Patient_Export.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ==========================================
# IMPORT EXCEL ROUTES (All Tables)
# ==========================================
@app.route("/api/download-template", methods=["GET"])
def download_import_template():
    """Provides a blank Excel template with all supported columns."""
    # This covers Demographics, History, Encounter, Eye Exams, Refractions, and Diagnoses
    fields = [
        'patient_code', 'last_name', 'first_name', 'middle_name', 'gender', 'birthdate', 'age', 'phone', 'email', 'location', 'occupation', 'language_spoken', 'referred_from', 'date',
        'drug_allergy_present', 'drug_allergy_info', 'pregnancy_status', 'pregnancy_info', 'family_history', 'family_history_info', 'past_history', 'past_history_info', 'medications', 'medications_info',
        'pd', 'manifest_ou', 'manifest_ou_details', 'master_eye', 'rifle_eye', 'flucaine_test', 'schirmers_test',
        'od_va', 'os_va', 'od_ph', 'os_ph', 'od_eye_movements', 'os_eye_movements', 'od_cover_testing', 'os_cover_testing', 'od_lids', 'os_lids', 'od_conjunctiva', 'os_conjunctiva', 'od_cornea', 'os_cornea', 'od_anterior_chamber', 'os_anterior_chamber', 'od_light_reflexes', 'os_light_reflexes', 'od_eye_pressure', 'os_eye_pressure', 'od_lens', 'os_lens', 'od_nifbut', 'os_nifbut',
        'od_k1', 'od_k2', 'od_ax', 'os_k1', 'os_k2', 'os_ax', 'ww_od', 'ww_os', 'scotopic_od', 'scotopic_os', 'pachy_od', 'pachy_os',
        'ms39_od_k1', 'ms39_od_k2', 'ms39_od_axis', 'ms39_od_pachy', 'ms39_od_class', 'ms39_od_epi', 'ms39_os_k1', 'ms39_os_k2', 'ms39_os_axis', 'ms39_os_pachy', 'ms39_os_class', 'ms39_os_epi',
        'ar_od_ds', 'ar_od_cyl', 'ar_od_axis', 'ar_os_ds', 'ar_os_cyl', 'ar_os_axis',
        'old_od_ds', 'old_od_cyl', 'old_od_axis', 'old_od_j', 'old_os_ds', 'old_os_cyl', 'old_os_axis', 'old_os_j',
        'manifest_by', 'manifest_od_ds', 'manifest_od_cyl', 'manifest_od_axis', 'manifest_od_j', 'manifest_os_ds', 'manifest_os_cyl', 'manifest_os_axis', 'manifest_os_j', 'manifest_add_od_ds', 'manifest_add_od_n', 'manifest_add_os_ds', 'manifest_add_os_n',
        'cyclo_by', 'cyclo_od_ds', 'cyclo_od_cyl', 'cyclo_od_axis', 'cyclo_od_vision', 'cyclo_od_j', 'cyclo_os_ds', 'cyclo_os_cyl', 'cyclo_os_axis', 'cyclo_os_vision', 'cyclo_os_j', 'cyclo_add_od_ds', 'cyclo_add_od_n', 'cyclo_add_os_ds', 'cyclo_add_os_n',
        'diagnosis', 'follow_ups'
    ]
    
    df = pd.DataFrame(columns=fields)
    # Add a sample row to guide users
    df.loc[0] = ['26-00001', 'Doe', 'John', 'Smith', 'Male', '1990-01-01', 36, '09123456789', 'john@email.com', 'Manila', 'Engineer', 'English', 'Walk-in', '2026-01-01'] + ([''] * (len(fields) - 14))
    df.at[0, 'diagnosis'] = "Myopia, Dry Eye"
    df.at[0, 'follow_ups'] = "[2026-02-14] Patient responded well to medication  |  [2026-03-01] Second checkup cleared"
    df.at[0, 'drug_allergy_present'] = "No"

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Template')
    output.seek(0)
    
    return send_file(
        output,
        download_name="RefraScan_Import_Template.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/api/import-excel", methods=["POST"])
def import_excel():
    """Parses uploaded Excel and inserts into all 7 tables."""
    file = request.files.get('excel_file')
    if not file or not file.filename.endswith('.xlsx'):
        return render_template('index.html', error='Invalid file format. Please upload an .xlsx file.')

    try:
        # Parse Excel and convert NaNs to empty strings
        df = pd.read_excel(file)
        df = df.fillna("")
        records = df.to_dict(orient="records")
        
        for row in records:
            last_name = str(row.get('last_name', '')).strip()
            first_name = str(row.get('first_name', '')).strip()
            if not last_name or not first_name:
                continue # Skip blank rows
                
            patient_code = str(row.get('patient_code', '')).strip()
            
            # 1. Generate patient code if missing
            if not patient_code:
                max_res, max_status = db.select_rows("SELECT patient_code FROM patients ORDER BY id DESC LIMIT 1;", single=True)
                try:
                    last_code = max_res.get_json()['data']['patient_code']
                    next_num = int(last_code.split("-")[1]) + 1
                except:
                    next_num = 1
                patient_code = f"{datetime.now().strftime('%y')}-{next_num:05d}"
            
            # 2. PATIENTS TABLE
            patient_query = """
                INSERT INTO patients (
                    patient_code, last_name, first_name, middle_name, gender, birthdate, 
                    age, phone, email, location, occupation, language_spoken, referred_from, date
                ) VALUES (%s, %s, %s, %s, %s, NULLIF(%s, ''), %s, %s, %s, %s, %s, %s, %s, COALESCE(NULLIF(%s, '')::DATE, CURRENT_DATE))
                ON CONFLICT (patient_code) DO UPDATE SET 
                    phone = EXCLUDED.phone, age = EXCLUDED.age, location = EXCLUDED.location
                RETURNING id;
            """
            p_vals = (
                patient_code, last_name, first_name, row.get('middle_name'), row.get('gender', 'Other'), 
                row.get('birthdate'), to_num(row.get('age')), row.get('phone'), row.get('email'), 
                row.get('location'), row.get('occupation'), row.get('language_spoken'), row.get('referred_from'), row.get('date')
            )
            p_res, p_stat = db.add_row("Import Patient", patient_query, p_vals)
            
            # Get Patient ID to link the rest of the tables
            if p_stat in [200, 201]:
                p_json = p_res.get_json() if hasattr(p_res, 'get_json') else p_res
                patient_id = p_json.get('data', {}).get('id') if 'data' in p_json else p_json.get('id')
            else:
                continue

            # 3. MEDICAL HISTORY TABLE
            mh_query = """
                INSERT INTO patient_medical_history (
                    patient_id, drug_allergy_present, drug_allergy_info, pregnancy_status, pregnancy_info,
                    family_history, family_history_info, past_history, past_history_info, medications, medications_info
                ) VALUES (%s, %s, %s, string_to_array(%s, ','), %s, string_to_array(%s, ','), %s, string_to_array(%s, ','), %s, string_to_array(%s, ','), %s)
                ON CONFLICT DO NOTHING;
            """
            db.add_row("Import Medical History", mh_query, (
                patient_id, str(row.get('drug_allergy_present', '')).lower() == 'yes', row.get('drug_allergy_info'),
                row.get('pregnancy_status'), row.get('pregnancy_info'), row.get('family_history'), row.get('family_history_info'),
                row.get('past_history'), row.get('past_history_info'), row.get('medications'), row.get('medications_info')
            ))

            # 4. CLINICAL ENCOUNTERS TABLE
            ce_query = """
                INSERT INTO clinical_encounters (
                    patient_id, pd, manifest_ou, manifest_ou_details, master_eye, rifle_eye, flucaine_test, schirmers_test
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
            """
            ce_res, ce_stat = db.add_row("Import Encounter", ce_query, (
                patient_id, to_num(row.get('pd')), row.get('manifest_ou'), row.get('manifest_ou_details'),
                row.get('master_eye'), row.get('rifle_eye'), row.get('flucaine_test'), row.get('schirmers_test')
            ))
            
            if ce_stat in [200, 201]:
                ce_json = ce_res.get_json() if hasattr(ce_res, 'get_json') else ce_res
                encounter_id = ce_json.get('data', {}).get('id') if 'data' in ce_json else ce_json.get('id')
            else:
                continue

            # 5. EYE EXAMINATIONS (OD & OS)
            ee_query = """
                INSERT INTO eye_examinations (
                    encounter_id, eye_side, visual_acuity, pinhole, eye_movements, cover_testing, lids, conjunctiva, cornea, anterior_chamber, light_reflexes, eye_pressure, lens, nifbut,
                    k1, k2, axis, white_to_white, scotopic_pupil, pachymetry, ms39_k1, ms39_k2, ms39_axis, ms39_pachy, ms39_class, ms39_epi
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            for side in ['od', 'os']:
                db.add_row("Import Eye Exam", ee_query, (
                    encounter_id, side.upper(), row.get(f'{side}_va'), row.get(f'{side}_ph'), row.get(f'{side}_eye_movements'), row.get(f'{side}_cover_testing'),
                    row.get(f'{side}_lids'), row.get(f'{side}_conjunctiva'), row.get(f'{side}_cornea'), row.get(f'{side}_anterior_chamber'), row.get(f'{side}_light_reflexes'),
                    row.get(f'{side}_eye_pressure'), row.get(f'{side}_lens'), row.get(f'{side}_nifbut'),
                    to_num(row.get(f'{side}_k1')), to_num(row.get(f'{side}_k2')), to_num(row.get(f'{side}_ax')), to_num(row.get(f'ww_{side}')), to_num(row.get(f'scotopic_{side}')), to_num(row.get(f'pachy_{side}')),
                    to_num(row.get(f'ms39_{side}_k1')), to_num(row.get(f'ms39_{side}_k2')), to_num(row.get(f'ms39_{side}_axis')), to_num(row.get(f'ms39_{side}_pachy')), row.get(f'ms39_{side}_class'), row.get(f'ms39_{side}_epi')
                ))

            # 6. REFRACTIONS
            ref_query = """
                INSERT INTO refractions (encounter_id, refraction_type, eye_side, sphere, cylinder, axis, add_sphere, near_va, distance_va, performed_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
            ref_types = [('Autorefraction', 'ar'), ('Old_Prescription', 'old'), ('Manifest', 'manifest'), ('Cycloplegic', 'cyclo')]
            for ref_name, prefix in ref_types:
                performed_by = row.get(f'{prefix}_by', '') if prefix in ['manifest', 'cyclo'] else ''
                for side in ['od', 'os']:
                    db.add_row("Import Refraction", ref_query, (
                        encounter_id, ref_name, side.upper(), to_num(row.get(f'{prefix}_{side}_ds')), to_num(row.get(f'{prefix}_{side}_cyl')), to_num(row.get(f'{prefix}_{side}_axis')),
                        to_num(row.get(f'{prefix}_add_{side}_ds')), row.get(f'{prefix}_add_{side}_n') or row.get(f'{prefix}_{side}_j', ''), row.get(f'{prefix}_{side}_vision', ''), performed_by
                    ))

            # 7. DIAGNOSES
            diags = str(row.get('diagnosis', '')).split(',')
            for diag in diags:
                if diag.strip():
                    db.add_row("Import Diagnosis", "INSERT INTO patient_diagnoses (encounter_id, diagnosis) VALUES (%s, %s);", (encounter_id, diag.strip()))

            # 8. FOLLOW UPS (Parsing from formatted string)
            fu_str = str(row.get('follow_ups', '')).strip()
            if fu_str:
                fu_list = fu_str.split('  |  ')
                for i, fu_item in enumerate(fu_list):
                    # Uses regex to split "[2026-02-14] My Details" into Date and Details
                    match = re.match(r'\[(.*?)\]\s*(.*)', fu_item.strip())
                    if match:
                        fu_date, fu_detail = match.groups()
                        fu_date = fu_date if fu_date and fu_date != 'No Date' else None
                    else:
                        fu_date, fu_detail = None, fu_item.strip()
                    
                    if fu_detail:
                        db.add_row("Import Follow Up", 
                                   "INSERT INTO patient_follow_ups (encounter_id, follow_up_number, follow_up_date, details) VALUES (%s, %s, COALESCE(NULLIF(%s, '')::DATE, CURRENT_DATE), %s);", 
                                   (encounter_id, i+1, fu_date, fu_detail))

        return redirect("/patient-records")
        
    except Exception as e:
        return f"An error occurred during import: {str(e)}"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
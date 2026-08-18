import os

# 1. Suppress TensorFlow C++ logging (3 = hide INFO, WARNING, and ERROR logs)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# 2. (Optional) Turn off the oneDNN notice explicitly
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from flask import Flask, request, jsonify, render_template, abort, redirect, url_for, flash
import cv2
import numpy as np
from tensorflow import keras
import joblib
from werkzeug.utils import secure_filename
from datetime import datetime
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
model = keras.models.load_model("static/models/best_resnet50_fold_1(1).keras",
                                compile=False  # Bypasses custom loss (SparseCategoricalFocalLoss) & optimizer loading
                                )
scaler = joblib.load("static/models/scaler_fold_1(1).joblib")

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
            pass  # Handle existing patient submission (to be implemented)
            # SELECT THE REST OF THE EXISTING PATIENT DETAILS FROM DATABASE BASED ON PATIENT ID
        
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

@app.route("/inference-results/<string:inference_id>", methods=["GET"])
def inference_results(inference_id):
    """Inference Results"""
    select_sql = """
        SELECT 
            inference_id, patient_id, encounter_id, 
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
        date=record.get('screening_date'),
        phone=record.get('phone', 'N/A'),
        email=record.get('email') or "N/A",
        age=record.get('age'),
        eye_side=record.get('eye_side'),
        prediction=pred_label,
        confidence=f"{confidence:.2f}%",
        probabilities=class_probabilities,
        image_path=record.get('original_image_path'),
        heatmap_path=record.get('heatmap_image_path')
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
    

@app.route("/patient-records")
def patient_records():
    """Patient Records"""
    return render_template("patient-records.html", page="patient_records")

@app.route("/patient-record-detailed")
def patient_record_detailed():
    """Detailed Patient Record"""
    # Fetch patient object/dictionary from DB
    #patient_data = get_patient_by_id(...)
    
    # Placeholder for now
    patient_data = {}
    return render_template("patient-record-detailed.html", page="patient_record_detailed", patient=patient_data)

@app.route("/add-patient", methods=["GET", "POST"])
def add_patient():
    """Add Patient Record"""
    if request.method == "POST":
        # Process form data and save to database
        # Example: name = request.form['name']
        return redirect("/patient-records")
    
    return render_template("add-patient.html", page="add_patient")

@app.route("/delete-patient", methods=["POST"])
def delete_patient():
    """Delete Patient Record"""
    # Implement deletion logic here (e.g., remove from database)
    return redirect("/patient-records")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
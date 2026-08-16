import os

# 1. Suppress TensorFlow C++ logging (3 = hide INFO, WARNING, and ERROR logs)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# 2. (Optional) Turn off the oneDNN notice explicitly
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from flask import Flask, request, jsonify, render_template, abort, redirect, session
import cv2
import numpy as np
from tensorflow import keras
import joblib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Refractive Error class labels
CLASS_NAMES = ["Emmetropia", "Myopia", "Hyperopia"]

# --- MONKEY-PATCH FOR KERAS 3 VERSION MISMATCH ---
_original_dense_init = keras.layers.Dense.__init__

def _patched_dense_init(self, *args, quantization_config=None, **kwargs):
    # Intercept and ignore quantization_config, then pass remaining args to original __init__
    _original_dense_init(self, *args, **kwargs)

keras.layers.Dense.__init__ = _patched_dense_init
# --------------------------------------------------

# Load Model and Scaler
model = keras.models.load_model("static/models/best_efficientnet_fold_1.keras",
                                compile=False  # Bypasses custom loss (SparseCategoricalFocalLoss) & optimizer loading
                                )
scaler = joblib.load("static/models/scaler_fold_1.joblib")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_and_preprocess_image(img_path, target_size=(300, 300)):
    """
    Loads image, and handles padding vs standard resize.
    """
    try:
        img = cv2.imread(img_path)
        if img is None:
            raise FileNotFoundError(f"Image not found at path: {img_path}")
            
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Calculate padding dimensions
        h, w = img.shape[:2]
        th, tw = target_size
        scale = min(tw / w, th / h)
        nw, nh = int(w * scale), int(h * scale)
        
        # Resize image keeping aspect ratio
        resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)

        # Create canvas and center the image
        padded = np.zeros((th, tw, 3), dtype=np.uint8)
        top = (th - nh) // 2
        left = (tw - nw) // 2
        padded[top : top + nh, left : left + nw] = resized
        
        return padded

    except Exception as e:
        return np.zeros((target_size[0], target_size[1], 3), dtype=np.uint8)


@app.route("/", methods=["GET"])
def inference_engine():
    """Inference Engine"""
    return render_template("inference-engine.html", page="inference_engine")

@app.route("/about-the-study")
def about_the_study():
    """About The Study"""
    return render_template("about-the-study.html", page="about_the_study")

@app.route("/inference-results", methods=["POST", "GET"])
def inference_results():
    """Inference Results"""
    if request.method == "POST":
        # 1. Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part provided'}), 400
        
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file format. Allowed: png, jpg, jpeg'}), 400

        try:
            # 2. Save file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            # 3. Preprocess image
            processed_img = load_and_preprocess_image(filepath)

            # 4. Ensure batch dimension: shape becomes (1, Height, Width, Channels)
            if len(processed_img.shape) == 3:
                processed_img = np.expand_dims(processed_img, axis=0)

            # 5. Run inference
            raw_preds = model.predict(processed_img)[0]
            
            # 6. Extract predictions & probabilities
            pred_idx = int(np.argmax(raw_preds))
            confidence = round(float(raw_preds[pred_idx]) * 100, 2)
            
            class_probabilities = {
                CLASS_NAMES[i]: round(float(raw_preds[i]) * 100, 2)
                for i in range(len(CLASS_NAMES))
            }
            
            # Format image path for Jinja2 template (relative to static directory)
            relative_image_path = os.path.join('uploads', filename).replace("\\", "/")

            return render_template(
                'inference-results.html',
                page="inference_results",
                prediction=CLASS_NAMES[pred_idx],
                confidence=f"{confidence}%",
                probabilities=class_probabilities,
                image_path=relative_image_path
            )

        except Exception as e:
            return render_template('index.html', error=f'Inference failed: {str(e)}')
        
    if request.method == "GET":
        return render_template("inference-results.html", page="inference_results")


@app.route("/inference-history")
def inference_history():
    """Inference History"""
    return render_template("inference-history.html", page="inference_history")

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
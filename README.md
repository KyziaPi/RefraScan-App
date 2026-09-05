# RefraScan App

RefraScan is a Flask-based web application designed for managing patient ophthalmic records for The Lasik Surgery Clinic - AUFMC and performing AI-assisted fundus image screening with explainable Grad-CAM heatmaps.

---

## ⚡ Features

* **Patient & Clinical Record Management:** Normalized storage for patient demographics, clinical encounters, eye examinations, refractions, and follow-up schedules.


* **AI Ophthalmic Screening:** Automated image processing and model inference with Grad-CAM heatmap visualization.


* **Network & Multi-User Deployment:** Centralized PostgreSQL database support with synchronized, shared network upload storage across multiple client PCs.


* **Data Mobility:** Built-in Excel template import and export features.



---

## 📁 Repository Structure

```text
RefraScan-App/
├── Refrascan/              # Core application source code
│   ├── app.py              # Main Flask application
│   ├── run-app.py          # Application launcher script
│   ├── static/             # Static assets, image uploads, and heatmaps
│   ├── templates/          # HTML view templates
│   └── utilities/          # Database and explainability helper scripts
│   └── requirements.txt    # Python package dependencies
├── tools/                  # Windows helper batch scripts
│   ├── SETUP.bat           # Initializes .venv and installs dependencies
│   ├── START-APP.bat       # Activates virtual environment and launches app
│   └── TEST-NETWORK.bat    # Validates database connection & network path
├── guides/                 # Detailed documentation and user manuals
├── .env.example            # Environment variables template

```

---

## 💻 Requirements

* **OS:** Windows 10 or later


* **Language:** Python 3.8+


* **Database:** PostgreSQL


* **Core Dependencies:** Flask, TensorFlow, OpenCV, NumPy, Pandas, OpenPyXL, Psycopg2-Binary, Joblib, Scikit-Learn, Python-Dotenv



---

## 🚀 Quick Start

### 1. Configuration

Copy `.env.example` to `.env` in the RefraScan folder and configure your database and file paths:

```ini
DB_NAME=refrascan_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=5432
UPLOAD_BASE_PATH=

```

### 2. Initial Setup

Run `tools\SETUP.bat` once to create the local Python virtual environment (`.venv`) and install required packages from `requirements.txt`.

### 3. Start the Application

Run `tools\START-APP.bat`. The launcher will start the Flask server and open `http://localhost:5000` automatically in your web browser.

---

## 🌐 Multi-Computer Network Setup

To share data and uploads across multiple client machines on a LAN:

1. **Server PC:** Share the `static/uploads` directory over the local network and set up PostgreSQL to accept incoming network connections.


2. **Client PCs:** Map the server's shared folder as a network drive (e.g., `Z:\`).


3. **Configure `.env`:** Point `DB_HOST` to the Server IP and `UPLOAD_BASE_PATH` to the mapped drive.



```ini
DB_HOST=192.168.1.100
UPLOAD_BASE_PATH=Z:\

```


4. **Diagnostic Check:** Run `tools\TEST-NETWORK.bat` to verify database connectivity and network drive access.

---

## 🔧 Troubleshooting

* **Python missing error:** Ensure Python 3.8+ is installed and checked for **"Add Python to PATH"** during installation.


* **Database connection failed:** Check that the PostgreSQL service is active and credentials in `.env` match.


* **Port 5000 in use:** Stop competing processes on port 5000 using `netstat -ano | findstr :5000` then get the rightmost value which contains the PID. Lastly, type `taskkill /PID <PID> /F` substitute <PID> with the value you copied earlier.


* **Network share offline:** Ensure the mapped drive is active on client PCs before launching.



---

**Version:** 1.0

**Contact:** guecoyerikaelaine@gmail.com
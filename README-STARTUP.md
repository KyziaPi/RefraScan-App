# RefraScan App - Startup Guide

## First Time Setup

### Step 1: Initial Setup (One-Time Only)
1. Double-click **SETUP.bat**
2. Follow the prompts to create the virtual environment
3. This will install all required dependencies from `requirements.txt`
4. The process may take 3-5 minutes

### Step 2: Start the App
After setup is complete, simply double-click **START-APP.bat**

The app will:
- ✓ Automatically activate the virtual environment
- ✓ Check and update dependencies if needed
- ✓ Start the Flask server
- ✓ Open your browser to http://localhost:5000
- ✓ Show status messages in the console

## Daily Usage

Just double-click **START-APP.bat** every time you want to use the app.

## Stopping the App

To stop the app, return to the command window and press **Ctrl+C**, then press any key to close the window.

## Troubleshooting

### "Python is not installed"
- Install Python 3.8+ from https://www.python.org/
- **Important**: Check the box "Add Python to PATH" during installation
- Restart your computer after installation

### "Virtual environment not found"
- Run **SETUP.bat** first to create it

### "Browser doesn't open automatically"
- The app is still running on http://localhost:5000
- Manually open your browser and go to http://localhost:5000

### Port 5000 already in use
- Another application is using port 5000
- Close that application or restart your computer

## For Non-Technical Users

You only need to remember:
1. **First time**: Double-click **SETUP.bat** (once only)
2. **Every time after**: Double-click **START-APP.bat**
3. **To stop**: Press Ctrl+C in the black window

That's it! No need to use command line or PowerShell.

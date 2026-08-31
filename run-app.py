import os
import webbrowser
import time
import subprocess
import sys

def main():
    """Start Flask server and open browser automatically"""
    
    print("=" * 60)
    print("RefraScan App Launcher")
    print("=" * 60)
    
    # Check if virtual environment is activated
    if os.getenv('VIRTUAL_ENV') is None:
        print("\n⚠️  Virtual environment not activated!")
        print("Please run 'START-APP.bat' instead of running this directly.")
        print("\nPress any key to exit...")
        input()
        sys.exit(1)
    
    # Check if requirements are installed
    print("\n📦 Checking if all dependencies are installed...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], 
                          capture_output=True)
    if result.returncode == 0:
        print("✓ Dependencies are up to date")
    else:
        print("⚠️  Some dependencies may be missing, attempting to install...")
    
    # Start Flask server
    print("\n🚀 Starting RefraScan App...")
    print("   Server: http://localhost:5000")
    print("   Press Ctrl+C to stop the app\n")
    
    try:
        process = subprocess.Popen([sys.executable, "-m", "flask", "run"])
        
        # Wait for server to start
        time.sleep(3)
        
        # Open browser automatically
        print("📱 Opening browser...")
        webbrowser.open("http://localhost:5000")
        
        # Keep the process running
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping app...")
        process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()

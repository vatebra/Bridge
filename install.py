import subprocess
import sys

# Install required packages
packages = [
    "flask==2.3.3",
    "requests==2.31.0", 
    "flask-cors==4.0.0",
    "gunicorn==21.2.0"
]

for package in packages:
    print(f"Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

print("All packages installed successfully!")

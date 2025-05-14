import os
import subprocess
import webbrowser
import time

# Set the working directory to the project root
os.chdir('c:/Users/anil_/Documents/concrete_mix_project')

# Start Jupyter notebook server in the background
print("Starting Jupyter notebook server...")
notebook_process = subprocess.Popen(
    ['jupyter', 'notebook', '--notebook-dir=analysis'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Give the server a moment to start
time.sleep(3)

print("Jupyter notebook server started.")
print("You can now open the strength_classification_analysis.ipynb notebook in your browser.")
print("Press Ctrl+C to stop the server when you're done.")

try:
    # Keep the script running to maintain the server
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # Handle graceful shutdown
    print("\nShutting down notebook server...")
    notebook_process.terminate()
    print("Notebook server stopped.")

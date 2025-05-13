#!/usr/bin/env python
"""
Utility script to run the development server with clear indicators for which app you're viewing.
This adds a banner to help distinguish between the original app and the CDB app.
"""
import os
import subprocess
import sys

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')

# Default port
port = "8000"

# Allow custom port via command line
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    port = sys.argv[1]

print("\n======================================================")
print("Starting Django development server with dual app support:")
print("------------------------------------------------------")
print("Original Concrete Mix App: http://localhost:{}/".format(port))
print("New CDB App:               http://localhost:{}/cdb/".format(port))
print("Admin Interface:          http://localhost:{}/admin/".format(port))
print("======================================================\n")
print("The apps are running on the same server, but using different databases.")
print("Navigate to /cdb/ URLs to use the new CDB app with improved schema.")
print("\nPress Ctrl+C to stop the server.\n")

# Execute Django's runserver command
cmd = [sys.executable, "manage.py", "runserver", port]
subprocess.run(cmd)

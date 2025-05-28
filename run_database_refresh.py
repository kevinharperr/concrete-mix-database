import os
import sys
import subprocess
import time
from datetime import datetime

# Define the script paths
RESET_SCRIPT = 'reset_database.py'
IMPORT_SCRIPT = 'sequential_import.py'

# Function to execute a script and capture output
def run_script(script_path, auto_confirm=False):
    print(f"\n===== Running {script_path} =====")
    
    if auto_confirm:
        # For scripts that require confirmation, pipe in 'yes'
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        stdout, _ = process.communicate(input='yes\n')
    else:
        # For scripts that don't require confirmation
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        stdout, _ = process.communicate()
    
    # Print the output
    print(stdout)
    
    return process.returncode == 0

# Main refresh process
def run_database_refresh():
    start_time = datetime.now()
    print(f"Database refresh process started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis process will reset the database and import fresh data.")
    print("Make sure the system is already in maintenance mode!")
    
    # Confirm before proceeding
    confirm = input("\nAre you sure you want to proceed with the database refresh? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Database refresh cancelled.")
        return False
    
    # Step 1: Reset Database
    print("\n\n==== STEP 1: RESETTING DATABASE =====")
    reset_success = run_script(RESET_SCRIPT, auto_confirm=True)
    if not reset_success:
        print("ERROR: Database reset failed! Stopping the refresh process.")
        return False
    
    # Step 2: Import Data
    print("\n\n==== STEP 2: IMPORTING DATA =====")
    import_success = run_script(IMPORT_SCRIPT, auto_confirm=True)
    if not import_success:
        print("ERROR: Data import failed! The database has been reset but import failed.")
        print("Please check the logs and correct any issues before retrying.")
        return False
    
    # Step 3: Update System Status
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n\n==== DATABASE REFRESH COMPLETED SUCCESSFULLY =====")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total duration: {duration}")
    print("\nNext steps:")
    print("1. Verify the imported data through the admin interface")
    print("2. Deactivate maintenance mode when ready")
    print("3. Update documentation with the refresh results")
    
    return True

if __name__ == '__main__':
    run_database_refresh()

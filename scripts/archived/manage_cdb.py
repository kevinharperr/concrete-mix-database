#!/usr/bin/env python
"""
Utility script for managing the CDB application specifically.
This provides a way to run Django commands with explicit database targeting.
"""
import os
import sys
import subprocess

def main():
    """Run Django management commands with appropriate settings for CDB app."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
    
    # Print banner
    print("\n====== CDB App Management Script ======")
    print("This script helps manage commands specifically for the CDB app")
    print("===========================================\n")
    
    if len(sys.argv) < 2:
        print("Usage: python manage_cdb.py <command> [options]")
        print("\nCommon commands:")
        print("  runserver - Start the development server")
        print("  makemigrations cdb_app - Create migrations for cdb_app")
        print("  migrate cdb_app - Apply migrations for cdb_app to the 'cdb' database")
        print("  shell - Start a Django shell")
        print("\nNote: Commands will be properly routed to the 'cdb' database when needed")
        return
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    # Prepare the base command
    django_command = [sys.executable, 'manage.py', command]
    
    # Add special handling for specific commands
    if command == 'migrate' and len(args) > 0 and args[0] == 'cdb_app':
        # Explicitly specify the database for cdb_app migrations
        django_command.extend(args)
        django_command.extend(['--database=cdb'])
    elif command == 'makemigrations' and len(args) > 0 and args[0] == 'cdb_app':
        # For makemigrations, pass through the app name
        django_command.extend(args)
    elif command == 'shell':
        # For shell, pass all args
        django_command.extend(args)
        print("Note: In the shell, use Model.objects.using('cdb').all() to query CDB models")
    else:
        # For other commands, just pass all arguments
        django_command.extend(args)
    
    # Execute the command
    print(f"Running: {' '.join(django_command)}\n")
    subprocess.run(django_command)

if __name__ == '__main__':
    main()

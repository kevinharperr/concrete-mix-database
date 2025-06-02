#!/usr/bin/env python
"""
Database restoration utility for the Concrete Mix Database.

This script helps restore a database dump that has been shared by a colleague.
It guides the user through the process of creating a new database and importing the dump.
"""
import os
import sys
import subprocess
import argparse

def get_input(prompt, default=None):
    """Get input from user with optional default value."""
    if default:
        result = input(f"{prompt} [{default}]: ").strip()
        return result if result else default
    else:
        return input(f"{prompt}: ").strip()

def restore_database(dump_file, db_name, username, password, host, port):
    """Restore database from a dump file."""
    # Determine if this is a binary or SQL dump
    is_binary = dump_file.lower().endswith('.backup')
    
    # Set environment variables for PostgreSQL
    pg_env = os.environ.copy()
    pg_env['PGPASSWORD'] = password
    
    try:
        # Check if database exists
        check_cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', username,
            '-lqt'
        ]
        process = subprocess.Popen(check_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        db_exists = db_name in stdout.decode()
        
        if not db_exists:
            print(f"Creating database '{db_name}'...")
            create_cmd = [
                'psql',
                '-h', host,
                '-p', port,
                '-U', username,
                '-c', f"CREATE DATABASE {db_name};"
            ]
            process = subprocess.Popen(create_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"Error creating database: {stderr.decode()}")
                return False
        else:
            print(f"Database '{db_name}' already exists.")
            proceed = get_input("Do you want to drop and recreate it? (y/n)", "n")
            if proceed.lower() == 'y':
                drop_cmd = [
                    'psql',
                    '-h', host,
                    '-p', port,
                    '-U', username,
                    '-c', f"DROP DATABASE {db_name};"
                ]
                process = subprocess.Popen(drop_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    print(f"Error dropping database: {stderr.decode()}")
                    return False
                
                create_cmd = [
                    'psql',
                    '-h', host,
                    '-p', port,
                    '-U', username,
                    '-c', f"CREATE DATABASE {db_name};"
                ]
                process = subprocess.Popen(create_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    print(f"Error creating database: {stderr.decode()}")
                    return False
            else:
                print("Will attempt to restore over the existing database.")
        
        # Restore database
        print(f"Restoring database from {dump_file}...")
        if is_binary:
            # Use pg_restore for binary format
            restore_cmd = [
                'pg_restore',
                '-h', host,
                '-p', port,
                '-U', username,
                '-d', db_name,
                '-v',  # Verbose mode
                dump_file
            ]
        else:
            # Use psql for SQL format
            restore_cmd = [
                'psql',
                '-h', host,
                '-p', port,
                '-U', username,
                '-d', db_name,
                '-f', dump_file
            ]
        
        process = subprocess.Popen(restore_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"Warning: Restore completed with non-zero exit code: {process.returncode}")
            print(f"This might be due to non-critical errors or warnings.")
            print(f"Error details: {stderr.decode()}")
        
        print("Database restoration completed successfully.")
        
        # Test the database connection
        test_cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', username,
            '-d', db_name,
            '-c', "SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';"
        ]
        process = subprocess.Popen(test_cmd, env=pg_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print(f"Database connection test successful.")
            print(f"The database contains tables: {stdout.decode()}")
            return True
        else:
            print(f"Warning: Database connection test failed: {stderr.decode()}")
            return False
    
    except Exception as e:
        print(f"Error during database restoration: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Restore Concrete Mix Database from dump file')
    parser.add_argument('--dump', help='Path to database dump file (.sql or .backup)')
    parser.add_argument('--db-name', help='Database name to restore to')
    parser.add_argument('--username', help='PostgreSQL username')
    parser.add_argument('--password', help='PostgreSQL password')
    parser.add_argument('--host', help='PostgreSQL host')
    parser.add_argument('--port', help='PostgreSQL port')
    
    args = parser.parse_args()
    
    print("\nConcrete Mix Database Restoration Utility\n" + "=" * 40)
    
    # Get parameters from user if not provided as arguments
    dump_file = args.dump or get_input("Path to database dump file (.sql or .backup)")
    if not os.path.exists(dump_file):
        print(f"Error: Dump file '{dump_file}' does not exist.")
        return
    
    db_name = args.db_name or get_input("Database name to restore to", "cdb")
    username = args.username or get_input("PostgreSQL username", "postgres")
    password = args.password or get_input("PostgreSQL password")
    host = args.host or get_input("PostgreSQL host", "localhost")
    port = args.port or get_input("PostgreSQL port", "5432")
    
    success = restore_database(dump_file, db_name, username, password, host, port)
    
    if success:
        print("\nDatabase restoration completed.")
        print("\nNext steps:")
        print("1. Update the Django settings.py file with your database connection details")
        print("2. Run 'python manage.py check' to verify the database connection")
        print("3. Start the Django development server with 'python manage.py runserver'")
    else:
        print("\nDatabase restoration failed. Please check the error messages above.")

if __name__ == "__main__":
    main()

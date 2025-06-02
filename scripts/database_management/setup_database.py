import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'concrete_mix_project.settings')
django.setup()

import psycopg2
from django.conf import settings
from django.db import connection

def setup_database_tables():
    """Create the necessary database tables for the refresh status app."""
    print("Setting up database tables for refresh status app...")
    
    # SQL to create the basic tables we need
    sql_commands = [
        # Create the DatabaseStatus table
        """
        CREATE TABLE IF NOT EXISTS refresh_status_databasestatus (
            id SERIAL PRIMARY KEY,
            status VARCHAR(20) NOT NULL,
            read_only_mode VARCHAR(10) NOT NULL,
            current_phase VARCHAR(100),
            current_step VARCHAR(100),
            progress_percentage INTEGER,
            maintenance_message TEXT,
            start_time TIMESTAMP WITH TIME ZONE,
            end_time TIMESTAMP WITH TIME ZONE,
            estimated_completion TIMESTAMP WITH TIME ZONE,
            last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
        """,
        
        # Create the StatusNotification table
        """
        CREATE TABLE IF NOT EXISTS refresh_status_statusnotification (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL,
            notification_type VARCHAR(20) NOT NULL,
            is_active BOOLEAN NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            start_display TIMESTAMP WITH TIME ZONE,
            end_display TIMESTAMP WITH TIME ZONE,
            display_order INTEGER NOT NULL,
            dismissible BOOLEAN NOT NULL,
            display_on_all_pages BOOLEAN NOT NULL,
            specific_pages TEXT,
            user_id INTEGER NULL
        )
        """,
        
        # Create the RefreshLogEntry table
        """
        CREATE TABLE IF NOT EXISTS refresh_status_refreshlogentry (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            phase VARCHAR(100),
            step VARCHAR(100),
            status VARCHAR(50),
            message TEXT,
            is_error BOOLEAN NOT NULL,
            details JSONB
        )
        """,
        
        # Insert a default database status
        """
        INSERT INTO refresh_status_databasestatus (id, status, read_only_mode, progress_percentage)
        VALUES (1, 'idle', 'off', 0)
        ON CONFLICT (id) DO NOTHING
        """
    ]
    
    # Connect to database and execute SQL
    with connection.cursor() as cursor:
        for sql in sql_commands:
            try:
                cursor.execute(sql)
                print(f"Successfully executed: {sql[:50]}...")
            except Exception as e:
                print(f"Error executing: {sql[:50]}...: {str(e)}")

if __name__ == "__main__":
    setup_database_tables()
    print("Database setup complete!")

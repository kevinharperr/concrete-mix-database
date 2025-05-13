import psycopg2
import sys

def migrate_django_tables():
    print("Starting migration of Django system tables...")
    
    # Connect to source database
    try:
        conn_source = psycopg2.connect(
            dbname='concrete_mix_db',
            user='postgres',
            password='264537',
            host='localhost',
            port='5432'
        )
        print("Connected to source database 'concrete_mix_db'")
    except Exception as e:
        print(f"Error connecting to source database: {e}")
        return
    
    # Connect to target database
    try:
        conn_target = psycopg2.connect(
            dbname='cdb',
            user='postgres',
            password='264537',
            host='localhost',
            port='5432'
        )
        print("Connected to target database 'cdb'")
    except Exception as e:
        print(f"Error connecting to target database: {e}")
        conn_source.close()
        return
    
    cur_source = conn_source.cursor()
    cur_target = conn_target.cursor()
    
    # Django tables to migrate
    django_tables = [
        'django_session',
        'django_content_type',
        'django_admin_log',
        'django_migrations',
        'auth_user',
        'auth_group',
        'auth_permission',
        'auth_group_permissions',
        'auth_user_groups',
        'auth_user_user_permissions',
    ]
    
    for table in django_tables:
        print(f"\nProcessing {table}...")
        
        # Check if table exists in source database
        cur_source.execute(f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)", (table,))
        if not cur_source.fetchone()[0]:
            print(f"Table {table} doesn't exist in source database, skipping")
            continue
            
        # Check if table already exists in target database
        cur_target.execute(f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)", (table,))
        table_exists = cur_target.fetchone()[0]
        
        if table_exists:
            print(f"Table {table} already exists in target database, dropping it")
            try:
                cur_target.execute(f"DROP TABLE {table} CASCADE;")
                conn_target.commit()
            except Exception as e:
                print(f"Error dropping {table}: {e}")
                conn_target.rollback()
                continue
        
        # Get table schema
        try:
            cur_source.execute(f"""
                SELECT 
                    column_name, 
                    data_type, 
                    character_maximum_length, 
                    column_default, 
                    is_nullable 
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """, (table,))
            columns = cur_source.fetchall()
            
            if not columns:
                print(f"No columns found for {table}, skipping")
                continue
                
            # Create table in target db
            columns_def = []
            for col in columns:
                col_name = col[0]
                col_type = col[1]
                col_len = col[2]
                col_default = col[3]
                col_nullable = col[4]
                
                # Format the type with length if applicable
                type_with_len = col_type
                if col_len is not None:
                    type_with_len = f"{col_type}({col_len})"
                
                # Handle nullable
                nullable = "NULL" if col_nullable == 'YES' else "NOT NULL"
                
                # Handle default value
                default = f" DEFAULT {col_default}" if col_default is not None else ""
                
                columns_def.append(f"{col_name} {type_with_len} {nullable}{default}")
            
            create_stmt = f"CREATE TABLE {table} (" + ", ".join(columns_def) + ");"
            print(f"Creating table with schema: {create_stmt[:100]}...")
            cur_target.execute(create_stmt)
            conn_target.commit()
            print(f"Table {table} created successfully")
            
            # Get constraints and indexes
            # We'll skip this for simplicity, but in a production migration you would want to recreate these
            
            # Copy data from source to target
            cur_source.execute(f"SELECT * FROM {table};")
            rows = cur_source.fetchall()
            
            if rows:
                print(f"Copying {len(rows)} rows to {table}...")
                for row in rows:
                    placeholders = ", ".join("%s" for _ in range(len(row)))
                    insert_stmt = f"INSERT INTO {table} VALUES ({placeholders});"
                    cur_target.execute(insert_stmt, row)
                conn_target.commit()
                print(f"Data copied to {table} successfully")
            else:
                print(f"No data to copy for {table}")
                
        except Exception as e:
            print(f"Error processing {table}: {e}")
            conn_target.rollback()
    
    # Close connections
    conn_source.close()
    conn_target.close()
    print("\nMigration complete!")

if __name__ == "__main__":
    migrate_django_tables()

import os
import psycopg2
import gzip
import re


def export_database(conn, schema_name):
    # Get a list of tables in the schema
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %(schema_name)s;
            """,
            {'schema_name': schema_name}
        )
        tables = [table[0] for table in cursor.fetchall()]

    exported_files = {}
    exported_ddls = {}
    for table in tables:
        with conn.cursor() as ddl_cursor:
            ddl_cursor.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = %(schema_name)s
                AND table_name = %(table)s;
                """,
                {'schema_name': schema_name, 'table': table}
            )
            columns = ddl_cursor.fetchall()
            ddl = f"CREATE TABLE {schema_name}.{table} (\n"
            for column in columns:
                column_ddl = f"{column[0]} {column[1]}"
                if column[2] == 'YES':
                    column_ddl += " NULL"
                else:
                    column_ddl += " NOT NULL"
                if column[3]:
                    column_ddl += f" DEFAULT {column[3]}"
                ddl += f"    {column_ddl},\n"
            ddl = ddl.rstrip(",\n")
            ddl += "\n)"
            exported_ddls[table] = ddl

        query = f"COPY {schema_name}.{table} TO STDOUT WITH CSV"

        with conn.cursor() as cursor:
            try:
                filename = f"{schema_name}.{table}.csv.gz"
                full_path = os.path.join(os.getcwd(), filename)
                with gzip.open(full_path, "wb") as export_file:
                    cursor.copy_expert(query, export_file)
                exported_files[table] = full_path
            except Exception as e:
                print(f"Error exporting table {table}: {e}")
                continue

    return exported_files, exported_ddls


def delete_exported_files(exported_files, schema_name):
    for table, file_path in exported_files.items():
        try:
            os.remove(file_path)
            print(f"Deleted {file_path}")
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")


def export_functions(conn, schema_name):
    print("Executing export function query...")
    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT pg_get_functiondef(p.oid) as function_definition,
                   p.proname as function_name,
                   n.nspname as schema_name,
                   array_agg(d.depname) as dependencies
            FROM pg_catalog.pg_proc p
            LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            LEFT JOIN (
                SELECT p.oid, p.proname depname
                FROM pg_catalog.pg_proc p
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            ) d ON position(d.depname in pg_get_functiondef(p.oid)) > 0
            WHERE n.nspname = '{schema_name}' OR n.nspname = 'public'
            GROUP BY p.oid, p.proname, n.nspname;
            """
        )
        functions = cursor.fetchall()

    return functions


def create_function_stub(conn, function_def, function_name, schema_name):
    try:
        signature = re.search(r"CREATE (OR REPLACE )?FUNCTION (.*?)\s*\((.*?)\)\s+RETURNS\s+(.+?)\s+(?:AS|LANGUAGE)",
                              function_def, flags=re.IGNORECASE)
        if signature:
            schema_function_name = f"{schema_name}.{function_name}"

            # Get the actual return type of the function
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT pg_catalog.pg_get_function_result(pg_proc.oid) FROM pg_catalog.pg_namespace JOIN pg_catalog.pg_proc ON pronamespace = pg_namespace.oid WHERE nspname = '{schema_name}' AND proname = '{function_name}'")
                actual_return_type = cursor.fetchone()[0]

            # Drop the existing function first
            delete_query = f"DROP FUNCTION IF EXISTS {schema_function_name}({signature.group(3)}) CASCADE;"
            with conn.cursor() as cursor:
                cursor.execute(delete_query)

            # Create the function stub with the correct return type
            function_stub = f"CREATE OR REPLACE FUNCTION {schema_function_name}({signature.group(3)}) RETURNS {actual_return_type} LANGUAGE sql AS $$SELECT NULL::{actual_return_type};$$"
            with conn.cursor() as cursor:
                cursor.execute(function_stub)

            conn.commit()

            print(f"Function stub for {schema_function_name} created successfully.")
        else:
            raise Exception("Unable to extract function signature")
    except Exception as e:
        print(f"Error creating function stub for {schema_name}.{function_name}: {e}")
        conn.rollback()


def import_functions(conn, functions):
    def import_function(function_def, function_name, schema_name):
        with conn.cursor() as cursor:
            try:
                cursor.execute(function_def)
                conn.commit()
                print(f"Function imported successfully: {schema_name}.{function_name}")
            except Exception as e:
                if "return type mismatch" in str(e) or "cannot change return type of existing function" in str(e):
                    signature = re.search(
                        r"CREATE (OR REPLACE )?FUNCTION (.*?)\s*\((.*?)\)\s+RETURNS\s+(.+?)\s+(?:AS|LANGUAGE)",
                        function_def, flags=re.IGNORECASE)
                    if signature:
                        schema_function_name = f"{schema_name}.{function_name}"
                        delete_query = f"DROP FUNCTION IF EXISTS {schema_function_name}({signature.group(3)}) CASCADE;"
                        cursor.execute("ROLLBACK TO savepoint_before_function;")
                        cursor.execute(delete_query)
                        conn.commit()
                        print(f"Deleted function with return type mismatch: {schema_name}.{function_name}")
                        import_function(function_def, function_name, schema_name)
                    else:
                        print(f"Error importing function {schema_name}.{function_name}: {e}")
                        conn.rollback()
                else:
                    print(f"Error importing function {schema_name}.{function_name}: {e}")
                    conn.rollback()

    for function_def, function_name, schema_name, _ in functions:
        with conn.cursor() as cursor:
            cursor.execute("SAVEPOINT savepoint_before_function;")
        import_function(function_def, function_name, schema_name)


def import_schema(conn, schema_name, exported_ddls, copy_data=True, exported_files=None):
    with conn.cursor() as cursor:
        # Drop the schema if it exists
        cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")

        # Create the schema
        cursor.execute(f"CREATE SCHEMA {schema_name}")

        # Import each table and its data (if copy_data is True) into the target database
        for table, ddl in exported_ddls.items():
            try:
                print(f"Importing table {table}")
                # Create table structure
                cursor.execute(ddl)

                # Import data if copy_data is True
                if copy_data and exported_files:
                    file_path = exported_files[table]
                    with gzip.open(file_path, "rt", encoding="utf-8") as import_file:
                        cursor.copy_expert(f"COPY {schema_name}.{table} FROM STDIN WITH CSV", import_file)

            except Exception as e:
                print(f"Error importing table {table}: {e}")
                conn.rollback()  # Rollback the transaction in case of errors
                continue
            else:
                print(f"Table {table} imported successfully")
                conn.commit()  # Commit the transaction after each table is imported


def call_grant_privileges_function(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT grant_priviledges();")
        conn.commit()


def check_databases_equal(conn1, conn2, schema_name):
    def compare_objects(conn1, conn2, object_type, query, object_name, delete_missing=False):
        with conn1.cursor() as cursor1, conn2.cursor() as cursor2:
            cursor1.execute(query, (schema_name,))
            cursor2.execute(query, (schema_name,))

            objects1 = set(cursor1.fetchall())
            objects2 = set(cursor2.fetchall())

            missing_in_conn2 = objects1 - objects2
            missing_in_conn1 = objects2 - objects1

            if missing_in_conn2 or missing_in_conn1:
                print(f"{object_type} are not equal:")
                if missing_in_conn2:
                    print(f"Missing in conn2:")
                    for obj in missing_in_conn2:
                        print(".".join(obj))
                if missing_in_conn1:
                    print(f"Missing in conn1:")
                    for obj in missing_in_conn1:
                        print(".".join(obj))
                        if delete_missing:
                            cursor2.execute(f"DROP FUNCTION {obj[0]}.{obj[1]};")
                            conn2.commit()
                return False

            return True

    tables_query = """
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        ORDER BY table_name;
    """

    functions_query = """
        SELECT nspname, proname, pg_get_functiondef(p.oid)
        FROM pg_proc p
        JOIN pg_namespace ns ON ns.oid = p.pronamespace
        WHERE ns.nspname IN (%s, 'public')
        ORDER BY proname;
    """

    tables_equal = compare_objects(conn1, conn2, "Tables", tables_query, "table_name")
    functions_equal = compare_objects(conn1, conn2, "Functions", functions_query, "function_name", delete_missing=True)

    return tables_equal and functions_equal



def main():
    # Source database information
    # You can get this from your Supabase project settings, Database tab
    src_db_host = "db.vcdvwqctfziufzhvmsti.supabase.co"
    src_db_name = "postgres"
    src_db_port = "5432"
    src_db_user = "postgres"
    src_db_password = "<sourcePassword>"

    # Target database information
    # You can get this from your Supabase project settings, Database tab
    target_db_host = "db.gwpcsfqcwydetmafihsq.supabase.co"
    target_db_name = "postgres"
    target_db_port = "5432"
    target_db_user = "postgres"
    target_db_password = "<targetPassword>"

    # Connect to the source database
    src_conn = psycopg2.connect(
        host=src_db_host,
        port=src_db_port,
        dbname=src_db_name,
        user=src_db_user,
        password=src_db_password
    )

    # Connect to the target database
    target_conn = psycopg2.connect(
        host=target_db_host,
        port=target_db_port,
        dbname=target_db_name,
        user=target_db_user,
        password=target_db_password

    )

    # Export the schema and data from the source database
    schema_name = "ad"

    # Set copy_data according to your preference
    # When it is False, it will not copy the data ONLY schema and functions
    copy_data = False

    exported_files, exported_ddls = export_database(src_conn, schema_name)

    # Export the functions from the source database
    exported_functions = export_functions(src_conn, schema_name)

    # Import the exported schema and its data (if copy_data is True) into the target database
    import_schema(target_conn, schema_name, exported_ddls, copy_data=copy_data,
                  exported_files=exported_files if copy_data else None)

    # First pass: Create function stubs in the target database
    for function_def, function_name, s_name, _ in exported_functions:
        create_function_stub(target_conn, function_def, function_name, s_name)

    # Second pass: Import the functions into the target database
    import_functions(target_conn, exported_functions)

    # Call the grant_privileges function in the target database
    call_grant_privileges_function(target_conn)

    # Delete the exported .gz files
    delete_exported_files(exported_files, schema_name)

    print("Checking if the databases are equal...")
    equal = check_databases_equal(src_conn, target_conn, schema_name)
    if equal:
        print("Databases are equal.")
    else:
        print("Databases are not equal.")

    # Close the connections
    src_conn.close()
    target_conn.close()


if __name__ == "__main__":
    main()

import psycopg2
from psycopg2.extras import RealDictCursor

# PostgreSQL connection
def create_connection(db_url):
    try:
        connection = psycopg2.connect(db_url)
        
        # connection = psycopg2.connect(
        #     dbname="postgres",        # nome do banco
        #     user="user",        # usuário
        #     password="secret",      # senha
        #     host="db",          # ou IP do servidor
        #     port="5432"                # porta padrão do Postgres
        # )

        # Cursor que retorna dicts em vez de tuplas (similar ao row_factory do sqlite3)
        connection.cursor_factory = RealDictCursor
        print("PostgreSQL connection was successful!")
        return connection

    except psycopg2.Error as e:
        print(f"PostgreSQL connection error: {e}")
        return None
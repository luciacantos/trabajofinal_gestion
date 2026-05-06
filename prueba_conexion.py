import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

print("Iniciando prueba de conexión...")

usuario = "postgres"
password = "mimosa060401"
host = "localhost"
puerto = 5432
base_datos = "trabajo_final"

try:
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=usuario,
        password=password,
        host=host,
        port=puerto,
        database=base_datos
    )

    engine = create_engine(url)

    consulta = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
    ORDER BY table_name;
    """

    tablas = pd.read_sql(consulta, engine)

    print("Conexión correcta.")
    print("Tablas encontradas:")
    print(tablas)

except Exception as e:
    print("Error al conectar con PostgreSQL:")
    print(e)
# IMPORTACIONES

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from getpass import getpass
import os
from sqlalchemy import text

print("Iniciando ETL...")

# DATOS DE CONEXIÓN
usuario = "postgres"
password = getpass("Introduce la contraseña de PostgreSQL: ")
host = "localhost"
puerto = 5432
base_datos = "trabajo_final"

# PROCESO ETL
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

    consulta_tablas = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE'
    ORDER BY table_name;
    """

    tablas = pd.read_sql(consulta_tablas, engine)["table_name"].tolist()

    print("Conexión correcta.")
    print(f"Tablas encontradas: {len(tablas)}")
    print(tablas)

    datos = {}

    print("\n" + "=" * 60)
    print("EXTRACCIÓN DE TABLAS")
    print("=" * 60)

    datos = {}

    # Extraer datos de cada tabla y mostrar información básica

    for tabla in tablas:
        consulta = f'SELECT * FROM public."{tabla}"'
        datos[tabla] = pd.read_sql(consulta, engine)

        print("-" * 60)
        print(f"Tabla: {tabla}")
        print(f"Filas: {datos[tabla].shape[0]}")
        print(f"Columnas: {datos[tabla].shape[1]}")
        print("-" * 60)

    
    print("\nPaso 1 completado: datos extraídos correctamente.")

except Exception as e:
    print("Error en el proceso ETL:")
    print(e)



print("\n" + "=" * 60)
print("PASO 2 - REVISIÓN INICIAL DE LOS DATOS")
print("=" * 60)

for tabla, df in datos.items():
    print("-" * 60)
    print(f"Tabla: {tabla}")
    print(f"Filas: {df.shape[0]}")
    print(f"Columnas: {df.shape[1]}")
    print(f"Valores nulos totales: {df.isnull().sum().sum()}")
    print(f"Filas duplicadas: {df.duplicated().sum()}")

    print("\nColumnas:")
    print(list(df.columns))

    print("\nTipos de datos:")
    print(df.dtypes)

    print("-" * 60)

print("\nPaso 2 completado: revisión inicial realizada.")

    
print("\n" + "=" * 60)
print("PASO 3 - LIMPIEZA Y TRANSFORMACIÓN")
print("=" * 60)

datos_limpios = {}

for tabla, df in datos.items():
    df_limpio = df.copy()

    filas_antes = df_limpio.shape[0]

    # Eliminar duplicados
    df_limpio = df_limpio.drop_duplicates()

    # Limpiar nombres de columnas
    df_limpio.columns = df_limpio.columns.str.strip().str.lower()

    # Limpiar columnas de texto
    columnas_texto = df_limpio.select_dtypes(include=["object"]).columns

    for columna in columnas_texto:
        df_limpio[columna] = df_limpio[columna].astype(str).str.strip()
        df_limpio[columna] = df_limpio[columna].replace(
            ["", "nan", "None", "NULL"],
            pd.NA
        )

        # Convertir fechas
    for columna in df_limpio.columns:
        if "date" in columna or "_at" in columna or "last_update" in columna:
            df_limpio[columna] = pd.to_datetime(df_limpio[columna], errors="coerce")

    filas_despues = df_limpio.shape[0]

    datos_limpios[tabla] = df_limpio

    print(f"{tabla}: {filas_antes - filas_despues} duplicados eliminados")

    # Tratamiento específico de valores nulos encontrados

if "brand" in datos_limpios:
    datos_limpios["brand"] = datos_limpios["brand"].fillna("Desconocido")
    print("brand: valores nulos sustituidos por 'Desconocido'")

if "city_zone" in datos_limpios:
    datos_limpios["city_zone"] = datos_limpios["city_zone"].fillna("Desconocido")
    print("city_zone: valores nulos sustituidos por 'Desconocido'")

if "sale_item" in datos_limpios:
    datos_limpios["sale_item"]["tiene_oferta"] = datos_limpios["sale_item"]["offer_id"].notna()
    datos_limpios["sale_item"]["offer_id"] = datos_limpios["sale_item"]["offer_id"].fillna(0).astype(int)
    print("sale_item: offer_id nulo convertido a 0 para indicar venta sin oferta")

print("\nRevisión después de la transformación:")

for tabla, df in datos_limpios.items():
    print("-" * 60)
    print(f"Tabla: {tabla}")
    print(f"Valores nulos restantes: {df.isnull().sum().sum()}")
    print(f"Filas duplicadas restantes: {df.duplicated().sum()}")

print("\nPaso 3 completado: datos limpiados y transformados.")


print("\n" + "=" * 60)
print("PASO 4 - CARGA DE DATOS LIMPIOS")
print("=" * 60)

carpeta_salida = "datos_limpios"
os.makedirs(carpeta_salida, exist_ok=True)

# Guardar cada tabla limpia en un CSV
for tabla, df in datos_limpios.items():
    ruta_csv = f"{carpeta_salida}/{tabla}_limpia.csv"
    df.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    print(f"CSV generado: {ruta_csv}")

# Guardar todas las tablas en un único Excel
ruta_excel = f"{carpeta_salida}/datos_limpios.xlsx"

with pd.ExcelWriter(ruta_excel) as writer:
    for tabla, df in datos_limpios.items():
        df.to_excel(writer, sheet_name=tabla[:31], index=False)

print(f"\nExcel generado: {ruta_excel}")
print("\nPaso 4 completado: datos limpios cargados correctamente.")




print("\n" + "=" * 60)
print("PASO 5 - CARGA DE TABLAS LIMPIAS EN POSTGRESQL")
print("=" * 60)

try:
    # Crear esquema staging si no existe
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging;"))

    print("Esquema staging creado o ya existente.")

    # Cargar cada DataFrame limpio en PostgreSQL
    for tabla, df in datos_limpios.items():
        nombre_tabla_staging = f"{tabla}_limpia"

        df.to_sql(
            name=nombre_tabla_staging,
            con=engine,
            schema="staging",
            if_exists="replace",
            index=False,
            chunksize=1000,
            method="multi"
        )

        print(f"Tabla cargada en PostgreSQL: staging.{nombre_tabla_staging} | Filas: {len(df)}")

    print("\nPaso 5 completado: tablas limpias cargadas en PostgreSQL correctamente.")

except Exception as e:
    print("Error al cargar las tablas limpias en PostgreSQL:")
    print(e)
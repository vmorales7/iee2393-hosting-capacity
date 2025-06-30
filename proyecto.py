from modulo_pf import ejecutar_pf

print("--- Iniciando mi análisis del proyecto ---")

# --- Escenario 1 de ejemplo: Demanda de 150 kW, SÍ guardamos el gráfico ---
print("\n--- Analizando Escenario 1: 150 kW ---")
df_cargas_1 = ejecutar_pf(
    demanda_neta_kw=150, 
    nombre_archivo_salida="caso_150kW" # Le damos un nombre, por lo tanto, SÍ se guarda
)

# Analizamos los resultados del Escenario 1
if not df_cargas_1.empty:
    print("\nResultados del Escenario 1:")
else:
    print("La simulación del Escenario 1 no fue exitosa.")


# --- Escenario 2 de ejemplo: Demanda de 250 kW, NO guardamos el gráfico ---
print("\n--- Analizando Escenario 2: 250 kW ---")
df_cargas_2 = ejecutar_pf(
    demanda_neta_kw=250 # Le pasamos None, por lo tanto, NO se guarda
)

# Analizamos los resultados del Escenario 2
if not df_cargas_2.empty:
    print("\nResultados del Escenario 2:")
    # Encontrar y mostrar las 3 líneas más cargadas
    print("Las 3 líneas más cargadas fueron:")
    print(df_cargas_2.sort_values(by="loading_percent", ascending=False).head(3))
else:
    print("La simulación del Escenario 2 no fue exitosa.")

print("\n--- Análisis finalizado ---")
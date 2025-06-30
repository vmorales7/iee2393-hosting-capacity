# %% -------------------- Parámetros del proyecto ---------------------
# Seleccionar caso de estudio:
case = "all"  # "base", "pv", "pv + bess", "ev", "ev + bess", "all"

# Librerías necesarias
from modulo_pf import ejecutar_pf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import funciones as f
import os

# Crear carpeta de resultados si no existe
if not os.path.exists("Resultados"):
    os.makedirs("Resultados")

# Datos de entrada
perfil_demanda_kw = [
    65, 65, 65, 74, 75, 80, 100, 148, 148, 148, 148, 148,
    133, 123, 123, 123, 123, 148, 148, 148, 246, 246, 148, 74
]
perfil_pv_pu = [
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05, 0.05, 0.2, 0.35, 0.6, 0.8,
    0.95, 1.0, 0.9, 0.4, 0.2, 0.1, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0
]
perfil_ev_pu = [
    0.6, 0.7, 0.8, 0.7, 0.6, 0.5, 0.5, 0.4, 0.1, 0.1, 0.1, 0.1,
    0.1, 0.2, 0.2, 0.2, 0.2, 0.6, 0.7, 1.0, 1.0, 0.9, 0.7, 0.7
]
perfil_costo = [
    100, 100, 100,   # 00:00 - 02:59 → Punta
    50, 50, 50, 50,  # 03:00 - 06:59 → Valle
    100, 100, 100, 100,  # 07:00 - 10:59 → Punta
    50, 50, 50, 50, 50, 50,  # 11:00 - 16:59 → Valle
    100, 100, 100, 100, 100, 100, 100  # 17:00 - 23:59 → Punta
]

parametros_bess = {
    "E_MAX": 900,     # Capacidad máxima en kWh
    "E_MIN": 0,       # Capacidad mínima en kWh
    "E_INI": 5,       # Estado de carga inicial en kWh
    "P_MAX": 150,     # Potencia máxima de carga/descarga en kW
    "ETA_C": 1.0,     # Eficiencia de carga
    "ETA_D": 1.0,     # Eficiencia de descarga
    "C_DEG": 15       # Costo de degradación en $/kW
}

# Será útil convertir los perfiles a arrays de NumPy para facilitar cálculos
perfil_demanda_kw = np.array(perfil_demanda_kw)
perfil_pv_pu = np.array(perfil_pv_pu)
perfil_ev_pu = np.array(perfil_ev_pu)
perfil_costo = np.array(perfil_costo)


# %% -------------------- Caso base ---------------------
if case in ["base", "all"]:
    print("\n---------- Analizando caso base ----------")

    # No se considera EV, PV ni BESS en el caso base
    perfil_neto_kw = perfil_demanda_kw

    # Ejecutar flujo de potencia para cada hora y graficar
    df, hora_max, carga_max, linea_max = f.loading_por_hora(perfil_neto_kw)
    f.graficar_carga_por_linea(df, "Resultados/base_perfil_lineas", perfil_demanda_kw)

    # Corremos el flujo para el caso máximo y generamos la figura de lineas
    df_resultado_critico = ejecutar_pf(perfil_neto_kw[hora_max], f"Resultados/base_hora{hora_max}")

    print("---------- Caso base finalizado ----------")


# %% -------------------- Hosting capacity: PV ---------------------
if case in ["pv", "all"]:
    print("\n---------- Analizando: Hosting Capacity PV ----------")

    # En este caso hay que considerar una cierta capacidad instalada de PV, steps de 10kW                       
    perfil_pv_kw = perfil_pv_pu * 800 
    perfil_neto_kw = perfil_demanda_kw - perfil_pv_kw

    # Ejecutar flujo de potencia para cada hora y graficar
    df, hora_max, carga_max, linea_max = f.loading_por_hora(perfil_neto_kw)
    f.graficar_carga_por_linea(
        df_loading_por_hora=df,
        nombre_archivo="Resultados/pv_perfil_lineas",
        perfil_demanda_kw=perfil_demanda_kw,
        perfil_neto_kw=perfil_neto_kw,
        perfil_pv_kw=perfil_pv_kw
    )

    # Corremos el flujo para el caso máximo y generamos la figura de lineas
    print(f"Hosting Capacity PV: {perfil_pv_kw.max()} kW")
    df_resultado_critico = ejecutar_pf(perfil_neto_kw[hora_max], f"Resultados/pv_hora{hora_max}")

    print("---------- Finalizado: Hosting Capacity PV ----------")


# %% -------------------- Hosting capacity: PV + BESS ---------------------
if case in ["pv + bess", "all"]:
    print("\n---------- Analizando: Hosting Capacity PV + BESS ----------")

    # Capacidad de PV encontrada en etapa de HC (revisar si está correcto)
    perfil_pv_kw = perfil_pv_pu * 800 

    # Resolver optimización del despacho BESS
    df_bess, perfil_bess_kw = f.resolver_despacho_bess(
        parametros_bess=parametros_bess,
        perfil_costo=perfil_costo,
        perfil_demanda_kw=perfil_demanda_kw,
        perfil_pv_kw=perfil_pv_kw,
        perfil_ev_kw=None        
    )
    
    # Se grafica el despacho de BESS
    perfil_neto_kw = perfil_demanda_kw - perfil_pv_kw + perfil_bess_kw
    f.graficar_perfiles_horarios(
        perfil_demanda_kw=perfil_demanda_kw,
        perfil_neto_kw=perfil_neto_kw,
        perfil_pv_kw=perfil_pv_kw,
        perfil_bess_kw=perfil_bess_kw,
        perfil_costo=perfil_costo,
        nombre_archivo="Resultados/pv_bess_perfiles"
    )

    # Volver a probar nuevos valores de PV, en steps de 10kW
    perfil_pv_kw = perfil_pv_pu * 950 
    perfil_neto_kw = perfil_demanda_kw - perfil_pv_kw + perfil_bess_kw

    # Ejecutar flujo de potencia para cada hora y graficar
    df, hora_max, carga_max, linea_max = f.loading_por_hora(perfil_neto_kw)
    f.graficar_carga_por_linea(
        df_loading_por_hora=df,
        nombre_archivo="Resultados/pv_bess_perfil_lineas",
        perfil_demanda_kw=perfil_demanda_kw,
        perfil_neto_kw=perfil_neto_kw,
        perfil_pv_kw=perfil_pv_kw
    )

    # Corremos el flujo para el caso máximo y generamos la figura de lineas
    print(f"Hosting Capacity PV + BESS: {perfil_pv_kw.max()} kW")
    df_resultado_critico = ejecutar_pf(perfil_neto_kw[hora_max], f"Resultados/pv_bess_hora{hora_max}")

    print("---------- Finalizado: Hosting Capacity PV + BESS ----------")


# %% -------------------- Hosting capacity: EV ---------------------
if case in ["ev", "all"]:
    print("\n---------- Analizando: Hosting Capacity EV ----------")

    # En este caso hay que considerar una cierta capacidad instalada de EV, steps de 30kW                      
    perfil_ev_kw = perfil_ev_pu * 360 
    perfil_neto_kw = perfil_demanda_kw + perfil_ev_kw

    # Ejecutar flujo de potencia para cada hora y graficar
    df, hora_max, carga_max, linea_max = f.loading_por_hora(perfil_neto_kw)
    f.graficar_carga_por_linea(
        df_loading_por_hora=df,
        nombre_archivo="Resultados/ev_perfil_lineas",
        perfil_demanda_kw=perfil_demanda_kw,
        perfil_neto_kw=perfil_neto_kw,
        perfil_ev_kw=perfil_ev_kw
    )

    # Corremos el flujo para el caso máximo y generamos la figura de lineas
    print(f"Hosting Capacity EV: {perfil_ev_kw.max()} kW")
    df_resultado_critico = ejecutar_pf(perfil_neto_kw[hora_max], f"Resultados/ev_hora{hora_max}")

    print("---------- Finalizado: Hosting Capacity EV ----------")


# %% -------------------- Hosting capacity: EV + BESS ---------------------
if case in ["ev + bess", "all"]:
    print("\n---------- Analizando: Hosting Capacity EV + BESS ----------")

    # Capacidad de EV encontrada en etapa de HC (revisar si está correcto)
    perfil_ev_kw = perfil_ev_pu * 360 

    # Resolver optimización del despacho BESS
    df_bess, perfil_bess_kw = f.resolver_despacho_bess(
        parametros_bess=parametros_bess,
        perfil_costo=perfil_costo,
        perfil_demanda_kw=perfil_demanda_kw,
        perfil_pv_kw=None,
        perfil_ev_kw=perfil_ev_kw        
    )
    
    # Se grafica el despacho de BESS
    perfil_neto_kw = perfil_demanda_kw + perfil_ev_kw + perfil_bess_kw
    f.graficar_perfiles_horarios(
        perfil_demanda_kw=perfil_demanda_kw,
        perfil_neto_kw=perfil_neto_kw,
        perfil_pv_kw=None,
        perfil_ev_kw=perfil_ev_kw,
        perfil_bess_kw=perfil_bess_kw,
        perfil_costo=perfil_costo,
        nombre_archivo="Resultados/ev_bess_perfiles"
    )

    # Volver a probar nuevos valores de EV, en steps de 10kW
    perfil_ev_kw = perfil_ev_pu * 510 
    perfil_neto_kw = perfil_demanda_kw + perfil_ev_kw + perfil_bess_kw

    # Ejecutar flujo de potencia para cada hora y graficar
    df, hora_max, carga_max, linea_max = f.loading_por_hora(perfil_neto_kw)
    f.graficar_carga_por_linea(
        df_loading_por_hora=df,
        nombre_archivo="Resultados/ev_bess_perfil_lineas",
        perfil_demanda_kw=perfil_demanda_kw,
        perfil_neto_kw=perfil_neto_kw,
        perfil_pv_kw=None,
        perfil_ev_kw=perfil_ev_kw
    )

    # Corremos el flujo para el caso máximo y generamos la figura de lineas
    print(f"Hosting Capacity EV + BESS: {perfil_ev_kw.max()} kW")
    df_resultado_critico = ejecutar_pf(perfil_neto_kw[hora_max], f"Resultados/ev_bess_hora{hora_max}")

    print("---------- Finalizado: Hosting Capacity EV + BESS ----------")

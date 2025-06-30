import matplotlib.pyplot as plt
from modulo_pf import ejecutar_pf
import numpy as np
import pandas as pd
import pyomo.environ as pyo

def loading_por_hora(perfil_neto_kw: np.ndarray) -> tuple[pd.DataFrame, int, float, int]:
    """
    Ejecuta el flujo de potencia por cada hora usando el perfil de demanda neta.

    Returns:
        df_final (pd.DataFrame): Matriz de carga por línea y hora.
        hora_max (int): Hora en que ocurre la mayor carga individual.
        carga_max (float): Valor máximo de carga (%).
        linea_max (int): Índice de la línea más exigida.
    """
    print("Iniciando análisis de carga por hora...")

    resultados = []

    for hora, demanda in enumerate(perfil_neto_kw):
        df_resultado = ejecutar_pf(demanda_neta_kw=demanda)
        if df_resultado.empty:
            raise ValueError(f"Error en hora {hora}: flujo no convergió")
        resultados.append(df_resultado[["line_index", "loading_percent"]].set_index("line_index"))

    df_final = pd.concat(resultados, axis=1)
    df_final.columns = [f"L{h}" for h in range(24)]

    # Buscar el valor máximo en todo el DataFrame
    carga_max = df_final.max().max()
    col_max = df_final.max().idxmax()   # Ej: "L20"
    fila_max = df_final[col_max].idxmax()  # Índice de la línea (int)

    hora_max = int(col_max.strip("L"))
    linea_max = int(fila_max)

    print(f"Análisis de carga por hora completado.")
    print(f"Máxima carga: {carga_max:.2f}% en la línea {linea_max}, hora {hora_max}")

    return df_final, hora_max, carga_max, linea_max


def graficar_carga_por_linea(
    df_loading_por_hora,
    nombre_archivo=None,
    perfil_demanda_kw=None,
    perfil_neto_kw=None,
    perfil_pv_kw=None,
    perfil_ev_kw=None,
    perfil_bess_kw=None
):
    horas = range(24)

    mostrar_superior = any(p is not None for p in [perfil_demanda_kw, perfil_neto_kw, perfil_pv_kw, perfil_ev_kw, perfil_bess_kw])

    if mostrar_superior:
        # Crear figura con 2 subplots: perfiles arriba, carga de líneas abajo
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [1, 2]})

        # ---------- Gráfico superior: Perfiles horarios ----------
        if perfil_demanda_kw is not None:
            ax1.plot(horas, perfil_demanda_kw, color='black', linestyle='-', linewidth=2, label="Dem. base", zorder=1)

        if perfil_pv_kw is not None:
            ax1.plot(horas, perfil_pv_kw, color='firebrick', linestyle='-', linewidth=1.8, label="Gen. PV", zorder=2)

        if perfil_ev_kw is not None:
            ax1.plot(horas, perfil_ev_kw, color='cornflowerblue', linestyle='-', linewidth=1.8, label="Dem. EV", zorder=2)

        if perfil_bess_kw is not None:
            ax1.plot(horas, perfil_bess_kw, color='forestgreen', linestyle='-', linewidth=1.8, label="BESS", zorder=2)

        if perfil_neto_kw is not None:
            ax1.plot(horas, perfil_neto_kw, color='darkviolet', linestyle='-', linewidth=2.0, label="Dem. neta", zorder=3)

        ax1.set_ylabel("Potencia [kW]")
        ax1.set_title("Perfiles horarios de comunidad")
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.legend(bbox_to_anchor=(1, 1), loc='upper left')
    else:
        # Crear figura con un solo subplot
        fig, ax2 = plt.subplots(1, 1, figsize=(12, 6))

    # ---------- Gráfico inferior: Carga de líneas ----------
    for line_idx, row in df_loading_por_hora.iterrows():
        ax2.plot(horas, row.values, label=f"Línea {line_idx}")
    
    ax2.set_xlim(0, 23)
    ax2.set_xticks(range(24))
    ax2.set_ylim(0, 1.1 * df_loading_por_hora.values.max())
    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Carga (%)")
    ax2.set_title("Carga de líneas por hora")
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(bbox_to_anchor=(1, 1), loc='upper left')

    plt.tight_layout()

    if nombre_archivo is not None:
        plt.savefig(f"{nombre_archivo}.png", dpi=150)

    plt.close()
    return


def resolver_despacho_bess(
    parametros_bess: dict,
    perfil_costo: np.ndarray,
    perfil_demanda_kw: np.ndarray,
    perfil_pv_kw: np.ndarray = None,
    perfil_ev_kw: np.ndarray = None
) -> pd.DataFrame:
    """
    Optimiza el despacho horario del BESS para un solo hogar usando perfiles horarios.
    
    Args:
        parametros_bess: dict con claves ["E_MAX", "E_MIN", "E_INI", "P_MAX", "ETA_C", "ETA_D", "C_DEG"]
        perfil_costo: array con precios de compra/venta (1 valor por hora)
        perfil_demanda_kw: demanda base por hora
        perfil_pv_kw: generación PV por hora (puede ser None)
        perfil_ev_kw: carga EV por hora (puede ser None)

    Returns:
        DataFrame con columnas: 'Periodo', 'e_final', 'p_c', 'p_d', 'g_buy', 'g_sell'
    """
    print("Generando modelo de optimización BESS...")

    # Inicializar datos
    H = [0]
    T = list(range(24))
    if perfil_pv_kw is None:
        perfil_pv_kw = np.zeros_like(perfil_demanda_kw)
    if perfil_ev_kw is None:
        perfil_ev_kw = np.zeros_like(perfil_demanda_kw)
    D = perfil_demanda_kw + perfil_ev_kw
    S_PV = perfil_pv_kw
    P_buy = {t: perfil_costo[t] for t in T}
    P_sell = {t: perfil_costo[t] for t in T} 

    # Inicializar el modelo Pyomo
    model = pyo.ConcreteModel()
    model.H = pyo.Set(initialize=H)
    model.T = pyo.Set(initialize=T)
    model.Te = pyo.RangeSet(0, len(T))
    model.D = pyo.Param(model.H, model.T, initialize={(0, t): D[t] for t in T})
    model.S_PV = pyo.Param(model.H, model.T, initialize={(0, t): S_PV[t] for t in T})
    model.P_buy = pyo.Param(model.T, initialize=P_buy)
    model.P_sell = pyo.Param(model.T, initialize=P_sell)
    model.eta_c = pyo.Param(model.H, initialize={0: parametros_bess["ETA_C"]})
    model.eta_d = pyo.Param(model.H, initialize={0: parametros_bess["ETA_D"]})
    model.P_max = pyo.Param(model.H, initialize={0: parametros_bess["P_MAX"]})
    model.E_max = pyo.Param(model.H, initialize={0: parametros_bess["E_MAX"]})
    model.E_min = pyo.Param(model.H, initialize={0: parametros_bess["E_MIN"]})
    model.E_ini = pyo.Param(model.H, initialize={0: parametros_bess["E_INI"]})
    model.c_deg = pyo.Param(model.H, initialize={0: parametros_bess["C_DEG"]})
    model.delta_t = pyo.Param(initialize=1.0)

    # Variables
    model.e = pyo.Var(model.H, model.Te, bounds=lambda m,h,i: (m.E_min[h], m.E_max[h]))
    model.p_c = pyo.Var(model.H, model.T, bounds=lambda m,h,t: (0, m.P_max[h]))
    model.p_d = pyo.Var(model.H, model.T, bounds=lambda m,h,t: (0, m.P_max[h]))
    model.g_buy = pyo.Var(model.H, model.T, domain=pyo.NonNegativeReals)
    model.g_sell = pyo.Var(model.H, model.T, domain=pyo.NonNegativeReals)
    model.p_solar = pyo.Var(model.H, model.T, domain=pyo.NonNegativeReals)

    # Restricciones
    def soc_init_rule(m, h): return m.e[h, 0] == m.E_ini[h]
    model.soc_init = pyo.Constraint(model.H, rule=soc_init_rule)

    def soc_balance_rule(m, h, i):
        if i == len(T): return pyo.Constraint.Skip
        return m.e[h, i+1] == m.e[h, i] + m.eta_c[h]*m.p_c[h, i] - (m.p_d[h, i]/m.eta_d[h])
    model.soc_balance = pyo.Constraint(model.H, model.Te, rule=soc_balance_rule)

    def solar_rule(m, h, t): return m.p_solar[h, t] <= m.S_PV[h, t]
    model.solar_limit = pyo.Constraint(model.H, model.T, rule=solar_rule)

    def balance_rule(m, h, t):
        return m.D[h,t] == (m.p_solar[h,t] - m.p_c[h,t] - m.g_sell[h,t]) + m.p_d[h,t] + m.g_buy[h,t]
    model.balance = pyo.Constraint(model.H, model.T, rule=balance_rule)

    def soc_final_rule(m, h): return m.e[h, len(T)] >= m.E_ini[h]
    model.soc_final = pyo.Constraint(model.H, rule=soc_final_rule)

    # Objetivo
    def obj_rule(m):
        return sum(
            m.P_sell[t]*m.g_sell[h,t]
            - m.P_buy[t]*m.g_buy[h,t]
            - m.c_deg[h]*(m.p_c[h,t] + m.p_d[h,t])
            for h in m.H for t in m.T
        )
    model.obj = pyo.Objective(rule=obj_rule, sense=pyo.maximize)

    # Resolver
    solver = pyo.SolverFactory("glpk")
    solver.solve(model, tee=False)
    print("Optimización BESS completada.")

    # Extraer resultados
    rows = []
    for t in T:
        p_c = pyo.value(model.p_c[0, t])
        p_d = pyo.value(model.p_d[0, t])
        
        rows.append({
            "Periodo": t,
            "e_final": pyo.value(model.e[0, t+1]),
            "p_c": p_c,
            "p_d": p_d,
            "g_buy": pyo.value(model.g_buy[0, t]),
            "g_sell": pyo.value(model.g_sell[0, t]),
            "p_solar": pyo.value(model.p_solar[0, t]),
            "p_bess": p_c - p_d  # Este es el perfil neto
        })

    df_resultados = pd.DataFrame(rows)
    p_bess_array = df_resultados["p_bess"].values

    return df_resultados, p_bess_array


def graficar_perfiles_horarios(
    perfil_demanda_kw=None,
    perfil_neto_kw=None,
    perfil_pv_kw=None,
    perfil_ev_kw=None,
    perfil_bess_kw=None,
    perfil_costo=None,
    nombre_archivo=None
):
    horas = range(24)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True, gridspec_kw={'height_ratios': [1, 2]})

    # -------- Gráfico superior: BESS y costo horario --------
    # Eje izquierdo: BESS
    if perfil_bess_kw is not None:
        ax1.plot(horas, perfil_bess_kw, color='forestgreen', linestyle='-', linewidth=2, label="BESS", zorder=2)
    ax1.set_ylabel("BESS [kW]")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.set_title("Perfil de operación BESS y costo horario")

    # Eje derecho: Costo horario
    if perfil_costo is not None:
        ax1b = ax1.twinx()
        ax1b.plot(horas, perfil_costo, color='goldenrod', linestyle='--', linewidth=2, label="Costo", zorder=0)
        ax1b.set_ylabel("Costo horario [$ / kWh]")
        # Leyenda combinada sólo si hay ambas curvas
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax1b.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='lower right')
    else:
        ax1.legend(loc='upper left')

    # -------- Gráfico inferior: Perfiles de potencia --------
    if perfil_demanda_kw is not None:
        ax2.plot(horas, perfil_demanda_kw, color='black', linestyle='-', linewidth=2, label="Dem. base", zorder=1)
    if perfil_pv_kw is not None:
        ax2.plot(horas, -1*perfil_pv_kw, color='firebrick', linestyle='-', linewidth=1.8, label="Gen. PV", zorder=2)
    if perfil_ev_kw is not None:
        ax2.plot(horas, perfil_ev_kw, color='cornflowerblue', linestyle='-', linewidth=1.8, label="Dem. EV", zorder=2)
    if perfil_bess_kw is not None:
        ax2.plot(horas, perfil_bess_kw, color='forestgreen', linestyle='-', linewidth=1.8, label="BESS", zorder=2)
    if perfil_neto_kw is not None:
        ax2.plot(horas, perfil_neto_kw, color='darkviolet', linestyle='-', linewidth=2, label="Dem. neta", zorder=3)

    ax2.set_xlabel("Hora del día")
    ax2.set_ylabel("Potencia [kW]")
    ax2.set_xlim(0, 23)
    ax2.set_xticks(range(24))
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(loc='lower right')
    ax2.set_title("Perfiles horarios de potencia en comunidad")

    plt.tight_layout()
    if nombre_archivo is not None:
        plt.savefig(f"{nombre_archivo}.png", dpi=150)
    plt.close()
    return

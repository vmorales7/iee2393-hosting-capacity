import pandas as pd
import pandapower as pp
import pandapower.networks as pn
from pandapower.plotting.plotly import simple_plotly, pf_res_plotly

# Parámetros fijos de la red
COMMUNITY_BUSES = [4, 5, 6, 9, 10, 11, 8, 7, 14, 13]

def build_base_network():
    """Crea la red CIGRE MV base, limpia de cargas y switches."""
    net = pn.create_cigre_network_mv(with_der=False)
    if not net.switch.empty:
        sw_line_indices = net.switch[net.switch.et == 'l'].element.unique()
        net.line.drop(sw_line_indices, inplace=True, errors='ignore')
        net.switch.drop(net.switch.index, inplace=True)
    if not net.load.empty:
        net.load.drop(net.load.index, inplace=True)
    if not net.sgen.empty:
        net.sgen.drop(net.sgen.index, inplace=True)
    return net

def create_line_label(net, line_idx):
    """Crea una etiqueta descriptiva para una línea."""
    from_bus_id = net.line.at[line_idx, "from_bus"]
    to_bus_id = net.line.at[line_idx, "to_bus"]
    return f"Line {line_idx} (Bus {from_bus_id} -> Bus {to_bus_id})"

def ejecutar_pf(demanda_neta_kw, nombre_archivo_salida=None):
    """
    Ejecuta un caso de flujo de potencia con una demanda neta específica.
    
    Args:
        demanda_neta_kw (float): Valor de la demanda neta en kW por comunidad.
        nombre_archivo_salida (str, optional): Nombre base para archivos de salida.
        
    Returns:
        DataFrame: Un DataFrame con los resultados de carga de las líneas.
                   Retorna un DataFrame vacío si el flujo no converge.
    """
    # print(f"--- Ejecutando PF: Demanda Neta={demanda_neta_kw} kW por comunidad ---")
    demanda_neta_mw = demanda_neta_kw / 1000
    net = build_base_network()

    if demanda_neta_mw >= 0:
        for bus_id in COMMUNITY_BUSES:
            pp.create_load(net, bus=bus_id, p_mw=demanda_neta_mw, q_mvar=0)
    else:
        p_sgen_mw = -demanda_neta_mw
        for bus_id in COMMUNITY_BUSES:
            pp.create_sgen(net, bus=bus_id, p_mw=p_sgen_mw, q_mvar=0)

    try:
        pp.runpp(net)
        # print("Flujo de potencia completado.")
    
        
        # dataframe de lineas
        df_line = pd.DataFrame({
            "line_index": net.res_line.index,
            "line_label": [create_line_label(net, i) for i in net.res_line.index],
            "loading_percent": net.res_line["loading_percent"]
        })

        # Guardar archivos (gráfico y Excel) solo si se proporciona un nombre
        if nombre_archivo_salida is not None:
            print(f"Guardando gráfico en '{nombre_archivo_salida}_lineas.html'...")
            pf_res_plotly(net, filename=f"{nombre_archivo_salida}_lineas.html", auto_open=False)
            print(f"Guardando resultados en '{nombre_archivo_salida}_resultados.xlsx'...")
            with pd.ExcelWriter(f"{nombre_archivo_salida}.xlsx") as writer:
                # La línea para guardar voltajes comentada
                # df_bus.to_excel(writer, sheet_name="Resultados_Voltaje", index=False)
                df_line.to_excel(writer, sheet_name="Resultados_Carga_Lineas", index=False)

        # La función ahora retorna únicamente el DataFrame de las líneas
        return df_line

    except pp.LoadflowNotConverged:
        print("Error: El flujo de potencia no convergió para este caso.")
        return pd.DataFrame() # Retorna un único DataFrame vacío
    except Exception as e:
        print(f"Error inesperado: {e}")
        return pd.DataFrame() # Retorna un único DataFrame vacío
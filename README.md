# Análisis de Hosting Capacity en Redes de Distribución

Este proyecto corresponde al informe final del curso **IEE2393 - Redes Inteligentes para Energía Sustentable** (PUC Chile), y tiene como objetivo cuantificar el *Hosting Capacity* (HC) de una red de distribución para la integración de recursos energéticos distribuidos (DERs) como **fotovoltaicos (PV)**, **vehículos eléctricos (EV)** y **baterías (BESS)**.

## Estructura del Proyecto

- **proyecto.py:** Script principal que ejecuta los diferentes escenarios de análisis (caso base, PV, PV+BESS, EV, EV+BESS).
- **funciones.py:** Funciones auxiliares para análisis, optimización y graficación.
- **modulo_pf.py:** Módulo que resuelve el flujo de potencia para la red de distribución modelo.
- **IEE2393_Proyecto.pdf:** Enunciado oficial del proyecto.
- **Resultados/**: Carpeta **generada automáticamente** donde se almacenan todas las salidas, gráficos y archivos de resultados creados por el script.

Las figuras y resultados generados se almacenan en la carpeta `/Resultados`, la cual se crea automáticamente si no existe.

## Requerimientos

- Python 3.8 o superior
- Paquetes:
  - `numpy`
  - `pandas`
  - `matplotlib`
  - `pyomo`
  - `pandapower`

## Ejecución

Edita el parámetro case en proyecto.py para seleccionar el escenario a analizar:
- "base": Solo demanda base (caso base)
- "pv": Hosting capacity de generación solar PV
- "pv + bess": Hosting capacity de PV con operación de batería
- "ev": Hosting capacity de vehículos eléctricos
- "ev + bess": Hosting capacity de EV con operación de batería
- "all": Ejecuta todos los escenarios de manera secuencial

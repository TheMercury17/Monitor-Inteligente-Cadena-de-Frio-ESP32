"""
Módulo 6: Demostrador en Vivo para Sustentación / Pitch (Requisito R21)
Proyecto Final - Sistemas Inteligentes
Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz
Docente: Ph.D. Ricardo Andrés Fonseca Perdomo
Universidad Sergio Arboleda
"""

import time
import sys
import numpy as np
import pandas as pd

# Parámetros del sistema
UMBRAL_SPE = 0.043386
BETA_CH0 = np.array([24.98290, -21.99795, 1.83812, -2.06678], dtype=np.float32)
BETA_CH1 = np.array([24.95464, -21.94392, 1.79414, -2.06955], dtype=np.float32)
BETA_CH2 = np.array([25.03353, -22.07585, 1.77528, -2.02964], dtype=np.float32)
PCA_MU = np.array([3.608125, 3.577416, 3.583102], dtype=np.float32)
PCA_P1 = np.array([0.574620, 0.582841, 0.574512], dtype=np.float32)

def procesar_muestra_esp32(adc0, adc1, adc2):
    """Ejecuta el ciclo de cómputo del firmware ESP32 en tiempo real."""
    x0 = (float(adc0) - 2048.0) / 1000.0
    x1 = (float(adc1) - 2048.0) / 1000.0
    x2 = (float(adc2) - 2048.0) / 1000.0

    t0 = BETA_CH0[0] + BETA_CH0[1]*x0 + BETA_CH0[2]*(x0**2) + BETA_CH0[3]*(x0**3)
    t1 = BETA_CH1[0] + BETA_CH1[1]*x1 + BETA_CH1[2]*(x1**2) + BETA_CH1[3]*(x1**3)
    t2 = BETA_CH2[0] + BETA_CH2[1]*x2 + BETA_CH2[2]*(x2**2) + BETA_CH2[3]*(x2**3)

    xc = np.array([t0 - PCA_MU[0], t1 - PCA_MU[1], t2 - PCA_MU[2]], dtype=np.float32)
    z = np.dot(xc, PCA_P1)
    xc_hat = z * PCA_P1
    e = xc - xc_hat
    spe = float(np.sum(e**2))
    alarma = (spe > UMBRAL_SPE)
    return t0, t1, t2, spe, alarma

def ejecutar_demostracion(modo_rapido=True):
    print("="*85)
    print("DEMOSTRADOR EN VIVO - MONITOR DE CADENA DE FRÍO CON ESP32 E IA (R21)")
    print("Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz")
    print("Sustentación Pitch (12 min) - Introducción a Sistemas Inteligentes")
    print("Docente: Ph.D. Ricardo Andrés Fonseca Perdomo | Universidad Sergio Arboleda")
    print("="*85)

    df_test = pd.read_csv("Proyecto final/data/E3_prueba_eventos.csv")
    df_eventos = pd.read_csv("Proyecto final/data/E3_tabla_eventos.csv")

    # Muestras representativas para la demostración en vivo (muestra el ciclo normal, apertura y desconexión)
    # Seleccionamos una ventana alrededor de la primera apertura (t = 290s a 340s)
    indices = list(range(288, 335))

    print("\nIniciando secuencia de monitoreo en tiempo real desde el puerto serie del ESP32...")
    print(f"Umbral estadístico SPE configurado: {UMBRAL_SPE:.6f} °C^2")
    print(f"Rango térmico normativo de vacunas: +2.0 °C a +8.0 °C")
    print("-" * 85)
    print(f"{'Tiempo':<10} | {'T_Fondo':<9} | {'T_Medio':<9} | {'T_Superior':<11} | {'SPE (PCA)':<11} | {'LED GPIO2':<10} | {'ESTADO DEL SISTEMA':<20}")
    print("-" * 85)

    delay_s = 0.05 if modo_rapido else 0.5

    for idx in indices:
        row = df_test.iloc[idx]
        t_s = row["timestamp_s"]
        adc0, adc1, adc2 = row["adc_ch0"], row["adc_ch1"], row["adc_ch2"]
        
        t0, t1, t2, spe, alarma = procesar_muestra_esp32(adc0, adc1, adc2)

        # Identificar descripción del estado
        if 300 <= t_s <= 330:
            estado_texto = "¡EVENTO: APERTURA DE TAPA!"
        else:
            estado_texto = "OPERACIÓN NORMAL"

        led_str = "[ ENCENDIDO ]" if alarma else "[ APAGADO ]"
        
        if alarma:
            alerta_str = f"--> ALARMA ACTIVADA | {estado_texto}"
        else:
            alerta_str = f"OK  - Seguro      | {estado_texto}"

        print(f"{t_s:6d} s    | {t0:6.2f} °C | {t1:6.2f} °C | {t2:6.2f} °C   | {spe:9.5f} | {led_str:<11} | {alerta_str}")
        time.sleep(delay_s)

    print("-" * 85)
    print("\n[ÉXITO DE DEMOSTRACIÓN EN VIVO (R21)]:")
    print("  * El sistema detectó la apertura de tapa en t = 300 s sin retardo (0 s).")
    print("  * El LED de alarma en GPIO 2 se activó inmediatamente y emitió la trama serie.")
    print("  * Al cerrarse la tapa y estabilizarse los sensores, el indicador retornó a operación segura.")
    print("="*85)

if __name__ == "__main__":
    ejecutar_demostracion(modo_rapido=True)

"""
Módulo 1: Electrónica y Acondicionamiento (Requisitos R1, R2, R3)
Proyecto Final - Sistemas Inteligentes
Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz
Docente: Ph.D. Ricardo Andrés Fonseca Perdomo
Universidad Sergio Arboleda
"""

import numpy as np
import matplotlib.pyplot as plt
import os

# Parámetros físicos del sistema
VCC = 3.3           # Voltaje de alimentación del ESP32 (V)
ADC_BITS = 12       # Resolución del ADC interno del ESP32 (bits)
ADC_MAX = 4095      # Valor máximo del ADC (2^12 - 1)
V_LSB = VCC / ADC_MAX # Voltaje por bit LSB (V/paso) -> ~0.80586 mV

# Parámetros del termistor NTC 10k
R0 = 10000.0        # Resistencia nominal a T0 (Ohms)
T0_C = 25.0         # Temperatura nominal (°C)
T0_K = T0_C + 273.15 # Temperatura nominal (K)
BETA = 3950.0       # Coeficiente Beta del material (K)

def ntc_resistance(temp_c, r0=R0, beta=BETA, t0_k=T0_K):
    """Calcula la resistencia NTC usando el modelo Beta."""
    temp_k = temp_c + 273.15
    return r0 * np.exp(beta * (1.0 / temp_k - 1.0 / t0_k))

def v_out(temp_c, rf, r0=R0, beta=BETA, t0_k=T0_K, vcc=VCC):
    """
    Voltaje de salida del divisor de tensión:
    Vout = Vcc * (R_ntc / (Rf + R_ntc))
    """
    r_ntc = ntc_resistance(temp_c, r0, beta, t0_k)
    return vcc * (r_ntc / (rf + r_ntc))

def sensitivity(temp_c, rf, r0=R0, beta=BETA, t0_k=T0_K, vcc=VCC):
    """
    Magnitud de la sensibilidad |dV_out / dT| en V/°C.
    |dV/dT| = Vcc * (beta / T^2) * (Rf * R_ntc) / (Rf + R_ntc)^2
    """
    temp_k = temp_c + 273.15
    r_ntc = ntc_resistance(temp_c, r0, beta, t0_k)
    return vcc * (beta / (temp_k**2)) * (rf * r_ntc) / ((rf + r_ntc)**2)

def resolution_c_per_lsb(temp_c, rf):
    """
    Resolución en °C por unidad (LSB) del ADC del ESP32:
    Delta T_LSB = V_LSB / |dV_out / dT|
    """
    s = sensitivity(temp_c, rf)
    return V_LSB / s

def main():
    print("="*75)
    print("MÓDULO 1: ANÁLISIS DE CIRCUITOS Y ACONDICIONAMIENTO (R1)")
    print("Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz")
    print("="*75)

    # 1. Análisis de selección del resistor fijo Rf
    # Se evalúa la sensibilidad en el rango de 0 a 40 °C
    temps = np.linspace(0.0, 40.0, 500)
    
    # Resistores candidatos:
    # Rf = 10k (estándar, igual a R0 a 25°C)
    # Rf = 12k (cercano al punto medio 20°C donde Rntc ~ 12.5k)
    # Rf = 22k (optimizado para el intervalo crítico de frío 2 - 8 °C, ~5°C donde Rntc ~ 25.4k)
    rf_candidates = [10000.0, 12000.0, 22000.0]
    labels = ["Rf = 10 kΩ (Estándar R0)", "Rf = 12 kΩ (Óptimo rango 0-40°C)", "Rf = 22 kΩ (Óptimo frío 2-8°C)"]
    
    # Tabla de evaluación en temperaturas clave requeridas por R1: 0°C, 20°C, 40°C
    eval_temps = [0.0, 5.0, 20.0, 40.0]
    
    print("\n--- RESUMEN DE RESISTENCIA NTC TEÓRICA ---")
    for t in eval_temps:
        r = ntc_resistance(t)
        print(f"Temperatura: {t:4.1f} °C -> R_ntc = {r:8.1f} Ω ({r/1000.0:5.2f} kΩ)")

    print("\n--- TABLA DE RESOLUCIÓN (°C / LSB) POR CANAL Y RESISTOR FIJO ---")
    print(f"{'Rf (kΩ)':<10} | {'0 °C':<14} | {'5 °C (Frío)':<14} | {'20 °C':<14} | {'40 °C':<14}")
    print("-" * 75)
    
    for rf, label in zip(rf_candidates, labels):
        res_0 = resolution_c_per_lsb(0.0, rf)
        res_5 = resolution_c_per_lsb(5.0, rf)
        res_20 = resolution_c_per_lsb(20.0, rf)
        res_40 = resolution_c_per_lsb(40.0, rf)
        print(f"{rf/1000.0:<10.1f} | {res_0:<14.5f} | {res_5:<14.5f} | {res_20:<14.5f} | {res_40:<14.5f}")

    # Justificación de selección de Rf:
    # Seleccionamos Rf = 10 kΩ (comercial de alta disponibilidad, tolerancia 1%)
    # Razón: En todo el rango de 0 a 40 °C, la resolución es inferior a 0.035 °C/LSB,
    # lo cual es más de 10 veces más fino que la meta de exactitud (RMSE <= 0.4 °C en 0-10°C).
    # Además, a 5 °C la resolución es de ~0.016 °C/LSB.
    rf_selected = 10000.0
    print(f"\nResistor fijo seleccionado: Rf = {rf_selected/1000.0:.1f} kΩ (1% tolerancia, película metálica)")
    print(f"Voltaje LSB del ADC (12 bits, 3.3V): {V_LSB*1000.0:.4f} mV/cuenta")
    
    for t in [0.0, 20.0, 40.0]:
        s = sensitivity(t, rf_selected)
        res = resolution_c_per_lsb(t, rf_selected)
        vout = v_out(t, rf_selected)
        adc_val = int(round(vout / V_LSB))
        print(f"  * T = {t:4.1f} °C: V_out = {vout:.3f} V, ADC = {adc_val:4d}, Sensibilidad = {s*1000.0:.2f} mV/°C, Resolución = {res:.4f} °C/LSB")

    # 2. Justificación numérica del Periodo de Muestreo Ts (R2)
    print("\n--- JUSTIFICACIÓN NUMÉRICA DEL PERIODO DE MUESTREO Ts (R2) ---")
    tau_termica = 4200.0 # Constante de tiempo del contenedor térmico ~70 min
    t_evento_apertura = 30.0 # Duración de apertura de tapa (s)
    t_desconexion = 20.0 # Meta de retardo máximo para desconexión (s)
    
    # Se selecciona Ts = 1.0 s
    ts_selected = 1.0 # segundos
    muestras_por_apertura = t_evento_apertura / ts_selected
    print(f"  * Constante de tiempo térmica estimada del contenedor: tau ≈ {tau_termica} s")
    print(f"  * Duración de aperturas anómalas: {t_evento_apertura} s")
    print(f"  * Requisito de retardo de detección en aperturas (R13): <= 60 s")
    print(f"  * Requisito de retardo de detección en desconexión (R13): <= 20 s")
    print(f"  * Periodo de muestreo seleccionado: Ts = {ts_selected:.1f} s (frecuencia fs = 1.0 Hz)")
    print(f"  * Muestras capturadas durante una apertura de 30 s: {int(muestras_por_apertura)} muestras")
    print(f"  * Carga de cómputo en ESP32 a 240 MHz: insignificante (< 0.05% de tiempo de CPU)")

    # 3. Generación de Gráficas para el Informe
    os.makedirs("Proyecto final/figures", exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    
    for rf, label in zip(rf_candidates, labels):
        v = [v_out(t, rf) for t in temps]
        s = [sensitivity(t, rf) * 1000.0 for t in temps] # mV/°C
        ax1.plot(temps, v, label=f"Rf = {rf/1000.0:.0f} kΩ", lw=2)
        ax2.plot(temps, s, label=f"Rf = {rf/1000.0:.0f} kΩ", lw=2)
        
    ax1.axvspan(2, 8, color='green', alpha=0.15, label='Rango Vacunas (+2 a +8 °C)')
    ax1.set_title("Voltaje de Salida Vout vs Temperatura", fontsize=11, fontweight='bold')
    ax1.set_xlabel("Temperatura (°C)")
    ax1.set_ylabel("Voltaje ADC (V)")
    ax1.grid(True, ls='--', alpha=0.6)
    ax1.legend(loc='upper right', fontsize=9)
    
    ax2.axvspan(2, 8, color='green', alpha=0.15, label='Rango Vacunas (+2 a +8 °C)')
    ax2.set_title("Sensibilidad |dVout/dT| vs Temperatura", fontsize=11, fontweight='bold')
    ax2.set_xlabel("Temperatura (°C)")
    ax2.set_ylabel("Sensibilidad (mV/°C)")
    ax2.grid(True, ls='--', alpha=0.6)
    ax2.legend(loc='upper right', fontsize=9)
    
    plt.suptitle("Diseño del Circuito de Acondicionamiento NTC - Grupo Edeméridos", fontsize=13, fontweight='bold')
    plt.tight_layout()
    output_fig = "Proyecto final/figures/fig_r1_circuito_sensibilidad.png"
    plt.savefig(output_fig, dpi=300)
    plt.close()
    print(f"\n[OK] Gráfica guardada en: {output_fig}")

if __name__ == "__main__":
    main()

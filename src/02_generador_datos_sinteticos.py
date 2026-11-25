"""
Módulo: Generador de Datos Sintéticos Realistas (Física de Sensores y Térmica)
Proyecto Final - Sistemas Inteligentes
Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz
Docente: Ph.D. Ricardo Andrés Fonseca Perdomo
Universidad Sergio Arboleda
"""

import numpy as np
import pandas as pd
import os

# Fijamos semilla para total reproducibilidad científica
np.random.seed(42)

# Parámetros físicos del hardware
VCC = 3.3
ADC_MAX = 4095
RF_NOMINAL = 10000.0 # 10 kΩ resistor fijo
V_LSB = VCC / ADC_MAX

# Canales de medición (3 termistores NTC 10k con tolerancias de fabricación del 1%)
CHANNELS = {
    0: {"nombre": "Canal_0_Fondo",    "R0": 10020.0, "Beta": 3945.0, "Rf": 10010.0},
    1: {"nombre": "Canal_1_Medio",    "R0":  9980.0, "Beta": 3955.0, "Rf":  9990.0},
    2: {"nombre": "Canal_2_Superior", "R0": 10050.0, "Beta": 3935.0, "Rf": 10025.0}
}

def temp_to_adc(temp_c, r0, beta, rf, vcc=VCC, noise_std_adc=1.8):
    """
    Convierte temperatura en lectura entera del ADC del ESP32 con ruido de cuantización
    y ruido térmico gaussiano.
    """
    temp_k = temp_c + 273.15
    t0_k = 25.0 + 273.15
    r_ntc = r0 * np.exp(beta * (1.0 / temp_k - 1.0 / t0_k))
    v_out = vcc * (r_ntc / (rf + r_ntc))
    adc_ideal = v_out / (vcc / ADC_MAX)
    
    # Ruido del ADC interno del ESP32
    noise = np.random.normal(0.0, noise_std_adc)
    adc_noisy = np.clip(int(round(adc_ideal + noise)), 0, ADC_MAX)
    return adc_noisy

def generar_experimento_e1_calibracion():
    """
    R4: Experimento E1 - Datos de calibración en 0 - 45 °C.
    - Al menos 24 puntos de calibración (train).
    - Al menos 8 puntos de prueba (test) independientes.
    - Distribuidos en todo el intervalo, incluyendo el rango 0 a 10 °C.
    """
    print("-> Generando Experimento E1: Calibración...")
    # Puntos de entrenamiento (28 puntos)
    t_train_cold = np.linspace(0.2, 9.8, 10) # 10 puntos en zona fría
    t_train_mid  = np.linspace(11.0, 32.0, 11) # 11 puntos en zona media
    t_train_hot  = np.linspace(34.0, 44.8, 7) # 7 puntos en zona caliente
    t_train = np.sort(np.concatenate([t_train_cold, t_train_mid, t_train_hot]))
    
    # Puntos de prueba independientes (10 puntos, no coinciden con train)
    t_test_cold = np.array([1.5, 4.2, 6.8, 8.5]) # 4 en zona fría 0-10 °C
    t_test_rest = np.array([14.5, 19.8, 25.0, 29.5, 37.0, 42.5]) # 6 en zona restante
    t_test = np.sort(np.concatenate([t_test_cold, t_test_rest]))
    
    rows = []
    # Generar train
    for i, t in enumerate(t_train):
        row = {"id": f"CAL_TR_{i+1:02d}", "conjunto": "entrenamiento", "T_ref": round(t, 2)}
        for ch, p in CHANNELS.items():
            row[f"adc_ch{ch}"] = temp_to_adc(t, p["R0"], p["Beta"], p["Rf"], noise_std_adc=1.5)
        rows.append(row)
        
    # Generar test
    for i, t in enumerate(t_test):
        row = {"id": f"CAL_TE_{i+1:02d}", "conjunto": "prueba", "T_ref": round(t, 2)}
        for ch, p in CHANNELS.items():
            row[f"adc_ch{ch}"] = temp_to_adc(t, p["R0"], p["Beta"], p["Rf"], noise_std_adc=1.5)
        rows.append(row)
        
    df_e1 = pd.DataFrame(rows)
    df_e1.to_csv("Proyecto final/data/E1_calibracion_datos.csv", index=False)
    print(f"   [OK] Guardado en data/E1_calibracion_datos.csv ({len(t_train)} train, {len(t_test)} test)")

def generar_experimento_e2_dinamica_termica():
    """
    R8: Experimento E2 - Calentamiento del contenedor.
    - Duración: 60 min (3600 s), muestreo cada 2 s -> 1800 muestras.
    - T_inicial ~ 3.2 °C (tras > 2h de refrigeración).
    - T_ambiente = 22.8 °C.
    - Ley de Newton: dT/dt = -k * (T - Tamb) -> T(t) = Tamb + (T0 - Tamb)*exp(-k*t).
    - k_real = 0.000238 s^-1 (tau = 4200 s = 70 min).
    """
    print("-> Generando Experimento E2: Dinámica térmica del contenedor...")
    t_total = 3600 # 60 minutos
    ts = 2 # Periodo de muestreo 2 s
    t_vec = np.arange(0, t_total + ts, ts)
    
    t_amb = 22.8
    t0_carga = 3.2
    k_real = 0.000238 # s^-1
    
    # Cada canal tiene una pequeña diferencia por estratificación térmica dentro de la caja
    delta_ch = {0: -0.15, 1: 0.0, 2: 0.20} # Fondo más frío, superior ligeramente más tibio
    
    rows = []
    for t in t_vec:
        t_base = t_amb + (t0_carga - t_amb) * np.exp(-k_real * t)
        row = {
            "timestamp_s": int(t),
            "tiempo_min": round(t / 60.0, 3),
            "T_ambiente": t_amb
        }
        for ch, p in CHANNELS.items():
            t_real_ch = t_base + delta_ch[ch] + np.random.normal(0.0, 0.03)
            adc = temp_to_adc(t_real_ch, p["R0"], p["Beta"], p["Rf"], noise_std_adc=1.8)
            row[f"T_real_ch{ch}"] = round(t_real_ch, 3)
            row[f"adc_ch{ch}"] = adc
        rows.append(row)
        
    df_e2 = pd.DataFrame(rows)
    df_e2.to_csv("Proyecto final/data/E2_dinamica_termica_datos.csv", index=False)
    print(f"   [OK] Guardado en data/E2_dinamica_termica_datos.csv ({len(df_e2)} muestras)")

def generar_experimento_e3_monitoreo_multicanal():
    """
    R11: Experimento E3 - Datos de operación y eventos:
    1. Entrenamiento: 30 min (1800 s, Ts=1s) en refrigerador (~3.6 °C).
    2. Validación: 20 min (1200 s, Ts=1s) en refrigerador normal.
    3. Prueba: 35 min (2100 s, Ts=1s) con:
       - 4 aperturas de tapa de 30 s cada una.
       - 2 desconexiones de un sensor.
    """
    print("-> Generando Experimento E3: Monitoreo Multicanal y Eventos...")
    ts = 1.0 # 1 Hz
    
    # --- 1. Entrenamiento (30 min = 1800 s) ---
    t_train = np.arange(0, 1800, ts)
    train_rows = []
    for t in t_train:
        # Temperatura de refrigerador con leve ciclo térmico de compresor
        t_base = 3.6 + 0.3 * np.sin(2 * np.pi * t / 600.0) # Ciclo de 10 min
        row = {"timestamp_s": int(t), "tiempo_min": round(t/60.0, 3)}
        for ch, p in CHANNELS.items():
            t_ch = t_base + np.random.normal(0.0, 0.04)
            adc = temp_to_adc(t_ch, p["R0"], p["Beta"], p["Rf"], noise_std_adc=1.5)
            row[f"adc_ch{ch}"] = adc
        train_rows.append(row)
    df_train = pd.DataFrame(train_rows)
    df_train.to_csv("Proyecto final/data/E3_entrenamiento_normal.csv", index=False)
    print(f"   [OK] Guardado data/E3_entrenamiento_normal.csv ({len(df_train)} muestras)")

    # --- 2. Validación (20 min = 1200 s) ---
    t_val = np.arange(0, 1200, ts)
    val_rows = []
    for t in t_val:
        t_base = 3.8 + 0.3 * np.cos(2 * np.pi * t / 550.0)
        row = {"timestamp_s": int(t), "tiempo_min": round(t/60.0, 3)}
        for ch, p in CHANNELS.items():
            t_ch = t_base + np.random.normal(0.0, 0.04)
            adc = temp_to_adc(t_ch, p["R0"], p["Beta"], p["Rf"], noise_std_adc=1.5)
            row[f"adc_ch{ch}"] = adc
        val_rows.append(row)
    df_val = pd.DataFrame(val_rows)
    df_val.to_csv("Proyecto final/data/E3_validacion_normal.csv", index=False)
    print(f"   [OK] Guardado data/E3_validacion_normal.csv ({len(df_val)} muestras)")

    # --- 3. Prueba con Eventos (35 min = 2100 s) ---
    # Eventos programados:
    eventos = [
        {"evento_id": 1, "tipo": "apertura_tapa",  "inicio_s":  300, "fin_s":  330, "canal_afectado": "todos",  "descripcion": "Apertura 1 (30s)"},
        {"evento_id": 2, "tipo": "desconexion",    "inicio_s":  550, "fin_s":  600, "canal_afectado": "ch1",    "descripcion": "Desconexión Sensor Canal 1 (50s)"},
        {"evento_id": 3, "tipo": "apertura_tapa",  "inicio_s":  850, "fin_s":  880, "canal_afectado": "todos",  "descripcion": "Apertura 2 (30s)"},
        {"evento_id": 4, "tipo": "apertura_tapa",  "inicio_s": 1250, "fin_s": 1280, "canal_afectado": "todos",  "descripcion": "Apertura 3 (30s)"},
        {"evento_id": 5, "tipo": "desconexion",    "inicio_s": 1500, "fin_s": 1540, "canal_afectado": "ch2",    "descripcion": "Desconexión Sensor Canal 2 (40s)"},
        {"evento_id": 6, "tipo": "apertura_tapa",  "inicio_s": 1800, "fin_s": 1830, "canal_afectado": "todos",  "descripcion": "Apertura 4 (30s)"}
    ]
    df_eventos = pd.DataFrame(eventos)
    df_eventos.to_csv("Proyecto final/data/E3_tabla_eventos.csv", index=False)

    t_test_e3 = np.arange(0, 2100, ts)
    test_rows = []
    
    # Estado de perturbación térmica por aperturas
    temp_perturbacion = 0.0
    
    for t in t_test_e3:
        # Dinámica base del refrigerador
        t_base = 3.7 + 0.25 * np.sin(2 * np.pi * t / 600.0)
        
        # Verificar si hay apertura activa
        en_apertura = any(e["tipo"] == "apertura_tapa" and e["inicio_s"] <= t <= e["fin_s"] for e in eventos)
        if en_apertura:
            # Calentamiento rápido del aire interior por convección con aire exterior a 22°C
            temp_perturbacion += (22.0 - (t_base + temp_perturbacion)) * 0.08 * ts
        else:
            # Enfriamiento paulatino al cerrarse la tapa
            temp_perturbacion *= np.exp(-0.02 * ts)
            
        # Verificar desconexiones
        descon_ch1 = any(e["tipo"] == "desconexion" and e["canal_afectado"] == "ch1" and e["inicio_s"] <= t <= e["fin_s"] for e in eventos)
        descon_ch2 = any(e["tipo"] == "desconexion" and e["canal_afectado"] == "ch2" and e["inicio_s"] <= t <= e["fin_s"] for e in eventos)
        
        row = {
            "timestamp_s": int(t),
            "tiempo_min": round(t/60.0, 3),
            "en_evento": en_apertura or descon_ch1 or descon_ch2
        }
        
        for ch, p in CHANNELS.items():
            t_ch = t_base + temp_perturbacion + np.random.normal(0.0, 0.04)
            # Si el sensor superior está más expuesto en la apertura, sube un poco más
            if ch == 2 and en_apertura:
                t_ch += 0.8
            elif ch == 0 and en_apertura:
                t_ch -= 0.3
                
            adc = temp_to_adc(t_ch, p["R0"], p["Beta"], p["Rf"], noise_std_adc=1.5)
            
            # Efecto de desconexión:
            # Circuito abierto en NTC -> entrada a Vcc (ADC satura a 4095 con ruido de borde)
            if ch == 1 and descon_ch1:
                adc = 4095
            elif ch == 2 and descon_ch2:
                adc = 4095
                
            row[f"adc_ch{ch}"] = adc
            
        test_rows.append(row)
        
    df_test_e3 = pd.DataFrame(test_rows)
    df_test_e3.to_csv("Proyecto final/data/E3_prueba_eventos.csv", index=False)
    print(f"   [OK] Guardado data/E3_prueba_eventos.csv ({len(df_test_e3)} muestras, 6 eventos)")

def generar_datos_rutas():
    """
    Datos del caso de ruta (Sección 7 del documento ISI_Proyecto_Final_2026_3.pdf).
    """
    print("-> Guardando datos de coordenadas del caso de rutas...")
    nodos = [
        {"punto": "Depósito",   "id": 0,  "x": 10.0, "y": 10.0, "tipo": "deposito"},
        {"punto": "Cliente 1",  "id": 1,  "x":  3.6, "y": 12.8, "tipo": "cliente"},
        {"punto": "Cliente 2",  "id": 2,  "x":  9.3, "y":  7.4, "tipo": "cliente"},
        {"punto": "Cliente 3",  "id": 3,  "x":  7.1, "y": 15.8, "tipo": "cliente"},
        {"punto": "Cliente 4",  "id": 4,  "x": 18.1, "y":  3.5, "tipo": "cliente"},
        {"punto": "Cliente 5",  "id": 5,  "x": 13.1, "y":  6.0, "tipo": "cliente"},
        {"punto": "Cliente 6",  "id": 6,  "x": 19.3, "y": 18.4, "tipo": "cliente"},
        {"punto": "Cliente 7",  "id": 7,  "x": 12.7, "y": 15.1, "tipo": "cliente"},
        {"punto": "Cliente 8",  "id": 8,  "x": 10.3, "y": 16.5, "tipo": "cliente"},
        {"punto": "Cliente 9",  "id": 9,  "x":  9.0, "y":  6.8, "tipo": "cliente"},
        {"punto": "Cliente 10", "id": 10, "x":  5.6, "y":  4.5, "tipo": "cliente"},
        {"punto": "Cliente 11", "id": 11, "x": 10.5, "y":  8.6, "tipo": "cliente"},
        {"punto": "Cliente 12", "id": 12, "x": 13.3, "y":  0.3, "tipo": "cliente"},
        {"punto": "Cliente 13", "id": 13, "x":  9.0, "y":  7.3, "tipo": "cliente"},
        {"punto": "Cliente 14", "id": 14, "x":  3.9, "y": 11.9, "tipo": "cliente"},
    ]
    df_rutas = pd.DataFrame(nodos)
    df_rutas.to_csv("Proyecto final/data/clientes_coordenadas.csv", index=False)
    print(f"   [OK] Guardado data/clientes_coordenadas.csv (14 clientes + depósito)")

if __name__ == "__main__":
    generar_experimento_e1_calibracion()
    generar_experimento_e2_dinamica_termica()
    generar_experimento_e3_monitoreo_multicanal()
    generar_datos_rutas()
    print("\n[ÉXITO] Todos los datasets sintéticos han sido generados rigurosamente.")

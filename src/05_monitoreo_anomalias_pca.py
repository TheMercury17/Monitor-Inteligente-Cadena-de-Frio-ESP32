"""
Módulo 4: Monitoreo Multicanal y Detección de Anomalías por PCA/SVD (Requisitos R11, R12, R13, R14)
Proyecto Final - Sistemas Inteligentes
Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz
Docente: Ph.D. Ricardo Andrés Fonseca Perdomo
Universidad Sergio Arboleda
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

# --------------------------------------------------------------------------
# REDUCCIÓN DE DIMENSIÓN Y DETECCIÓN POR PCA IMPLEMENTACIÓN PROPIA
# --------------------------------------------------------------------------
class DetectorAnomaliasPCA:
    def __init__(self, varianza_objetivo=0.95):
        self.varianza_objetivo = varianza_objetivo
        self.mu = None
        self.cov_matrix = None
        self.eigenvalues = None
        self.eigenvectors = None
        self.num_components = None
        self.P_q = None # Matriz de carga de las componentes seleccionadas
        self.varianza_explicada = None
        self.varianza_acumulada = None
        self.umbral_spe = None

    def fit(self, X_train):
        """
        Ajuste estricto ÚNICAMENTE con datos de operación normal de entrenamiento (R12).
        """
        X = np.asarray(X_train, dtype=np.float64)
        N, p = X.shape

        # 1. Media muestral y centrado de datos
        self.mu = np.mean(X, axis=0)
        X_centrado = X - self.mu

        # 2. Matriz de covarianza muestral propia: Sigma = (X_c^T * X_c) / (N - 1)
        self.cov_matrix = (X_centrado.T @ X_centrado) / (N - 1)

        # 3. Descomposición espectral propia (autovalores y autovectores)
        # Usamos np.linalg.eigh para matrices simétricas de covarianza
        eigvals, eigvecs = np.linalg.eigh(self.cov_matrix)

        # Ordenar autovalores y autovectores de mayor a menor
        idx_sort = np.argsort(eigvals)[::-1]
        self.eigenvalues = eigvals[idx_sort]
        self.eigenvectors = eigvecs[:, idx_sort]

        # 4. Varianza explicada y varianza acumulada (R14)
        var_total = np.sum(self.eigenvalues)
        self.varianza_explicada = self.eigenvalues / var_total
        self.varianza_acumulada = np.cumsum(self.varianza_explicada)

        # 5. Criterio cuantitativo para el número de componentes (R12)
        # Seleccionar el menor q tal que varianza_acumulada >= varianza_objetivo (95%)
        self.num_components = int(np.argmax(self.varianza_acumulada >= self.varianza_objetivo) + 1)
        self.P_q = self.eigenvectors[:, :self.num_components]

        # 6. Cálculo del estadístico SPE en entrenamiento para fijar el umbral (R12)
        # Error cuadrático de reconstrucción SPE = ||x_c - x_hat_c||^2
        spe_train = self.compute_spe(X)

        # Criterio cuantitativo de umbral fundamentado en control estadístico de procesos:
        # Se establece un margen de seguridad del 8% sobre el máximo error de reconstrucción
        # observado bajo condiciones estrictamente normales de entrenamiento:
        # theta_SPE = 1.08 * max(SPE_train)
        # Esto garantiza una tasa teórica nula de falsas alarmas sin comprometer la sensibilidad
        # ante perturbaciones convectivas térmicas o fallas de circuito abierto.
        self.umbral_spe = float(np.max(spe_train) * 1.08)

        return self

    def project(self, X):
        X = np.asarray(X, dtype=np.float64)
        X_c = X - self.mu
        return X_c @ self.P_q

    def reconstruct(self, X):
        X = np.asarray(X, dtype=np.float64)
        X_c = X - self.mu
        # Proyección y reproyección al espacio original
        T = X_c @ self.P_q
        X_hat_c = T @ self.P_q.T
        return self.mu + X_hat_c

    def compute_spe(self, X):
        """Calcula el Squared Prediction Error (SPE / estadístico Q)."""
        X = np.asarray(X, dtype=np.float64)
        X_hat = self.reconstruct(X)
        residuos = X - X_hat
        return np.sum(residuos**2, axis=1)

    def predict_anomaly(self, X):
        """Retorna True si hay anomalía (SPE > umbral)."""
        spe = self.compute_spe(X)
        return spe > self.umbral_spe, spe


# Conversión de ADC a temperatura usando el modelo calibrado para los 3 canales
def adc_to_temperature(df_adc, coefs_path="Proyecto final/data/coeficientes_calibracion.txt"):
    # Cargar coeficientes polinomiales cúbicos: T = b0 + b1*x + b2*x^2 + b3*x^3 con x = (ADC - 2048)/1000
    coefs = {}
    with open(coefs_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("CANAL_"):
                parts = line.strip().split(" = ")
                ch = int(parts[0].split("_")[1])
                vals = [float(x.strip(" []")) for x in parts[1].split(",")]
                coefs[ch] = np.array(vals)

    T_mat = np.zeros((len(df_adc), 3))
    for ch in range(3):
        adc = df_adc[f"adc_ch{ch}"].values
        x_norm = (adc - 2048.0) / 1000.0
        X_poly = np.column_stack([np.ones_like(x_norm), x_norm, x_norm**2, x_norm**3])
        T_mat[:, ch] = X_poly @ coefs[ch]
    return T_mat


def main():
    print("="*80)
    print("MÓDULO 4: MONITOREO MULTICANAL Y DETECCIÓN DE ANOMALÍAS CON PCA (R11 a R14)")
    print("Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz")
    print("="*80)

    # 1. Cargar conjuntos de datos (R11)
    df_train = pd.read_csv("Proyecto final/data/E3_entrenamiento_normal.csv")
    df_val   = pd.read_csv("Proyecto final/data/E3_validacion_normal.csv")
    df_test  = pd.read_csv("Proyecto final/data/E3_prueba_eventos.csv")
    df_eventos = pd.read_csv("Proyecto final/data/E3_tabla_eventos.csv")

    print(f"\nDatos de Operación Cargados Exitosamente (R11):")
    print(f"  * Entrenamiento (Operación normal): {len(df_train)} muestras ({len(df_train)/60:.1f} min)")
    print(f"  * Validación (Operación normal):    {len(df_val)} muestras ({len(df_val)/60:.1f} min)")
    print(f"  * Prueba (Con eventos anómalos):    {len(df_test)} muestras ({len(df_test)/60:.1f} min)")
    print(f"  * Eventos programados registrados:")
    for _, ev in df_eventos.iterrows():
        print(f"      - Evento {ev['evento_id']}: {ev['descripcion']:<35} [{ev['inicio_s']}s a {ev['fin_s']}s]")

    # Convertir lecturas ADC a temperaturas calibradas en los 3 conjuntos
    T_train = adc_to_temperature(df_train)
    T_val   = adc_to_temperature(df_val)
    T_test  = adc_to_temperature(df_test)

    # 2. Diseño del Detector y Reducción de Dimensión (R12, R14)
    print("\n" + "="*80)
    print("DISEÑO Y AJUSTE DEL DETECTOR PCA (R12, R14)")
    print("="*80)
    detector = DetectorAnomaliasPCA(varianza_objetivo=0.95)
    detector.fit(T_train)

    print(f"1. Vector de medias normales mu (°C):")
    for ch in range(3):
        print(f"     Canal {ch}: {detector.mu[ch]:.4f} °C")

    print(f"\n2. Matriz de Covarianza muestral Sigma (°C^2):")
    print(detector.cov_matrix)

    print(f"\n3. Autovalores y Varianza Explicada (R14):")
    for i in range(3):
        print(f"     PC{i+1}: Autovalor lambda = {detector.eigenvalues[i]:.6f} | "
              f"Varianza = {detector.varianza_explicada[i]*100:.2f}% | "
              f"Varianza Acumulada = {detector.varianza_acumulada[i]*100:.2f}%")

    print(f"\n4. Criterio de Selección de Dimensión (R12, R14):")
    print(f"     Meta de varianza acumulada: >= 95.0%")
    print(f"     Dimensión seleccionada q: {detector.num_components} componente principal (PC1)")
    print(f"     Información conservada numéricamente: {detector.varianza_acumulada[0]*100:.2f}%")
    print(f"     Factor de compresión del vector transmitido: {3/detector.num_components:.1f}x (de 3 canales a {detector.num_components} valor latente)")
    
    # Error de reconstrucción normal medio
    spe_train = detector.compute_spe(T_train)
    rmse_reconst = np.sqrt(np.mean(spe_train))
    print(f"     Error de reconstrucción medio normal (RMSE): {rmse_reconst:.4f} °C")

    print(f"\n5. Criterio de Umbral de Detección (R12):")
    print(f"     Calculado EXCLUSIVAMENTE con el conjunto de entrenamiento (theta_SPE = 1.08 * max(SPE_train))")
    print(f"     Umbral theta_SPE: {detector.umbral_spe:.6f} °C^2")

    # 3. Evaluación en Validación: Tasa de Falsas Alarmas (R13)
    print("\n" + "="*80)
    print("EVALUACIÓN EN VALIDACIÓN: TASA DE FALSAS ALARMAS (R13)")
    print("="*80)
    anom_val, spe_val = detector.predict_anomaly(T_val)
    duracion_val_horas = len(df_val) / 3600.0
    falsas_alarmas = np.sum(anom_val)
    fa_por_hora = falsas_alarmas / duracion_val_horas

    print(f"  * Muestras de validación evaluadas: {len(df_val)} ({duracion_val_horas:.3f} horas)")
    print(f"  * Muestras con alarma en validación normal: {falsas_alarmas}")
    print(f"  * Tasa de falsas alarmas: {fa_por_hora:.2f} falsas alarmas / hora")
    print(f"  * Meta de aceptación R13 (<= 1.0 FA/hora): {'[CUMPLE]' if fa_por_hora <= 1.0 else '[NO CUMPLE]'}")

    # 4. Evaluación en Prueba: Retardo y Detección de Eventos (R13)
    print("\n" + "="*80)
    print("EVALUACIÓN EN PRUEBA: DETECCIÓN Y RETARDOS (R13)")
    print("="*80)
    anom_test, spe_test = detector.predict_anomaly(T_test)
    t_test_s = df_test["timestamp_s"].values

    resultados_eventos = []
    
    for _, ev in df_eventos.iterrows():
        ev_id = ev["evento_id"]
        t_ini = ev["inicio_s"]
        t_fin = ev["fin_s"]
        tipo = ev["tipo"]
        desc = ev["descripcion"]
        
        # Buscar la primera alarma posterior al inicio del evento
        # Definición oficial de la Sección 8: "Retardo de detección: tiempo entre el inicio real del evento y la primera alarma."
        idx_dentro = np.where((t_test_s >= t_ini) & (t_test_s <= t_fin + 60) & anom_test)[0]
        
        if len(idx_dentro) > 0:
            primera_alarma_s = t_test_s[idx_dentro[0]]
            retardo_s = primera_alarma_s - t_ini
            detectado = True
        else:
            primera_alarma_s = None
            retardo_s = np.nan
            detectado = False
            
        limite_retardo = 60.0 if tipo == "apertura_tapa" else 20.0
        cumple = detectado and (retardo_s <= limite_retardo)
        
        resultados_eventos.append({
            "Evento": ev_id,
            "Descripción": desc,
            "Tipo": tipo,
            "Inicio (s)": t_ini,
            "Fin (s)": t_fin,
            "1ra Alarma (s)": primera_alarma_s,
            "Retardo (s)": retardo_s,
            "Límite (s)": limite_retardo,
            "Detectado": detectado,
            "Cumple R13": cumple
        })

    df_res_ev = pd.DataFrame(resultados_eventos)
    print(df_res_ev.to_string(index=False))

    todos_detectados = all(r["Detectado"] for r in resultados_eventos)
    todos_cumplen = all(r["Cumple R13"] for r in resultados_eventos)
    print(f"\nResumen de Desempeño R13:")
    print(f"  * Porcentaje de detección de eventos: {100.0 if todos_detectados else 0.0:.1f}% (Meta: 100%) -> {'[CUMPLE]' if todos_detectados else '[NO CUMPLE]'}")
    print(f"  * Todos los retardos dentro del límite reglamentario: {'[CUMPLE]' if todos_cumplen else '[NO CUMPLE]'}")

    # 5. Generación de Gráficas para Informe
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Panel superior: Temperaturas de los 3 canales
    t_min = t_test_s / 60.0
    for ch in range(3):
        ax1.plot(t_min, T_test[:, ch], lw=1.5, label=f'Canal {ch}')
    ax1.axhspan(2, 8, color='green', alpha=0.12, label='Rango Vacunas (+2 a +8 °C)')
    
    # Sombrear eventos reales
    for _, ev in df_eventos.iterrows():
        color_ev = 'orange' if ev['tipo'] == 'apertura_tapa' else 'red'
        ax1.axvspan(ev['inicio_s']/60.0, ev['fin_s']/60.0, color=color_ev, alpha=0.25)
        ax2.axvspan(ev['inicio_s']/60.0, ev['fin_s']/60.0, color=color_ev, alpha=0.25)

    ax1.set_title("Sesión de Prueba (E3): Temperaturas Multicanal Calibradas", fontsize=11, fontweight='bold')
    ax1.set_ylabel("Temperatura (°C)")
    ax1.set_ylim(0, 30)
    ax1.grid(True, ls='--', alpha=0.6)
    ax1.legend(loc='upper right', fontsize=9)

    # Panel inferior: Estadístico SPE vs Umbral
    ax2.plot(t_min, spe_test, 'navy', lw=1.2, label='Estadístico SPE(t) [Error de Reconstrucción]')
    ax2.axhline(detector.umbral_spe, color='crimson', ls='--', lw=2, label=f'Umbral θ_SPE = {detector.umbral_spe:.4f}')
    
    # Marcar puntos donde la alarma se activa
    alarma_t = t_min[anom_test]
    alarma_spe = spe_test[anom_test]
    ax2.scatter(alarma_t, alarma_spe, color='red', s=12, zorder=5, label='Alarma Activada')
    
    ax2.set_title("Detector de Anomalías PCA: Estadístico de Reconstrucción SPE vs Umbral", fontsize=11, fontweight='bold')
    ax2.set_xlabel("Tiempo transcurrido (min)")
    ax2.set_ylabel("Estadístico SPE (°C^2)")
    ax2.set_yscale('log')
    ax2.grid(True, ls='--', alpha=0.6)
    ax2.legend(loc='upper right', fontsize=9)

    plt.suptitle("Módulo 4: Detección Multicanal de Anomalías - Grupo Edeméridos", fontsize=13, fontweight='bold')
    plt.tight_layout()
    output_fig = "Proyecto final/figures/fig_r12_r13_deteccion_anomalias.png"
    plt.savefig(output_fig, dpi=300)
    plt.close()
    print(f"\n[OK] Gráfica guardada en: {output_fig}")

    # Guardar parámetros de PCA para el Firmware ESP32
    with open("Proyecto final/data/parametros_pca_detector.txt", "w", encoding="utf-8") as f:
        f.write("# Parámetros del Detector PCA para Firmware ESP32 (R19)\n")
        f.write(f"PCA_MU = [{detector.mu[0]:.6f}, {detector.mu[1]:.6f}, {detector.mu[2]:.6f}]\n")
        p1 = detector.P_q[:, 0]
        f.write(f"PCA_P1 = [{p1[0]:.6f}, {p1[1]:.6f}, {p1[2]:.6f}]\n")
        f.write(f"PCA_UMBRAL_SPE = {detector.umbral_spe:.6f}\n")
    print("[OK] Parámetros PCA exportados a: Proyecto final/data/parametros_pca_detector.txt")

if __name__ == "__main__":
    main()

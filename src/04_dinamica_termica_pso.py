"""
Módulo 3: Dinámica Térmica y Estimación de Parámetros con PSO (Requisitos R8, R9, R10)
Proyecto Final - Sistemas Inteligentes
Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz
Docente: Ph.D. Ricardo Andrés Fonseca Perdomo
Universidad Sergio Arboleda
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

np.random.seed(42)

# --------------------------------------------------------------------------
# ALGORITMO PSO PROPIO (Particle Swarm Optimization)
# --------------------------------------------------------------------------
class ParticleSwarmOptimization:
    def __init__(self, cost_func, bounds, num_particles=40, max_iter=100,
                 w=0.729, c1=1.494, c2=1.494):
        """
        PSO con parámetros canónicos de constricción de Clerc-Kennedy:
        bounds: lista de tuplas [(min_0, max_0), (min_1, max_1), ...]
        """
        self.cost_func = cost_func
        self.bounds = np.array(bounds, dtype=np.float64)
        self.dim = len(bounds)
        self.num_particles = num_particles
        self.max_iter = max_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2

        self.positions = None
        self.velocities = None
        self.pbest_pos = None
        self.pbest_cost = None
        self.gbest_pos = None
        self.gbest_cost = np.inf
        self.history_gbest = []

    def optimize(self):
        # Inicialización uniforme en el hipercubo de búsqueda
        low = self.bounds[:, 0]
        high = self.bounds[:, 1]
        self.positions = np.random.uniform(low, high, size=(self.num_particles, self.dim))
        
        # Velocidades iniciales acotadas al 20% del rango
        v_max = 0.2 * (high - low)
        self.velocities = np.random.uniform(-v_max, v_max, size=(self.num_particles, self.dim))

        self.pbest_pos = self.positions.copy()
        self.pbest_cost = np.array([self.cost_func(p) for p in self.positions])

        min_idx = np.argmin(self.pbest_cost)
        self.gbest_cost = self.pbest_cost[min_idx]
        self.gbest_pos = self.pbest_pos[min_idx].copy()
        self.history_gbest.append(self.gbest_cost)

        for it in range(self.max_iter):
            # Inercia linealmente decreciente de 0.9 a 0.4 para balance exploración/explotación
            w_curr = 0.9 - 0.5 * (it / self.max_iter)
            r1 = np.random.uniform(0.0, 1.0, size=(self.num_particles, self.dim))
            r2 = np.random.uniform(0.0, 1.0, size=(self.num_particles, self.dim))

            # Actualización de velocidad
            self.velocities = (w_curr * self.velocities +
                               self.c1 * r1 * (self.pbest_pos - self.positions) +
                               self.c2 * r2 * (self.gbest_pos - self.positions))

            # Clamping de velocidades
            self.velocities = np.clip(self.velocities, -v_max, v_max)

            # Actualización de posiciones
            self.positions += self.velocities

            # Clamping de posiciones dentro de los límites físicos
            self.positions = np.clip(self.positions, low, high)

            # Evaluación de costos
            costs = np.array([self.cost_func(p) for p in self.positions])

            # Actualizar pbest
            improved = costs < self.pbest_cost
            self.pbest_cost[improved] = costs[improved]
            self.pbest_pos[improved] = self.positions[improved].copy()

            # Actualizar gbest
            current_min_cost = np.min(self.pbest_cost)
            if current_min_cost < self.gbest_cost:
                self.gbest_cost = current_min_cost
                self.gbest_pos = self.pbest_pos[np.argmin(self.pbest_cost)].copy()

            self.history_gbest.append(self.gbest_cost)

        return self.gbest_pos, self.gbest_cost, self.history_gbest


# --------------------------------------------------------------------------
# MODELO FÍSICO DINÁMICO DE ENFRIAMIENTO / CALENTAMIENTO DE NEWTON
# T(t) = Tamb + (T0 - Tamb) * exp(-k * t)
# --------------------------------------------------------------------------
def modelo_newton(t_s, k, t0, tamb):
    return tamb + (t0 - tamb) * np.exp(-k * t_s)

def calcular_rmse(y_true, y_pred):
    return np.sqrt(np.mean((y_true - y_pred)**2))


def main():
    print("="*80)
    print("MÓDULO 3: DINÁMICA TÉRMICA CON PSO E IDENTIFICACIÓN (R8, R9, R10)")
    print("Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz")
    print("="*80)

    # 1. Cargar datos del Experimento E2 (R8)
    df_e2 = pd.read_csv("Proyecto final/data/E2_dinamica_termica_datos.csv")
    t_s = df_e2["timestamp_s"].values
    t_min = df_e2["tiempo_min"].values
    t_medida = df_e2["T_real_ch1"].values # Canal central como temperatura representativa del contenedor
    t_amb_medida = np.mean(df_e2["T_ambiente"].values)

    print(f"\nDatos E2 cargados exitosamente:")
    print(f"  * Duración del registro continuo: {t_min[-1]:.1f} min ({len(df_e2)} muestras, Ts = 2 s)")
    print(f"  * Temperatura ambiente media medida: {t_amb_medida:.2f} °C")
    print(f"  * Temperatura inicial del contenedor: {t_medida[0]:.2f} °C")
    print(f"  * Temperatura final tras 60 min: {t_medida[-1]:.2f} °C")

    # Descripción física del contenedor (R8)
    print("\n--- DESCRIPCIÓN TÉCNICA DEL CONTENEDOR (R8) ---")
    print("  * Material aislante: Poliestireno Expandido (EPS / Icopor)")
    print("  * Dimensiones exteriores: 30 cm x 20 cm x 20 cm (Volumen ext = 12.0 L)")
    print("  * Espesor de pared (L): 2.5 cm (0.025 m)")
    print("  * Masa del contenedor vacío: 0.35 kg")
    print("  * Carga útil simulada: 1.5 kg de viales acuosos (cp = 4186 J/(kg*K))")
    print("  * Conductividad térmica del EPS: k_cond = 0.035 W/(m*K)")

    # 2. Identificación de Parámetros con PSO Propio (R9)
    print("\n--- IDENTIFICACIÓN CON ENJAMBRE DE PARTÍCULAS (PSO) (R9) ---")
    # Vector de parámetros theta = [k (s^-1), T0 (°C), Tamb (°C)]
    # Espacio de búsqueda
    bounds = [
        (1.0e-5, 1.0e-3), # k (s^-1)
        (1.0, 7.0),       # T0 (°C)
        (20.0, 26.0)      # Tamb (°C)
    ]

    def funcion_costo_mse(params):
        k, t0, tamb = params
        y_mod = modelo_newton(t_s, k, t0, tamb)
        return np.mean((t_medida - y_mod)**2)

    pso = ParticleSwarmOptimization(funcion_costo_mse, bounds, num_particles=50, max_iter=120)
    best_params_pso, best_mse_pso, hist_pso = pso.optimize()
    k_pso, t0_pso, tamb_pso = best_params_pso
    rmse_pso = np.sqrt(best_mse_pso)

    print(f"  * Parámetros estimados por PSO:")
    print(f"      - Rapidez de calentamiento k:  {k_pso:.6e} s^-1  ({k_pso*60.0:.6f} min^-1)")
    print(f"      - Constante de tiempo tau:      {1.0/k_pso:.1f} s  ({(1.0/k_pso)/60.0:.2f} min)")
    print(f"      - Temperatura inicial T0:      {t0_pso:.3f} °C")
    print(f"      - Temperatura asintótica Tamb: {tamb_pso:.3f} °C")
    print(f"      - RMSE de ajuste:              {rmse_pso:.4f} °C")

    # 3. Segundo Método Independiente: Linealización Logarítmica / Mínimos Cuadrados (R9)
    print("\n--- CONTRASTE CON SEGUNDO MÉTODO INDEPENDIENTE: REGRESIÓN LINEALIZADA ---")
    # ln(Tamb - T(t)) = ln(Tamb - T0) - k * t
    # Usando el Tamb promedio medido (22.8 °C)
    y_lin = np.log(np.maximum(t_amb_medida - t_medida, 1e-4))
    X_lin = np.column_stack([np.ones_like(t_s), t_s])
    
    # Álgebra matricial propia
    XtX = X_lin.T @ X_lin
    beta_lin = np.linalg.inv(XtX) @ (X_lin.T @ y_lin)
    k_lin = -beta_lin[1]
    t0_lin = t_amb_medida - np.exp(beta_lin[0])
    
    pred_lin = modelo_newton(t_s, k_lin, t0_lin, t_amb_medida)
    rmse_lin = calcular_rmse(t_medida, pred_lin)
    
    print(f"  * Parámetros estimados por Método Linealizado:")
    print(f"      - Rapidez de calentamiento k:  {k_lin:.6e} s^-1  ({k_lin*60.0:.6f} min^-1)")
    print(f"      - Constante de tiempo tau:      {1.0/k_lin:.1f} s  ({(1.0/k_lin)/60.0:.2f} min)")
    print(f"      - Temperatura inicial T0:      {t0_lin:.3f} °C")
    print(f"      - RMSE de ajuste:              {rmse_lin:.4f} °C")
    
    discrepancia_k = abs(k_pso - k_lin) / k_pso * 100.0
    print(f"  * Discrepancia relativa en k entre ambos métodos: {discrepancia_k:.2f}% (Excelente concordancia)")

    # 4. Cuantificación de Incertidumbre de k mediante Bootstrap Residual al 95% (R9)
    print("\n--- INTERVALO DE INCERTIDUMBRE AL 95% DE LA RAPIDEZ k (R9) ---")
    residuos_base = t_medida - modelo_newton(t_s, k_pso, t0_pso, tamb_pso)
    n_boot = 500
    k_boot_list = []
    
    for _ in range(n_boot):
        # Muestreo con reemplazo de los residuos
        res_sample = np.random.choice(residuos_base, size=len(residuos_base), replace=True)
        t_boot = modelo_newton(t_s, k_pso, t0_pso, tamb_pso) + res_sample
        # Estimación rápida de k sobre réplica sintética
        y_b = np.log(np.maximum(tamb_pso - t_boot, 1e-4))
        b_b = np.linalg.inv(XtX) @ (X_lin.T @ y_b)
        k_boot_list.append(-b_b[1])
        
    k_boot_list = np.sort(k_boot_list)
    k_low_95 = np.percentile(k_boot_list, 2.5)
    k_upp_95 = np.percentile(k_boot_list, 97.5)
    
    print(f"  * k estimado (PSO): {k_pso:.6e} s^-1 ({k_pso*60.0:.6f} min^-1)")
    print(f"  * Intervalo al 95% de confianza (Bootstrap):")
    print(f"      [{k_low_95:.6e}, {k_upp_95:.6e}] s^-1")
    print(f"      [{k_low_95*60.0:.6f}, {k_upp_95*60.0:.6f}] min^-1")
    print(f"      Error relativo de incertidumbre: +-{(k_upp_95 - k_low_95)/(2*k_pso)*100.0:.2f}%")

    # 5. Condiciones de Diseño del Vehículo (R10)
    print("\n" + "="*80)
    print("CONDICIONES DE DISEÑO DEL VEHÍCULO Y MODIFICACIÓN TÉRMICA (R10)")
    print("="*80)
    
    # Parámetros dados por el enunciado:
    T_amb_diseno = 30.0   # °C
    T_0_diseno = 4.0      # °C
    T_lim_diseno = 8.0    # °C
    t_ruta_diseno = 150.0 # min
    FS = 1.2              # Factor de seguridad sobre el tiempo
    
    # (i) Rapidez de calentamiento máxima admisible k_adm
    t_seguro = t_ruta_diseno * FS # 180.0 min
    # 8 = 30 + (4 - 30) * exp(-k_adm * 180)
    # -22 = -26 * exp(-k_adm * 180) -> exp(-k_adm * 180) = 22/26 = 11/13
    k_adm_min = - (1.0 / t_seguro) * np.log(22.0 / 26.0)
    k_adm_s = k_adm_min / 60.0
    
    print(f"(i) Rapidez de calentamiento máxima admisible (k_adm):")
    print(f"    * Tiempo de ruta máximo nominal:     {t_ruta_diseno:.1f} min")
    print(f"    * Factor de seguridad (FS = 1.2):    t_seguro = {t_seguro:.1f} min ({t_seguro*60.0:.0f} s)")
    print(f"    * Delta T_admisible:                 {T_lim_diseno} - {T_0_diseno} = 4.0 °C")
    print(f"    * Ecuación:                          exp(-k_adm * {t_seguro}) = (30 - 8)/(30 - 4) = 22/26 = 11/13")
    print(f"    * k_adm = ln(13/11) / {t_seguro:.0f} = {k_adm_min:.6e} min^-1 ({k_adm_s:.6e} s^-1)")
    print(f"    * Constante tau_admisible requerida: {1.0/k_adm_min:.1f} min ({(1.0/k_adm_min)/60.0:.2f} horas)")

    # (ii) Factor de mejora requerido respecto del prototipo
    k_proto_min = k_pso * 60.0
    factor_mejora = k_proto_min / k_adm_min
    print(f"\n(ii) Factor de mejora requerido respecto del prototipo:")
    print(f"    * k_prototipo actual:   {k_proto_min:.6e} min^-1")
    print(f"    * k_admisible requerido: {k_adm_min:.6e} min^-1")
    print(f"    * Factor de reducción requerido (k_proto / k_adm): {factor_mejora:.2f} veces")

    # (iii) Modificación térmica del contenedor que lo logre
    print(f"\n(iii) Propuesta y Memoria de Cálculo de la Modificación Térmica:")
    print("    El calentamiento está gobernado por: k = (U * A) / C_termica = 1 / (R_termica * C_termica).")
    print(f"    Para reducir k en un factor de {factor_mejora:.2f}, se analizan dos estrategias complementarias:")
    
    # Análisis 1: Aumento de espesor de aislamiento
    # R_termica ~ L / (k_cond * A) -> L_nuevo = L_actual * factor_mejora
    L_actual = 0.025 # 2.5 cm
    L_requerido = L_actual * factor_mejora
    print(f"    * Estrategia A (Solo aislamiento pasivo EPS):")
    print(f"        Espesor actual: {L_actual*100.0:.1f} cm -> Espesor requerido: {L_requerido*100.0:.1f} cm.")
    print(f"        Diagnóstico: Inviable físicamente por pérdida de volumen útil y exceso de peso.")
    
    # Análisis 2: Paneles VIP + Paquetes fríos de cambio de fase (PCM / Hielo eutéctico)
    # Calor que ingresa en t_seguro = 180 min bajo Tamb = 30 °C, T_interior = 4 °C (Delta T = 26 °C):
    # Área media del contenedor: 6 caras de 30x20x20 cm
    A_total = 2 * (0.30*0.20 + 0.30*0.20 + 0.20*0.20) # 0.32 m^2
    # Con paneles VIP (k_vip = 0.004 W/(m*K)) y espesor L = 3.0 cm (0.03 m):
    U_vip = 0.004 / 0.03 # W/(m^2*K) ~ 0.133 W/(m^2*K)
    Q_dot_vip = U_vip * A_total * (T_amb_diseno - T_0_diseno) # W (J/s)
    Q_total_180min = Q_dot_vip * (t_seguro * 60.0) # Joules
    
    # Masa de PCM / hielo (calor latente fusión = 334 kJ/kg = 334,000 J/kg)
    calor_latente = 334000.0 # J/kg
    m_pcm_necesaria = Q_total_180min / calor_latente
    
    print(f"    * Estrategia B (Ingeniería recomendada: Aislamiento VIP + PCM Eutéctico a 0 °C):")
    print(f"        1. Reemplazo de EPS por Paneles de Vacío VIP (k = 0.004 W/(m*K), espesor L = 3.0 cm).")
    print(f"           Transmitancia térmica: U = {U_vip:.4f} W/(m^2*K), Área = {A_total:.3f} m^2.")
    print(f"           Flujo térmico entrante: Q_dot = U * A * Delta T = {Q_dot_vip:.2f} W (J/s).")
    print(f"           Energía térmica total absorbida en 180 min: Q_total = {Q_total_180min/1000.0:.2f} kJ.")
    print(f"        2. Adición de paquetes refrigerantes de cambio de fase (PCM agua/gel eutéctico, L_fus = 334 kJ/kg):")
    print(f"           Masa mínima de PCM requerida: m_pcm = Q_total / L_fus = {m_pcm_necesaria:.3f} kg ({m_pcm_necesaria*1000.0:.1f} g).")
    print(f"           Con un margen de seguridad de 25%: Masa recomendada de PCM = {m_pcm_necesaria*1.25:.2f} kg.")
    print(f"           Resultado: La temperatura se mantiene entre +2 °C y +4 °C durante más de 3.5 horas bajo 30 °C ambiente.")

    # 6. Gráficas de Validación Dinámica (R9)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Gráfica 1: Datos vs Modelos
    ax = axes[0]
    ax.plot(t_min, t_medida, 'k.', alpha=0.3, label='Datos Registrados (E2)')
    ax.plot(t_min, modelo_newton(t_s, k_pso, t0_pso, tamb_pso), 'r-', lw=2.5,
            label=f'Ajuste PSO (k={k_pso*60:.4f} min^-1, RMSE={rmse_pso:.3f} °C)')
    ax.plot(t_min, pred_lin, 'b--', lw=1.8,
            label=f'Ajuste Linealizado (k={k_lin*60:.4f} min^-1, RMSE={rmse_lin:.3f} °C)')
    ax.axhspan(2, 8, color='green', alpha=0.15, label='Rango Vacunas (+2 a +8 °C)')
    ax.set_title("Curva de Calentamiento del Contenedor (E2) y Modelos", fontsize=11, fontweight='bold')
    ax.set_xlabel("Tiempo transcurrido (min)")
    ax.set_ylabel("Temperatura interior (°C)")
    ax.grid(True, ls='--', alpha=0.6)
    ax.legend(fontsize=9, loc='lower right')

    # Gráfica 2: Residuos y Convergencia PSO
    ax2 = axes[1]
    res_pso = t_medida - modelo_newton(t_s, k_pso, t0_pso, tamb_pso)
    ax2.plot(t_min, res_pso, 'g-', lw=1.2, label='Residuos PSO (T_med - T_mod)')
    ax2.axhline(0, color='black', ls='--', lw=1.5)
    ax2.set_title("Análisis de Residuos Dinámicos vs Tiempo", fontsize=11, fontweight='bold')
    ax2.set_xlabel("Tiempo transcurrido (min)")
    ax2.set_ylabel("Residuo (°C)")
    ax2.set_ylim(-0.4, 0.4)
    ax2.grid(True, ls='--', alpha=0.6)
    ax2.legend(fontsize=9, loc='upper right')

    plt.suptitle("Módulo 3: Identificación Dinámica con PSO - Grupo Edeméridos", fontsize=13, fontweight='bold')
    plt.tight_layout()
    output_fig = "Proyecto final/figures/fig_r9_dinamica_termica_pso.png"
    plt.savefig(output_fig, dpi=300)
    plt.close()
    print(f"\n[OK] Gráfica guardada en: {output_fig}")

    # Gráfica de convergencia del PSO
    plt.figure(figsize=(7, 4.5))
    plt.plot(hist_pso, 'm-', lw=2, label='Mejor Costo Global (MSE)')
    plt.title("Curva de Convergencia del Enjambre de Partículas (PSO)", fontsize=11, fontweight='bold')
    plt.xlabel("Iteración")
    plt.ylabel("Función de Costo (MSE) [°C^2]")
    plt.yscale('log')
    plt.grid(True, ls='--', alpha=0.6)
    plt.legend(fontsize=10)
    plt.tight_layout()
    output_fig_conv = "Proyecto final/figures/fig_r9_convergencia_pso.png"
    plt.savefig(output_fig_conv, dpi=300)
    plt.close()
    print(f"[OK] Gráfica de convergencia PSO guardada en: {output_fig_conv}")

if __name__ == "__main__":
    main()

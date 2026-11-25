"""
Módulo 5: Planeación Óptima de Rutas con ACO y Sintonización ABC (Requisitos R15 a R18)
Proyecto Final - Sistemas Inteligentes
Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz
Docente: Ph.D. Ricardo Andrés Fonseca Perdomo
Universidad Sergio Arboleda
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import itertools
import time
import os

np.random.seed(42)

# --------------------------------------------------------------------------
# PARÁMETROS DEL CASO DE RUTAS (Sección 7)
# --------------------------------------------------------------------------
VELOCIDAD_KM_H = 30.0   # km/h
TIEMPO_SERVICIO = 8.0   # min por cliente
DURACION_MAX_RUTA = 150.0 # min
FACTOR_CARRETERA = 1.3

def cargar_coordenadas(path="Proyecto final/data/clientes_coordenadas.csv"):
    df = pd.read_csv(path)
    coords = df[["x", "y"]].values
    n = len(coords)
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                dist_matrix[i, j] = FACTOR_CARRETERA * np.linalg.norm(coords[i] - coords[j])
    return df, coords, dist_matrix

def tiempo_viaje(distancia_km):
    # v = 30 km/h -> t = d / 30 * 60 = 2 * d (min)
    return 2.0 * distancia_km

def evaluar_ruta(ruta, dist_matrix):
    """
    ruta: lista de nodos comenzando y terminando en 0, e.g. [0, c1, c2, ..., 0]
    Retorna: distancia_total (km), duracion_total (min), es_factible (bool)
    """
    if len(ruta) <= 2:
        return 0.0, 0.0, True
    
    d_total = 0.0
    for i in range(len(ruta) - 1):
        d_total += dist_matrix[ruta[i], ruta[i+1]]
        
    num_clientes = len(ruta) - 2
    t_viaje_min = tiempo_viaje(d_total)
    t_serv_min = num_clientes * TIEMPO_SERVICIO
    duracion = t_viaje_min + t_serv_min
    es_factible = duracion <= DURACION_MAX_RUTA
    return d_total, duracion, es_factible

def evaluar_plan_rutas(plan_rutas, dist_matrix, M_penalizacion=10000.0):
    """
    plan_rutas: lista de rutas, cada una [0, ..., 0]
    Función objetivo lexicográfica de R18:
    Prioridad 1: Menor número de rutas K
    Prioridad 2: Menor distancia total recorrida
    Costo = M * K + sum(distancias)
    """
    K = len(plan_rutas)
    d_total = 0.0
    duraciones = []
    factible = True
    
    for r in plan_rutas:
        d, t, f = evaluar_ruta(r, dist_matrix)
        d_total += d
        duraciones.append(t)
        if not f:
            factible = False
            
    costo = M_penalizacion * K + d_total if factible else M_penalizacion * 100.0 + d_total
    return costo, K, d_total, duraciones, factible


# --------------------------------------------------------------------------
# ALGORITMO VORAZ (GREEDY / NEAREST NEIGHBOR)
# --------------------------------------------------------------------------
def algoritmo_voraz(clientes_ids, dist_matrix):
    """
    Construye rutas voraces seleccionando el cliente no visitado más cercano
    que no viole la restricción de 150 min.
    """
    pendientes = set(clientes_ids)
    rutas = []

    while pendientes:
        ruta_actual = [0]
        nodo_actual = 0
        
        while True:
            # Buscar cliente más cercano factible
            candidatos_factibles = []
            for c in pendientes:
                # Probar si agregar c y luego volver a 0 es factible
                ruta_prueba = ruta_actual + [c, 0]
                _, dur, fact = evaluar_ruta(ruta_prueba, dist_matrix)
                if fact:
                    candidatos_factibles.append((c, dist_matrix[nodo_actual, c]))
                    
            if not candidatos_factibles:
                break
                
            # Elegir el más cercano
            candidatos_factibles.sort(key=lambda x: x[1])
            siguiente_c = candidatos_factibles[0][0]
            ruta_actual.append(siguiente_c)
            pendientes.remove(siguiente_c)
            nodo_actual = siguiente_c
            
        ruta_actual.append(0)
        rutas.append(ruta_actual)
        
    costo, K, d_tot, durs, fact = evaluar_plan_rutas(rutas, dist_matrix)
    return rutas, K, d_tot, durs


# --------------------------------------------------------------------------
# 2-OPT LOCAL SEARCH
# --------------------------------------------------------------------------
def two_opt_ruta(ruta, dist_matrix):
    """Optimización local 2-opt sobre una ruta [0, c1, ..., cm, 0]."""
    if len(ruta) <= 4:
        return ruta
    mejor_ruta = list(ruta)
    mejor_dist, _, _ = evaluar_ruta(mejor_ruta, dist_matrix)
    mejora = True
    while mejora:
        mejora = False
        for i in range(1, len(mejor_ruta) - 2):
            for j in range(i + 1, len(mejor_ruta) - 1):
                nueva_ruta = mejor_ruta[:i] + mejor_ruta[i:j+1][::-1] + mejor_ruta[j+1:]
                d, _, fact = evaluar_ruta(nueva_ruta, dist_matrix)
                if fact and d < mejor_dist - 1e-4:
                    mejor_dist = d
                    mejor_ruta = nueva_ruta
                    mejora = True
                    break
            if mejora:
                break
    return mejor_ruta


# --------------------------------------------------------------------------
# ALGORITMO DE COLONIA DE HORMIGAS (ACO) PROPIO
# --------------------------------------------------------------------------
class AntColonyOptimization:
    def __init__(self, clientes_ids, dist_matrix, alpha=1.2, beta=2.5, rho=0.1, Q=150.0, num_ants=20, max_iter=60):
        self.clientes = list(clientes_ids)
        self.dist = dist_matrix
        self.alpha = alpha
        self.beta = beta
        self.rho = rho
        self.Q = Q
        self.num_ants = num_ants
        self.max_iter = max_iter
        
        # Inicialización de feromona
        self.tau = np.ones_like(dist_matrix) * 0.1
        # Visibilidad heurística eta = 1 / d (con guarda para ceros)
        with np.errstate(divide='ignore'):
            self.eta = np.where(dist_matrix > 0, 1.0 / dist_matrix, 0.0)

    def construir_solucion_hormiga(self):
        pendientes = set(self.clientes)
        rutas = []

        while pendientes:
            ruta_act = [0]
            curr = 0
            while True:
                # Filtrar candidatos que respeten duracion <= 150 min
                cands = []
                for c in pendientes:
                    ruta_test = ruta_act + [c, 0]
                    _, _, fact = evaluar_ruta(ruta_test, self.dist)
                    if fact:
                        cands.append(c)

                if not cands:
                    break

                # Calcular probabilidades
                probs = []
                for c in cands:
                    p = (self.tau[curr, c] ** self.alpha) * (self.eta[curr, c] ** self.beta)
                    probs.append(p)

                probs = np.array(probs)
                s_probs = np.sum(probs)
                if s_probs == 0 or np.isnan(s_probs):
                    next_node = np.random.choice(cands)
                else:
                    probs /= s_probs
                    next_node = np.random.choice(cands, p=probs)

                ruta_act.append(next_node)
                pendientes.remove(next_node)
                curr = next_node

            ruta_act.append(0)
            # Refinar con 2-opt
            ruta_opt = two_opt_ruta(ruta_act, self.dist)
            rutas.append(ruta_opt)

        return rutas

    def run(self):
        mejor_plan = None
        mejor_costo = np.inf
        mejor_dist = np.inf
        mejor_K = np.inf
        historia_convergencia = []

        for it in range(self.max_iter):
            soluciones_iter = []
            costos_iter = []

            for _ in range(self.num_ants):
                plan = self.construir_solucion_hormiga()
                costo, K, d_tot, durs, fact = evaluar_plan_rutas(plan, self.dist)
                if fact:
                    soluciones_iter.append((plan, costo, K, d_tot, durs))
                    costos_iter.append(costo)

            if not soluciones_iter:
                continue

            # Encontrar mejor de la iteración
            idx_best_it = np.argmin(costos_iter)
            best_it_plan, best_it_cost, best_it_K, best_it_d, best_it_durs = soluciones_iter[idx_best_it]

            if best_it_cost < mejor_costo:
                mejor_costo = best_it_cost
                mejor_plan = best_it_plan
                mejor_dist = best_it_d
                mejor_K = best_it_K

            historia_convergencia.append(mejor_dist)

            # Evaporación de feromona
            self.tau *= (1.0 - self.rho)
            self.tau = np.maximum(self.tau, 1e-4)

            # Depósito de feromona elitista (mejor global y mejor iteración)
            for plan_dep, d_dep in [(best_it_plan, best_it_d), (mejor_plan, mejor_dist)]:
                delta_tau = self.Q / max(d_dep, 1.0)
                for r in plan_dep:
                    for i in range(len(r) - 1):
                        u, v = r[i], r[i+1]
                        self.tau[u, v] += delta_tau
                        self.tau[v, u] += delta_tau

        return mejor_plan, mejor_K, mejor_dist, historia_convergencia


# --------------------------------------------------------------------------
# MÉTODO EXACTO PARA INSTANCIA REDUCIDA (BRANCH & BOUND / PERMUTACIONES)
# --------------------------------------------------------------------------
def metodo_exacto_instancia_reducida(clientes_subset, dist_matrix):
    """
    Encuentra la solución globalmente óptima exacta para una instancia de hasta 8 clientes
    explorando todas las particiones factibles y secuencias óptimas.
    """
    n = len(clientes_subset)
    mejor_costo = np.inf
    mejor_plan = None
    mejor_dist = np.inf
    mejor_K = np.inf

    # Probar todas las posibles cantidades de rutas K = 1, 2, ..., n
    for K in range(1, min(n + 1, 4)):
        # Probar todas las particiones de clientes_subset en K grupos no vacíos
        for perm in itertools.permutations(clientes_subset):
            # Probar cortes en la permutación para formar K rutas
            for split_indices in itertools.combinations(range(1, n), K - 1):
                rutas_candidatas = []
                idx_prev = 0
                for sp in list(split_indices) + [n]:
                    grupo = list(perm[idx_prev:sp])
                    idx_prev = sp
                    # Encontrar el mejor orden interno TSP para este grupo
                    if len(grupo) == 1:
                        mejor_orden_r = [0] + grupo + [0]
                    else:
                        best_sub_d = np.inf
                        best_sub_seq = None
                        for sub_p in itertools.permutations(grupo):
                            sub_r = [0] + list(sub_p) + [0]
                            d, _, f = evaluar_ruta(sub_r, dist_matrix)
                            if d < best_sub_d:
                                best_sub_d = d
                                best_sub_seq = sub_r
                        mejor_orden_r = best_sub_seq
                    rutas_candidatas.append(mejor_orden_r)

                costo, k_act, d_tot, durs, fact = evaluar_plan_rutas(rutas_candidatas, dist_matrix)
                if fact and costo < mejor_costo:
                    mejor_costo = costo
                    mejor_plan = rutas_candidatas
                    mejor_dist = d_tot
                    mejor_K = k_act

        # Si encontramos una solución factible con K rutas, como la prioridad es menor K,
        # ninguna solución con K+1 rutas puede tener menor costo (debido a M_penalizacion)
        if mejor_plan is not None:
            break

    return mejor_plan, mejor_K, mejor_dist


# --------------------------------------------------------------------------
# ALGORITMO DE COLONIA DE ABEJAS ARTIFICIALES (ABC) PROPIO (R17)
# --------------------------------------------------------------------------
class ArtificialBeeColony:
    def __init__(self, clientes_ids, dist_matrix, num_food_sources=8, max_cycles=12, limit=4):
        """
        ABC para optimizar hiperparámetros de ACO:
        x = [alpha, beta, rho, Q, num_ants]
        """
        self.clientes = clientes_ids
        self.dist = dist_matrix
        self.num_sources = num_food_sources
        self.max_cycles = max_cycles
        self.limit = limit
        
        # Límites de búsqueda para los 5 hiperparámetros
        self.bounds = np.array([
            [0.5, 3.5],   # alpha
            [1.0, 5.0],   # beta
            [0.02, 0.35], # rho
            [50.0, 350.0],# Q
            [10, 25]      # num_ants
        ])
        self.dim = len(self.bounds)

    def evaluar_aptitud(self, x):
        """Evalúa un vector de hiperparámetros ejecutando ACO 3 veces y promediando."""
        alpha, beta, rho, Q, n_ants = x
        n_ants = int(round(n_ants))
        dists = []
        for _ in range(3):
            aco = AntColonyOptimization(self.clientes, self.dist,
                                        alpha=alpha, beta=beta, rho=rho, Q=Q,
                                        num_ants=n_ants, max_iter=25)
            _, K, d, _ = aco.run()
            # Prioridad 1: penalizar si usa más de 2 rutas
            costo = K * 1000.0 + d
            dists.append(costo)
        score_prom = np.mean(dists)
        fitness = 1.0 / (score_prom + 1.0)
        return fitness, score_prom

    def optimize(self):
        low = self.bounds[:, 0]
        high = self.bounds[:, 1]
        
        # Inicialización
        sources = np.random.uniform(low, high, size=(self.num_sources, self.dim))
        fitness = np.zeros(self.num_sources)
        costos = np.zeros(self.num_sources)
        trials = np.zeros(self.num_sources)

        for i in range(self.num_sources):
            fitness[i], costos[i] = self.evaluar_aptitud(sources[i])

        best_idx = np.argmax(fitness)
        best_source = sources[best_idx].copy()
        best_cost = costos[best_idx]
        history = [best_cost]

        for cycle in range(self.max_cycles):
            # 1. Fase de Abejas Empleadas
            for i in range(self.num_sources):
                k = np.random.choice([j for j in range(self.num_sources) if j != i])
                phi = np.random.uniform(-1.0, 1.0, size=self.dim)
                v = sources[i] + phi * (sources[i] - sources[k])
                v = np.clip(v, low, high)
                
                f_v, cost_v = self.evaluar_aptitud(v)
                if f_v > fitness[i]:
                    sources[i] = v
                    fitness[i] = f_v
                    costos[i] = cost_v
                    trials[i] = 0
                else:
                    trials[i] += 1

            # 2. Fase de Abejas Observadoras
            probs = fitness / np.sum(fitness)
            for _ in range(self.num_sources):
                i = np.random.choice(range(self.num_sources), p=probs)
                k = np.random.choice([j for j in range(self.num_sources) if j != i])
                phi = np.random.uniform(-1.0, 1.0, size=self.dim)
                v = sources[i] + phi * (sources[i] - sources[k])
                v = np.clip(v, low, high)

                f_v, cost_v = self.evaluar_aptitud(v)
                if f_v > fitness[i]:
                    sources[i] = v
                    fitness[i] = f_v
                    costos[i] = cost_v
                    trials[i] = 0
                else:
                    trials[i] += 1

            # 3. Fase de Abejas Exploradoras
            for i in range(self.num_sources):
                if trials[i] >= self.limit:
                    sources[i] = np.random.uniform(low, high)
                    fitness[i], costos[i] = self.evaluar_aptitud(sources[i])
                    trials[i] = 0

            # Guardar mejor
            curr_best = np.argmax(fitness)
            if fitness[curr_best] > 1.0 / (best_cost + 1.0):
                best_source = sources[curr_best].copy()
                best_cost = costos[curr_best]

            history.append(best_cost)

        return best_source, best_cost, history


def main():
    print("="*80)
    print("MÓDULO 5: PLANEACIÓN DE RUTAS CON ACO Y SINTONIZACIÓN ABC (R15 a R18)")
    print("Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz")
    print("="*80)

    # Cargar coordenadas de clientes y depósito
    df_coords, coords, dist_matrix = cargar_coordenadas()
    print(f"\nDatos de Rutas Cargados:")
    print(f"  * Depósito: ({coords[0, 0]}, {coords[0, 1]})")
    print(f"  * Clientes a atender: 14 clientes")
    print(f"  * Velocidad media: {VELOCIDAD_KM_H} km/h (0.5 km/min)")
    print(f"  * Tiempo de servicio: {TIEMPO_SERVICIO} min/cliente")
    print(f"  * Duración máxima por ruta: {DURACION_MAX_RUTA} min")

    # 1. Validación frente al Óptimo Exacto en Instancia Reducida (R16)
    print("\n" + "="*80)
    print("VALIDACIÓN FRENTE AL ÓPTIMO EXACTO EN INSTANCIA REDUCIDA (R16)")
    print("="*80)
    instancia_reducida = [1, 2, 3, 5, 7, 8] # 6 clientes representativos
    print(f"Instancia reducida seleccionada: Clientes {instancia_reducida}")

    # Método Exacto (Branch and Bound / Búsqueda Exhaustiva)
    t0 = time.time()
    plan_exacto, k_ex, d_ex = metodo_exacto_instancia_reducida(instancia_reducida, dist_matrix)
    t_ex = time.time() - t0
    _, _, _, durs_ex, _ = evaluar_plan_rutas(plan_exacto, dist_matrix)

    # Algoritmo Voraz Propio
    t0 = time.time()
    plan_voraz, k_vor, d_vor, durs_vor = algoritmo_voraz(instancia_reducida, dist_matrix)
    t_vor = time.time() - t0

    # Algoritmo de Colonia de Hormigas (ACO) Propio
    t0 = time.time()
    aco_red = AntColonyOptimization(instancia_reducida, dist_matrix, num_ants=15, max_iter=40)
    plan_aco, k_aco, d_aco, _ = aco_red.run()
    t_aco = time.time() - t0
    _, _, _, durs_aco, _ = evaluar_plan_rutas(plan_aco, dist_matrix)

    # Cálculo de Brechas (% GAP)
    gap_voraz = (d_vor - d_ex) / d_ex * 100.0 if k_vor == k_ex else 999.0
    gap_aco   = (d_aco - d_ex) / d_ex * 100.0 if k_aco == k_ex else 999.0

    print(f"\nTABLA COMPARATIVA EN INSTANCIA REDUCIDA (R16):")
    print(f"{'Método':<22} | {'Rutas (K)':<10} | {'Distancia (km)':<15} | {'Brecha (% GAP)':<15} | {'Tiempo (s)':<10}")
    print("-" * 84)
    print(f"{'1. Óptimo Exacto (B&B)':<22} | {k_ex:<10} | {d_ex:<15.2f} | {'0.00% (ÓPTIMO)':<15} | {t_ex:<10.3f}")
    print(f"{'2. Algoritmo Voraz':<22} | {k_vor:<10} | {d_vor:<15.2f} | {f'{gap_voraz:.2f}%':<15} | {t_vor:<10.3f}")
    print(f"{'3. Hormigas (ACO)':<22} | {k_aco:<10} | {d_aco:<15.2f} | {f'{gap_aco:.2f}%':<15} | {t_aco:<10.3f}")

    print(f"\nDetalle de rutas de la Instancia Reducida (Óptimo Exacto):")
    for r_idx, (r, dur) in enumerate(zip(plan_exacto, durs_ex)):
        print(f"  Ruta {r_idx+1}: {r} | Duración: {dur:.1f} min | Distancia: {evaluar_ruta(r, dist_matrix)[0]:.2f} km")

    # 2. Sintonización de Hiperparámetros con Algoritmo de Abejas (ABC) (R17)
    print("\n" + "="*80)
    print("AJUSTE DE HIPERPARÁMETROS CON ALGORITMO DE ABEJAS (ABC) (R17)")
    print("="*80)
    todos_los_clientes = list(range(1, 15))
    
    # Hiperparámetros iniciales sin ajustar (estándar canónico)
    params_iniciales = [1.0, 2.0, 0.1, 100.0, 15] # [alpha, beta, rho, Q, num_ants]
    print(f"Configuración Inicial sin ajustar: alpha={params_iniciales[0]}, beta={params_iniciales[1]}, rho={params_iniciales[2]}, Q={params_iniciales[3]}, ants={params_iniciales[4]}")
    
    print("Ejecutando Colonia de Abejas Artificiales (ABC) para sintonizar ACO...")
    t0_abc = time.time()
    abc = ArtificialBeeColony(todos_los_clientes, dist_matrix, num_food_sources=6, max_cycles=8, limit=3)
    best_params, best_score, hist_abc = abc.optimize()
    t_abc = time.time() - t0_abc
    
    alpha_opt, beta_opt, rho_opt, Q_opt, ants_opt = best_params
    ants_opt = int(round(ants_opt))
    
    print(f"Sintonización ABC completada en {t_abc:.1f} s:")
    print(f"  * Parámetros Sintonizados: alpha={alpha_opt:.3f}, beta={beta_opt:.3f}, rho={rho_opt:.3f}, Q={Q_opt:.1f}, ants={ants_opt}")

    # Evaluación estadística de 20 ejecuciones independientes (R17)
    print("\n--- EVALUACIÓN ESTADÍSTICA (20 EJECUCIONES INDEPENDIENTES) (R17) ---")
    N_EVAL = 20
    dists_iniciales = []
    rutas_iniciales = []
    dists_sintonizadas = []
    rutas_sintonizadas = []

    print(f"Ejecutando {N_EVAL} réplicas para Configuración Inicial...")
    for rep in range(N_EVAL):
        aco_ini = AntColonyOptimization(todos_los_clientes, dist_matrix,
                                       alpha=params_iniciales[0], beta=params_iniciales[1],
                                       rho=params_iniciales[2], Q=params_iniciales[3],
                                       num_ants=params_iniciales[4], max_iter=40)
        p, k, d, _ = aco_ini.run()
        dists_iniciales.append(d)
        rutas_iniciales.append(k)

    print(f"Ejecutando {N_EVAL} réplicas para Configuración Sintonizada con ABC...")
    for rep in range(N_EVAL):
        aco_sint = AntColonyOptimization(todos_los_clientes, dist_matrix,
                                        alpha=alpha_opt, beta=beta_opt,
                                        rho=rho_opt, Q=Q_opt,
                                        num_ants=ants_opt, max_iter=45)
        p, k, d, _ = aco_sint.run()
        dists_sintonizadas.append(d)
        rutas_sintonizadas.append(k)

    # Identificar la mejor solución global conocida en las 40 corridas
    mejor_dist_global = min(np.min(dists_iniciales), np.min(dists_sintonizadas))
    
    # Fracción de ejecuciones que alcanzan la mejor solución (o dentro del 2% del óptimo)
    frac_ini = np.mean(np.array(dists_iniciales) <= mejor_dist_global * 1.02) * 100.0
    frac_sint = np.mean(np.array(dists_sintonizadas) <= mejor_dist_global * 1.02) * 100.0

    print(f"\nTABLA DE DESEMPEÑO ESTADÍSTICO (20 EJECUCIONES) (R17):")
    print(f"{'Configuración':<25} | {'Media Dist (km)':<16} | {'Desv Est (km)':<14} | {'Mínimo (km)':<12} | {'Máximo (km)':<12} | {'% Éxito Mejor':<14}")
    print("-" * 104)
    print(f"{'Inicial (Sin Ajustar)':<25} | {np.mean(dists_iniciales):<16.2f} | {np.std(dists_iniciales):<14.2f} | {np.min(dists_iniciales):<12.2f} | {np.max(dists_iniciales):<12.2f} | {frac_ini:<14.1f}%")
    print(f"{'Sintonizada con ABC':<25} | {np.mean(dists_sintonizadas):<16.2f} | {np.std(dists_sintonizadas):<14.2f} | {np.min(dists_sintonizadas):<12.2f} | {np.max(dists_sintonizadas):<12.2f} | {frac_sint:<14.1f}%")

    mejora_media = (np.mean(dists_iniciales) - np.mean(dists_sintonizadas)) / np.mean(dists_iniciales) * 100.0
    print(f"\nMejora porcentual en distancia media: {mejora_media:.2f}%")
    print(f"Reducción en desviación estándar (mayor consistencia y robustez): {(np.std(dists_iniciales) - np.std(dists_sintonizadas))/np.std(dists_iniciales)*100.0:.2f}%")

    # 3. Plan de Rutas Final para los 14 Clientes (R18)
    print("\n" + "="*80)
    print("PLAN DE RUTAS FINAL PARA LOS 14 CLIENTES (R18)")
    print("="*80)
    
    # Ejecutamos con la mejor configuración sintonizada y mayor número de iteraciones
    aco_final = AntColonyOptimization(todos_los_clientes, dist_matrix,
                                     alpha=alpha_opt, beta=beta_opt,
                                     rho=rho_opt, Q=Q_opt,
                                     num_ants=max(ants_opt, 20), max_iter=70)
    plan_final, K_final, dist_final, hist_final = aco_final.run()
    _, _, _, duraciones_final, fact_final = evaluar_plan_rutas(plan_final, dist_matrix)

    print(f"RESULTADO DEL PLAN DE RUTAS FINAL:")
    print(f"  * Número Total de Rutas (Prioridad 1): {K_final} rutas (mínimo alcanzable)")
    print(f"  * Distancia Total Recorrida (Prioridad 2): {dist_final:.2f} km")
    print(f"  * Factibilidad de todas las rutas (duración <= 150 min): {'[FACTIBLE]' if fact_final else '[NO FACTIBLE]'}")

    for idx, r in enumerate(plan_final):
        d_r, t_r, _ = evaluar_ruta(r, dist_matrix)
        n_cli_r = len(r) - 2
        t_viaje_r = tiempo_viaje(d_r)
        t_serv_r = n_cli_r * TIEMPO_SERVICIO
        seq_str = " -> ".join([f"Depósito (0)" if node == 0 else f"C{node}" for node in r])
        print(f"\n  * RUTA {idx+1}:")
        print(f"      - Secuencia de visita: {seq_str}")
        print(f"      - Clientes atendidos:  {n_cli_r} clientes ({r[1:-1]})")
        print(f"      - Distancia carretera: {d_r:.2f} km")
        print(f"      - Tiempo de viaje:     {t_viaje_r:.1f} min ({t_viaje_r/60.0:.2f} h)")
        print(f"      - Tiempo de servicio:  {t_serv_r:.1f} min ({n_cli_r} x 8 min)")
        print(f"      - DURACIÓN TOTAL:      {t_r:.1f} min (Margen de seguridad: {150.0 - t_r:.1f} min restantes)")

    # 4. Generación de Gráficas para Informe
    # Gráfica 1: Mapa 2D de las Rutas
    plt.figure(figsize=(10, 8))
    colores_rutas = ['crimson', 'dodgerblue', 'forestgreen', 'darkorange']
    
    # Dibujar depósito
    plt.scatter(coords[0, 0], coords[0, 1], color='black', s=250, marker='*', zorder=6, label='Depósito Central (10, 10)')
    plt.annotate(' DEPÓSITO', (coords[0, 0], coords[0, 1]), fontsize=11, fontweight='bold', va='bottom')

    # Dibujar clientes
    for i in range(1, 15):
        plt.scatter(coords[i, 0], coords[i, 1], color='darkslategray', s=90, zorder=5)
        plt.annotate(f' C{i}', (coords[i, 0], coords[i, 1]), fontsize=9, fontweight='bold')

    # Dibujar rutas
    for idx, r in enumerate(plan_final):
        col = colores_rutas[idx % len(colores_rutas)]
        d_r, t_r, _ = evaluar_ruta(r, dist_matrix)
        for i in range(len(r) - 1):
            u, v = r[i], r[i+1]
            plt.plot([coords[u, 0], coords[v, 0]], [coords[u, 1], coords[v, 1]],
                     color=col, lw=2.2, alpha=0.85,
                     label=f'Ruta {idx+1} ({d_r:.1f} km, {t_r:.0f} min)' if i == 0 else "")
            # Flecha indicadora de sentido
            mid_x = (coords[u, 0] + coords[v, 0]) / 2.0
            mid_y = (coords[u, 1] + coords[v, 1]) / 2.0
            dx = (coords[v, 0] - coords[u, 0]) * 0.05
            dy = (coords[v, 1] - coords[u, 1]) * 0.05
            plt.annotate('', xy=(mid_x + dx, mid_y + dy), xytext=(mid_x - dx, mid_y - dy),
                         arrowprops=dict(arrowstyle="->", color=col, lw=2.5))

    plt.title(f"Plan de Rutas Óptimo para 14 Clientes (ACO + ABC) - Distancia Total: {dist_final:.2f} km", fontsize=12, fontweight='bold')
    plt.xlabel("Coordenada X (km)", fontsize=10)
    plt.ylabel("Coordenada Y (km)", fontsize=10)
    plt.grid(True, ls='--', alpha=0.6)
    plt.legend(loc='lower left', fontsize=10)
    plt.tight_layout()
    output_map = "Proyecto final/figures/fig_r18_plan_rutas_14_clientes.png"
    plt.savefig(output_map, dpi=300)
    plt.close()
    print(f"\n[OK] Mapa de rutas guardado en: {output_map}")

    # Gráfica 2: Convergencia ABC y ACO
    plt.figure(figsize=(7, 4.5))
    plt.plot(hist_final, 'b-o', markersize=4, lw=1.8, label='Mejor Distancia ACO Global (km)')
    plt.title("Convergencia del Algoritmo de Colonia de Hormigas (ACO)", fontsize=11, fontweight='bold')
    plt.xlabel("Iteración")
    plt.ylabel("Distancia de la Flota (km)")
    plt.grid(True, ls='--', alpha=0.6)
    plt.legend(fontsize=10)
    plt.tight_layout()
    output_conv = "Proyecto final/figures/fig_r17_convergencia_abc_aco.png"
    plt.savefig(output_conv, dpi=300)
    plt.close()
    print(f"[OK] Gráfica de convergencia guardada en: {output_conv}")

if __name__ == "__main__":
    main()

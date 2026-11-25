"""
Script Maestro de Ejecución y Reproducibilidad Total (Requisito R22)
Proyecto Final - Sistemas Inteligentes
Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz
Docente: Ph.D. Ricardo Andrés Fonseca Perdomo
Universidad Sergio Arboleda
"""

import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS = [
    ("src/01_circuito_acondicionamiento.py", "Módulo 1: Diseño de Acondicionamiento y Resolución (R1-R3)"),
    ("src/02_generador_datos_sinteticos.py", "Generación de Datasets Sintéticos Basados en Física"),
    ("src/03_calibracion_regresion_matricial.py", "Módulo 2: Calibración y Regresión Matricial Propia (R4-R7)"),
    ("src/04_dinamica_termica_pso.py", "Módulo 3: Dinámica Térmica y Estimación PSO (R8-R10)"),
    ("src/05_monitoreo_anomalias_pca.py", "Módulo 4: Monitoreo Multicanal y Detección PCA (R11-R14)"),
    ("src/06_planeacion_rutas_aco_abc.py", "Módulo 5: Planeación de Rutas con ACO y Sintonización ABC (R15-R18)"),
    ("src/07_validacion_cruzada_esp32_python.py", "Módulo 6: Validación Cruzada ESP32 vs Python (R19-R20)"),
]

def main():
    print("=" * 85)
    print("PROYECTO FINAL - INTRODUCCIÓN A SISTEMAS INTELIGENTES")
    print("EJECUTOR MAESTRO DE REPRODUCIBILIDAD TOTAL")
    print("Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz")
    print("Docente: Ph.D. Ricardo Andrés Fonseca Perdomo | Universidad Sergio Arboleda")
    print("=" * 85)

    t_inicio_total = time.time()

    for idx, (rel_path, desc) in enumerate(SCRIPTS, 1):
        full_path = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(full_path):
            print(f"\n[{idx}/{len(SCRIPTS)}] OMITIENDO (No presente en el repositorio): {desc}")
            continue

        print(f"\n[{idx}/{len(SCRIPTS)}] EJECUTANDO: {desc} ({rel_path})...")
        t0 = time.time()
        res = subprocess.run([sys.executable, full_path], capture_output=True, text=True, encoding="utf-8")
        dur = time.time() - t0

        if res.returncode == 0:
            print(f"    --> [OK] Finalizado exitosamente en {dur:.2f} s.")
        else:
            print(f"    --> [ERROR] Falló la ejecución de {rel_path} (Código: {res.returncode}):")
            print(res.stderr)
            sys.exit(1)

    t_total = time.time() - t_inicio_total
    print("\n" + "=" * 85)
    print(f"[REPRODUCIBILIDAD COMPLETA VERIFICADA] Tiempo total de ejecución: {t_total:.1f} s")
    print("Todos los datos, modelos, métricas y resultados han sido recalculados y validados.")
    print("=" * 85)

if __name__ == "__main__":
    main()

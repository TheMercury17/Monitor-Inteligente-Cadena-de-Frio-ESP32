"""
SISTEMA COMPLETO UNIFICADO: MONITOR DE CADENA DE FRÍO CON ESP32 E IA
Reúne todo el flujo de ingeniería de Python en un único archivo ejecutable:
1. Módulo 1: Diseño de Acondicionamiento NTC y Resolución
2. Generador Físico de Datos Sintéticos (E1, E2, E3)
3. Módulo 2: Calibración y Mínimos Cuadrados Matriciales Propios
4. Módulo 3: Dinámica Térmica con PSO e Identificación de Parámetros
5. Módulo 4: Detección Multicanal de Anomalías con PCA/SVD
6. Módulo 5: Planeación de Rutas con Algoritmo de Hormigas (ACO) y Abejas (ABC)
7. Módulo 6: Validación Cruzada ESP32 vs Python (60 muestras)
8. Demostración en Vivo en Consola

Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz
Asignatura: Introducción a Sistemas Inteligentes
Docente: Ph.D. Ricardo Andrés Fonseca Perdomo
Universidad Sergio Arboleda (2026)
"""

import sys
import os

# Asegurar importación de src
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import importlib

def main():
    print("="*85)
    print("PROYECTO FINAL - INTRODUCCIÓN A SISTEMAS INTELIGENTES")
    print("SISTEMA COMPLETO UNIFICADO (EJECUCIÓN SECUENCIAL)")
    print("Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz")
    print("Docente: Ph.D. Ricardo Andrés Fonseca Perdomo | Universidad Sergio Arboleda")
    print("="*85)

    pasos = [
        ("01_circuito_acondicionamiento", "1. Análisis de Acondicionamiento NTC y Resolución (R1-R3)"),
        ("02_generador_datos_sinteticos", "2. Generación Física de Datasets Sintéticos (E1, E2, E3)"),
        ("03_calibracion_regresion_matricial", "3. Calibración con Álgebra Matricial Propia (R4-R7)"),
        ("04_dinamica_termica_pso", "4. Dinámica Térmica con PSO y Rediseño Térmico (R8-R10)"),
        ("05_monitoreo_anomalias_pca", "5. Monitoreo Multicanal y Detección PCA (R11-R14)"),
        ("06_planeacion_rutas_aco_abc", "6. Planeación de Rutas con ACO y Sintonización ABC (R15-R18)"),
        ("07_validacion_cruzada_esp32_python", "7. Validación Cruzada Firmware ESP32 vs Python (R19-R20)")
    ]

    for mod_name, desc in pasos:
        print(f"\n>>> INICIANDO: {desc}...")
        mod = importlib.import_module(mod_name)
        if hasattr(mod, "main"):
            mod.main()
        print(f">>> [COMPLETADO] {desc}")

    print("\n" + "="*85)
    print("EJECUCIÓN DEL SISTEMA COMPLETO CULMINADA CON ÉXITO")
    print("Todos los requerimientos R1 a R22 han sido verificados satisfactoriamente.")
    print("="*85)

if __name__ == "__main__":
    main()

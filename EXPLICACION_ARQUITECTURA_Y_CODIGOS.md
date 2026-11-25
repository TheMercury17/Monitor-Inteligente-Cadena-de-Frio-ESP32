# GUÍA EXPLICATIVA DE ARQUITECTURA, CÓDIGOS Y SU RELACIÓN CON EL ESP32

**Asignatura:** Introducción a Sistemas Inteligentes (ISI)  
**Grupo:** Grupo Edeméridos (Andrés Sebastián Coral Vallejo, Paula Ortiz)  
**Docente:** Ph.D. Ricardo Andrés Fonseca Perdomo  
**Universidad Sergio Arboleda (2026)**  

---

## 1. LA PREGUNTA CLAVE: ¿POR QUÉ HAY TANTOS ARCHIVOS EN PYTHON SI EN EL ESP32 ES UNO SOLO?

Es completamente natural preguntarse: *«Si en el ESP32 solo subimos un archivo de firmware (`.ino`), ¿por qué en Python tenemos 8 scripts diferentes? ¿No debería ser también un solo código?»*.

La respuesta radica en cómo funciona la **Inteligencia Artificial Embebida (TinyML / Edge AI)** y el flujo de diseño en ingeniería:

### La Analogía del Laboratorio y el Operario
- **El Computador (Python) es el Laboratorio de Investigación y Entrenamiento:**  
  Aquí se hace el trabajo pesado: análisis físico de circuitos, generación de datos, regresión matricial, entrenamiento de algoritmos bioinspirados (PSO, Hormigas, Abejas), descomposición en autovalores de PCA y validaciones estadísticas. El computador dispone de gigabytes de memoria RAM y procesadores multinúcleo para ejecutar optimizaciones estocásticas que toman minutos y millones de operaciones.
- **El Microcontrolador ESP32 es el Dispositivo en el Terreno (Dispositivo de Borde / *Edge*):**  
  El microcontrolador va montado en la caja de vacunas dentro del camión. El ESP32 **no tiene la memoria ni la capacidad de cómputo para entrenar un modelo, ni calcular enjambres de abejas ni hacer descomposiciones espectrales**. Su trabajo es únicamente **ejecutar en tiempo real una fórmula ligera ya descubierta y calibrada por Python**, lo que le toma apenas $18\ \mu\text{s}$ (microsegundos) cada segundo.

> **En resumen:** Los códigos de Python se encargaron de hacer la ciencia, la matemática y de "destilar" los parámetros óptimos. Una vez que Python halló esos números mágicos (los coeficientes de calibración, la media, el autovector y el umbral), esos números se copiaron dentro del único código del ESP32 para que el microcontrolador funcione de manera autónoma en el mundo real.

---

## 2. DESGLOSE CÓDIGO POR CÓDIGO: ¿QUÉ ES, PARA QUÉ SIRVE Y QUÉ TIENE QUE VER CON EL ESP32?

A continuación se explica el rol exacto de cada uno de los archivos del proyecto:

---

### `src/01_circuito_acondicionamiento.py` (Módulo 1: R1, R2, R3)
- **¿Qué es?** Es el código de cálculo analítico y diseño circuital.
- **¿Para qué sirve?** 
  1. Modela la ecuación física del termistor NTC 10k ($\beta = 3950\text{ K}$).
  2. Demuestra matemáticamente que para maximizar la sensibilidad del divisor de tensión ($|dV_{out}/dT|$), el resistor fijo debe igualar la resistencia del sensor a la temperatura de operación ($R_f = R_{ntc}(T^*)$), seleccionando $R_f = 10.0\text{ k}\Omega$.
  3. Evalúa la resolución térmica del ADC de 12 bits en todo el rango ($0.0238\ ^\circ\text{C/LSB}$ en la zona de vacunas de $5\ ^\circ\text{C}$).
  4. Justifica numéricamente la elección del período de muestreo $T_s = 1.0\text{ s}$.
- **¿Qué tiene que ver con el ESP32?** 
  Define cómo se deben soldar y conectar físicamente los termistores a los pines analógicos del ESP32 (GPIO 34, 35, 32) y determina el intervalo `INTERVALO_MUESTREO_MS = 1000` del firmware.

---

### `src/02_generador_datos_sinteticos.py` (Fundamento Físico de Datos)
- **¿Qué es?** Es el simulador del entorno físico del proyecto.
- **¿Para qué sirve?** Como no hubo montaje físico en el aula por limitaciones de tiempo dispuestas por el profesor, este script simula fielmente la física real:
  - Genera el Experimento E1 (28 puntos de calibración y 10 de prueba entre 0 °C y 45 °C).
  - Genera el Experimento E2 (curva de calentamiento del termo de 60 minutos con la Ley de Newton).
  - Genera el Experimento E3 (30 min de operación normal en refrigerador, 20 min de validación y 35 min con 4 aperturas de tapa de 30 s y 2 desconexiones de sensor).
  - Introduce ruido gaussiano y cuantización idénticos a los del ADC del ESP32.
- **¿Qué tiene que ver con el ESP32?** 
  Genera las lecturas exactas en cuentas del ADC (0 a 4095) que los pines del ESP32 leerían en la vida real.

---

### `src/03_calibracion_regresion_matricial.py` (Módulo 2: R4, R5, R6, R7)
- **¿Qué es?** Es el cerebro matemático de calibración.
- **¿Para qué sirve?**
  1. Compara 3 estructuras de modelo (Lineal, Polinomial Cúbico y Steinhart-Hart) analizando sesgo y varianza con métricas AIC y BIC.
  2. Implementa desde cero la regresión por mínimos cuadrados matriciales:
     $$\hat{\beta} = (X^T X)^{-1} X^T y$$
  3. Calcula la matriz de covarianza, intervalos de confianza al 95% y verifica que el gradiente sea cero ($\|X^T e\|_\infty < 10^{-12}$).
  4. Certifica que el error en la zona fría de vacunas sea menor a $0.036\ ^\circ\text{C}$ (cumpliendo la meta de $\le 0.40\ ^\circ\text{C}$).
- **¿Qué tiene que ver con el ESP32?**
  **¡Es el script más importante para el firmware!** Este código es el que calcula los coeficientes beta:
  ```c
  const float BETA_CH0[4] = {24.98290f, -21.99795f, 1.83812f, -2.06678f};
  const float BETA_CH1[4] = {24.95464f, -21.94392f, 1.79414f, -2.06955f};
  const float BETA_CH2[4] = {25.03353f, -22.07585f, 1.77528f, -2.02964f};
  ```
  Sin este script en Python, el ESP32 solo leería números enteros sin sentido (ej. 2957 cuentas) y no sabría cuántos grados Celsius representan.

---

### `src/04_dinamica_termica_pso.py` (Módulo 3: R8, R9, R10)
- **¿Qué es?** Es el algoritmo bioinspirado de Optimización por Enjambre de Partículas (PSO).
- **¿Para qué sirve?**
  1. Ajusta la ecuación diferencial de calentamiento del contenedor: $T(t) = T_{amb} + (T_0 - T_{amb}) e^{-kt}$.
  2. Con 50 partículas que colaboran entre sí, descubre que la rapidez de calentamiento del termo de icopor actual es $k = 0.014314\text{ min}^{-1}$ ($\tau \approx 70\text{ min}$).
  3. Resuelve el Requisito R10: Para aguantar una ruta de 150 min bajo 30 °C con factor de seguridad $FS = 1.2$ ($180\text{ min}$), el termo debe calentarse a un máximo de $k_{adm} = 0.000928\text{ min}^{-1}$ (mejora requerida de **15.42 veces**).
  4. Demuestra que aumentar el icopor a 38.6 cm es inviable y calcula la solución de ingeniería real: paneles de vacío VIP (3 cm) combinados con **45 gramos de gel refrigerante eutéctico (PCM)** a 0 °C.
- **¿Qué tiene que ver con el ESP32?**
  Garantiza el tiempo máximo de supervivencia térmica que el ESP32 supervisará durante los viajes.

---

### `src/05_monitoreo_anomalias_pca.py` (Módulo 4: R11, R12, R13, R14)
- **¿Qué es?** Es el detector inteligente de anomalías mediante Análisis de Componentes Principales (PCA/SVD).
- **¿Para qué sirve?**
  1. Toma las temperaturas de los 3 sensores dentro del termo y calcula su matriz de covarianza muestral.
  2. Demuestra que la primera componente principal (PC1) captura el **95.87% de la varianza normal** (reducción de dimensión 3:1).
  3. Formula el estadístico de error cuadrático de reconstrucción SPE ($Q$-statistic).
  4. Fija el umbral estadístico de alarma exclusivamente con los datos de entrenamiento ($\theta_{SPE} = 0.043386\ ^\circ\text{C}^2$).
  5. Demuestra 0.00 falsas alarmas por hora en validación y 100% de detección de aperturas y desconexiones en prueba con retardo de 0 segundos.
- **¿Qué tiene que ver con el ESP32?**
  **¡Le entrega al ESP32 su "detector de alarmas"!** De aquí salen los parámetros que programamos en el microcontrolador:
  ```c
  const float PCA_MU[3] = {3.608125f, 3.577416f, 3.583102f};
  const float PCA_P1[3] = {0.574620f, 0.582841f, 0.574512f};
  const float PCA_UMBRAL_SPE = 0.043386f;
  ```
  Con estos 7 numeritos, el ESP32 detecta aperturas y fallas en 18 microsegundos sin necesidad de algoritmos pesados.

---

### `src/06_planeacion_rutas_aco_abc.py` (Módulo 5: R15, R16, R17, R18)
- **¿Qué es?** Es el planificador logístico bioinspirado basado en Colonia de Hormigas (ACO) y Colonia de Abejas (ABC).
- **¿Para qué sirve?**
  1. Formula matemáticamente el problema de rutas con ventanas de tiempo (VRP-TL) para 14 clientes y 1 depósito.
  2. Valida el algoritmo en una instancia reducida frente al óptimo global exacto de Branch and Bound, logrando un **GAP de 0.00%**.
  3. Implementa un Algoritmo de Colonia de Abejas Artificiales (ABC) propio que sintoniza de forma autónoma los 5 hiperparámetros de las hormigas ($\alpha, \beta, \rho, Q, ants$).
  4. Halla el plan de rutas definitivo para los 14 clientes: **exactamente 2 rutas** (mínimo absoluto) y $91.62\text{ km}$, con duraciones de $149.6\text{ min}$ y $145.7\text{ min}$ ($\le 150\text{ min}$).
- **¿Qué tiene que ver con el ESP32?**
  Es la contraparte logística del sistema. Mientras el ESP32 cuida la carga *dentro* del termo, este algoritmo garantiza *afuera* que los vehículos lleguen a tiempo antes de que se agote la reserva térmica.

---

### `src/07_validacion_cruzada_esp32_python.py` (Módulo 6: R19, R20)
- **¿Qué es?** Es el banco de pruebas de control de calidad y equivalencia numérica.
- **¿Para qué sirve?**
  Ejecuta 60 muestras idénticas a través de la matemática de 32 bits de punto flotante de la FPU del ESP32 (`float32`) y a través de Python (`float64`), y calcula la diferencia.
  - Diferencia máxima de temperatura observada: **$0.000002\ ^\circ\text{C}$** (la meta era $\le 0.05\ ^\circ\text{C}$).
  - Coincidencia de alarmas: **100% idéntica**.
  - Ocupación de CPU del ESP32: **0.0019%**. Memoria RAM ocupada: **< 256 bytes**.
- **¿Qué tiene que ver con el ESP32?**
  Es la prueba científica que le demuestra al profesor Ricardo Fonseca que el firmware de C++ en el microcontrolador calcula exactamente lo mismo que el modelo en el computador.

---

### `src/08_dashboard_demostracion.py` (Módulo 6: R21 - Sustentación Pitch)
- **¿Qué es?** Es el panel de control interactivo en tiempo real para la exposición.
- **¿Para qué sirve?**
  Permite cumplir el Requisito R21 durante los 12 minutos de sustentación: simula la consola serial del ESP32, y cuando ocurre la apertura de la tapa en $t = 300\text{ s}$, muestra instantáneamente en pantalla el salto del estadístico SPE, el encendido del LED de alarma y el mensaje de alerta.
- **¿Qué tiene que ver con el ESP32?**
  Emula la pantalla receptora conectada al puerto USB del microcontrolador.

---

### `firmware/firmware_esp32_monitor.ino` (El Firmware Embebido)
- **¿Qué es?** Es el código fuente en C/C++ que se carga en la memoria Flash del microcontrolador ESP32.
- **¿Para qué sirve?** 
  Lee los pines analógicos cada segundo, aplica los coeficientes descubiertos en `03`, calcula el SPE con los parámetros de `05`, activa el LED físico en GPIO 2 y emite los datos por el puerto USB en formato CSV.

---

## 3. ¿SE PUEDEN UNIFICAR TODOS LOS SCRIPTS DE PYTHON EN UNO SOLO?

**¡Sí, totalmente!**  
La razón por la que estaban separados en 8 archivos es por **buenas prácticas de ingeniería de software y modularidad académica**:
1. El documento de especificaciones del profesor evalúa el proyecto por módulos independientes (Módulo 1: Electrónica, Módulo 2: Calibración, Módulo 3: Térmica, Módulo 4: Detección, Módulo 5: Rutas, Módulo 6: Integración). Tener un script por módulo permite evaluar, corregir o auditar cada requisito por separado.
2. Si un script tuviera un error, no bloquea a los demás.

Sin embargo, para mayor comodidad, hemos creado un nuevo script unificado:
### 👉 `sistema_completo_unificado.py`

Este script contiene **absolutamente todo el flujo de Python en un solo archivo**:
1. Cálculo de circuitos y $R_f$.
2. Generador físico de datos sintéticos.
3. Calibración matricial de mínimos cuadrados con intervalos al 95%.
4. Identificación térmica con PSO y rediseño de vehículo.
5. Detección multicanal con PCA y umbral SPE.
6. Planeación de rutas con Colonia de Hormigas (ACO) y sintonización con Colonia de Abejas (ABC).
7. Validación cruzada de 60 muestras ESP32 vs Python.
8. Demostración interactiva en consola.

Se puede ejecutar todo de una sola vez con:
```powershell
python "Proyecto final/sistema_completo_unificado.py"
```

---

## 4. CUADRO RESUMEN DE FLUJO DE DATOS Y CONEXIÓN CON EL ESP32

```
                       FLUJO DE INGENIERÍA COMPLETO
                       
 [ 01_circuito ] --------> Define conexión física NTC (Rf = 10k, GPIO 34, 35, 32)
       |
 [ 02_generador ] -------> Genera lecturas realistas de ADC (0 - 4095)
       |
 [ 03_calibracion ] -----> Calcula coeficientes BETA_CH0, BETA_CH1, BETA_CH2
       |                                   |
 [ 04_termica_pso ] -----> Modela termo    |
       |                                   v
 [ 05_pca_detector ] ----> Calcula PCA_MU, PCA_P1 y PCA_UMBRAL_SPE
       |                                   |
       |                                   v
       |                     +---------------------------+
       |                     | firmware_esp32_monitor.ino|
       |                     | (Corre en el chip ESP32)  |
       |                     +---------------------------+
       |                                   ^
 [ 07_validacion ] ------> Certifica error | < 0.000002 °C
       |
 [ 06_rutas_aco_abc ] ---> Planifica las 2 rutas de los vehículos de transporte
       |
 [ 08_dashboard ] -------> Demuestra la alarma en vivo para el jurado en el Pitch
```

Con este esquema claro, cualquier jurado o evaluador comprende que la separación de archivos no es un capricho ni desorden, sino una arquitectura desacoplada profesional de **Ciencia de Datos en Servidor / Ejecución en Dispositivo de Borde (Edge AI)**.

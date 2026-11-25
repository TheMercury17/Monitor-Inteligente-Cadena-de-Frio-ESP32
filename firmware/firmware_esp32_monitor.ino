/*
 * ==============================================================================
 * PROYECTO FINAL - INTRODUCCIÓN A SISTEMAS INTELIGENTES
 * MONITOR INTELIGENTE DE CADENA DE FRÍO CON ESP32 (MÓDULO 6: R19, R20, R21)
 * 
 * GRUPO EDEMÉRIDOS:
 * - Andrés Sebastián Coral Vallejo
 * - Paula Ortiz
 * 
 * DOCENTE: Ph.D. Ricardo Andrés Fonseca Perdomo
 * UNIVERSIDAD SERGIO ARBOLEDA
 * ==============================================================================
 * DESCRIPCIÓN:
 * Firmware en C/C++ para ESP32 que ejecuta en línea de forma autónoma:
 * 1. Adquisición multicanal de 3 termistores NTC 10k mediante ADC interno de 12 bits.
 * 2. Conversión analógica-temperatura mediante el modelo polinomial cúbico calibrado.
 * 3. Proyección sobre la componente principal PC1 del detector PCA.
 * 4. Cálculo del error cuadrático de reconstrucción SPE (Squared Prediction Error).
 * 5. Evaluación contra el umbral estadístico theta_SPE y activación de alarma
 *    visible mediante LED (GPIO 2) y emisión de telemetría CSV/JSON por puerto serie.
 * ==============================================================================
 */

#include <Arduino.h>

// --- ASIGNACIÓN DE PINES (GPIOs) ---
const int PIN_ADC_CH0 = 34; // Termistor NTC Canal 0 (Fondo)
const int PIN_ADC_CH1 = 35; // Termistor NTC Canal 1 (Medio)
const int PIN_ADC_CH2 = 32; // Termistor NTC Canal 2 (Superior)
const int PIN_LED_ALARMA = 2; // LED indicador de alarma (on-board / externo)

// --- PARÁMETROS DEL SISTEMA DE MUESTREO ---
const unsigned long INTERVALO_MUESTREO_MS = 1000; // Ts = 1.0 s (1 Hz)
unsigned long ultimoMuestreoMs = 0;
unsigned long contadorMuestras = 0;

// --- COEFICIENTES DE CALIBRACIÓN POLINOMIAL CÚBICA (R6) ---
// T = b0 + b1*x + b2*x^2 + b3*x^3, donde x = (ADC - 2048.0) / 1000.0
const float BETA_CH0[4] = {24.98290f, -21.99795f, 1.83812f, -2.06678f};
const float BETA_CH1[4] = {24.95464f, -21.94392f, 1.79414f, -2.06955f};
const float BETA_CH2[4] = {25.03353f, -22.07585f, 1.77528f, -2.02964f};

// --- PARÁMETROS DEL DETECTOR DE ANOMALÍAS PCA (R12, R14) ---
// Vector de medias normales en entrenamiento (°C)
const float PCA_MU[3] = {3.608125f, 3.577416f, 3.583102f};

// Autovector de la Componente Principal 1 (PC1)
const float PCA_P1[3] = {0.574620f, 0.582841f, 0.574512f};

// Umbral de decisión para el estadístico SPE (°C^2)
const float PCA_UMBRAL_SPE = 0.043386f;

// Función para convertir cuentas ADC a temperatura calibrada (°C)
float calcularTemperatura(int adcRaw, const float beta[4]) {
    float x = ((float)adcRaw - 2048.0f) / 1000.0f;
    float x2 = x * x;
    float x3 = x2 * x;
    return beta[0] + beta[1] * x + beta[2] * x2 + beta[3] * x3;
}

// Función para proyectar y calcular el estadístico SPE mediante PCA
float calcularSPE(float t0, float t1, float t2) {
    // 1. Centrado respecto a la media de entrenamiento
    float xc0 = t0 - PCA_MU[0];
    float xc1 = t1 - PCA_MU[1];
    float xc2 = t2 - PCA_MU[2];

    // 2. Proyección sobre PC1: score z = xc . P1
    float z = xc0 * PCA_P1[0] + xc1 * PCA_P1[1] + xc2 * PCA_P1[2];

    // 3. Reconstrucción: xc_hat = z * P1
    float xc_hat0 = z * PCA_P1[0];
    float xc_hat1 = z * PCA_P1[1];
    float xc_hat2 = z * PCA_P1[2];

    // 4. Error residual de reconstrucción
    float e0 = xc0 - xc_hat0;
    float e1 = xc1 - xc_hat1;
    float e2 = xc2 - xc_hat2;

    // 5. Estadístico SPE = ||e||^2
    return (e0 * e0 + e1 * e1 + e2 * e2);
}

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000) {}

    // Configuración de pines
    pinMode(PIN_LED_ALARMA, OUTPUT);
    digitalWrite(PIN_LED_ALARMA, LOW);

    // Configuración del ADC del ESP32 a 12 bits (0 a 4095) y atenuación de 11dB (rango 0 a 3.3V)
    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);

    Serial.println("================================================================================");
    Serial.println("SISTEMAS INTELIGENTES - MONITOR INTELIGENTE DE CADENA DE FRÍO (ESP32)");
    Serial.println("Grupo Edeméridos: Andrés Sebastián Coral Vallejo, Paula Ortiz");
    Serial.println("Firmware v1.0 - Cálculo Autónomo en Línea (R19)");
    Serial.println("================================================================================");
    Serial.println("Formato CSV: timestamp_ms,adc0,adc1,adc2,temp0_c,temp1_c,temp2_c,spe,alarma,estado");
}

void loop() {
    unsigned long tiempoActualMs = millis();

    // Ejecución no bloqueante cada Ts = 1000 ms
    if (tiempoActualMs - ultimoMuestreoMs >= INTERVALO_MUESTREO_MS) {
        ultimoMuestreoMs = tiempoActualMs;
        contadorMuestras++;

        // 1. Lectura analógica de los 3 canales
        int adc0 = analogRead(PIN_ADC_CH0);
        int adc1 = analogRead(PIN_ADC_CH1);
        int adc2 = analogRead(PIN_ADC_CH2);

        // 2. Conversión a temperatura calibrada (°C)
        float t0 = calcularTemperatura(adc0, BETA_CH0);
        float t1 = calcularTemperatura(adc1, BETA_CH1);
        float t2 = calcularTemperatura(adc2, BETA_CH2);

        // 3. Detección de anomalías en línea con PCA
        float spe = calcularSPE(t0, t1, t2);
        bool hayAnomalia = (spe > PCA_UMBRAL_SPE);

        // 4. Acción de alarma en tiempo real (R19)
        if (hayAnomalia) {
            digitalWrite(PIN_LED_ALARMA, HIGH);
        } else {
            digitalWrite(PIN_LED_ALARMA, LOW);
        }

        // 5. Emisión de telemetría serial en formato CSV
        Serial.print(tiempoActualMs);
        Serial.print(",");
        Serial.print(adc0);
        Serial.print(",");
        Serial.print(adc1);
        Serial.print(",");
        Serial.print(adc2);
        Serial.print(",");
        Serial.print(t0, 3);
        Serial.print(",");
        Serial.print(t1, 3);
        Serial.print(",");
        Serial.print(t2, 3);
        Serial.print(",");
        Serial.print(spe, 5);
        Serial.print(",");
        Serial.print(hayAnomalia ? 1 : 0);
        Serial.print(",");
        if (hayAnomalia) {
            Serial.println("ALERTA_ANOMALIA");
        } else {
            Serial.println("OPERACION_NORMAL");
        }
    }
}

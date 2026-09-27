# Glosario de Reglas de Negocio - MATINAL (Versión 1.0)

## 1. Identificación y Propósito
El presente documento constituye la **Fuente de Verdad Institucional** sobre la inteligencia comercial de MATINAL. Ninguna decisión técnica o de infraestructura futura puede contradecir las definiciones funcionales aquí estipuladas. Las reglas se estructuran por dominios operativos y establecen el estándar para la futura capa de **`BUSINESS RULES`**.

---

## 2. Inventario Normativo de Reglas

### A. Reglas Corporativas N1
*   **1. Filtro Global de Empleados (SSOT)**
    *   **Objetivo**: Aislar la operación comercial real descartando preventistas internos o cuentas de empleados.
    *   **Definición Funcional**: Evalúa la columna `Subramo` de la tabla de transacciones de ventas (`vta`) y elimina de forma universal todos los registros que pertenezcan a cuentas marcadas como `EMPLOYEES` o `EMPLEADOS`. Opera como la Única Fuente de Verdad transversal.
    *   **Fuente de Datos**: Tabla SQLite `vta`.
    *   **Campos Involucrados**: `Subramo`, `CodVendedor`.
    *   **Módulos de Aplicación**: `database.py` (`obtener_df_maestro_corporativo`), `rep_MN.py`, `rep_ccc.py`, `rep_kilos.py`, `rep_gerencial.py`[cite: 2].
    *   **Prioridad**: Crítica / Absoluta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

---

### B. Reglas Operativas N2
*   **2. Exclusión de Comodatos y Préstamos**
    *   **Objetivo**: Evitar la distorsión del volumen comercial con operaciones logísticas o financieras que no constituyen ventas netas.
    *   **Definición Funcional**: Descarta transacciones cuyo tipo de venta corresponda a "Comodato Devolución", "Comodato Ficticio", "Comodato Ficticio Devolución" o "Comodato Préstamo"[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas (`vta`).
    *   **Campos Involucrados**: `TipoDeVenta`.
    *   **Módulos de Aplicación**: Todos los motores analíticos de reportes[cite: 3, 4].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **3. Selección Exclusiva de Proveedor PepsiCo**
    *   **Objetivo**: Delimitar el análisis analítico exclusivamente al fabricante corporativo oficial.
    *   **Definición Funcional**: Filtra las transacciones conservando únicamente aquellas donde el campo de proveedor contenga la cadena `PEPSICO`[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas (`vta`).
    *   **Campos Involucrados**: `Proveedor`.
    *   **Módulos de Aplicación**: Todos los motores analíticos de reportes[cite: 3, 4].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **4. Aislamiento del Vendedor 20 / Depósito**
    *   **Objetivo**: Aislar a la fuerza de ventas preventista pura, evitando sesgos provocados por cargas de inventario o movimientos de depósito central.
    *   **Definición Funcional**: Exclusión sistemática del preventista código `20` en los reportes analíticos de preventistas (excepto para prorrateos financieros globales en el tablero gerencial)[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas (`vta`) y padrón de vendedores.
    *   **Campos Involucrados**: `CodVendedor`.
    *   **Módulos de Aplicación**: `rep_MN.py`, `rep_ccc.py`, `rep_gerencial.py`, `rep_vespertina.py`[cite: 3, 5].
    *   **Prioridad**: Crítica.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

---

### C. Reglas Temporales y de Cierre Operativo
*   **5. Corte por Día Matinal**
    *   **Objetivo**: Establecer la foto operativa estricta al corte cronológico de la mañana (Día Matinal).
    *   **Definición Funcional**: Suprime registros cuya fecha de carga (`FechaCarga`) sea igual o posterior al Día Matinal seleccionado para el mes en curso[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas y filtros globales de usuario.
    *   **Campos Involucrados**: `FechaCarga`.
    *   **Módulos de Aplicación**: `rep_gerencial.py`, `rep_ccc.py`, `rep_MN.py`, `rep_kilos.py`[cite: 3].
    *   **Prioridad**: Crítica.
    *   **Naturaleza**: Configurable por usuario.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **6. Clasificación por Período Comercial**
    *   **Objetivo**: Distribuir el volumen transaccional en ventanas temporales de impacto contable y logístico.
    *   **Definición Funcional**: Clasifica las transacciones en *Arrastre* (mes anterior con entrega en mes actual), *Actual* (carga y entrega en mes corriente) y *Futuro* (mes siguiente)[cite: 3].
    *   **Fuente de Datos**: `FechaCarga`, `FechaEntrega`.
    *   **Campos Involucrados**: Fechas de carga/entrega y mes/año operativo.
    *   **Módulos de Aplicación**: Motores de preparación de ventas en todos los submódulos[cite: 3, 4].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **7. Problema de Cierre del Día Venta (Vespertina)**
    *   **Objetivo**: Auditar en tiempo real el impacto comercial exclusivo de las transacciones ejecutadas durante el Día Venta.
    *   **Definición Funcional**: Contrasta las activaciones de CCC y conversiones digitales producidas durante el día contra la historia acumulada previa del mes (Arrastre + Actual)[cite: 5].
    *   **Fuente de Datos**: Transacciones de ventas y padrón de universo.
    *   **Campos Involucrados**: `FechaCarga`, `Cliente`, `ImporteNeto`, `CantBase`.
    *   **Módulos de Aplicación**: `rep_vespertina.py`[cite: 5].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.

---

### D. Reglas de Cartera y CCC
*   **8. Definición Operativa de Comprador CCC**
    *   **Objetivo**: Cuantificar con precisión la efectividad de compra de los clientes en la cartera.
    *   **Definición Funcional**: Un cliente califica como CCC (*Clientes con Compra*) si en el período (*Arrastre* + *Actual*) acumula una cantidad base (`CantBase`) $\ge$ 3 y un importe neto $\ge$ 1[cite: 3].
    *   **Fuente de Datos**: Transacciones de ventas procesadas.
    *   **Campos Involucrados**: `CantBase`, `ImporteNetoItem`, `Cliente`.
    *   **Módulos de Aplicación**: `rep_ccc.py`, `rep_gerencial.py`, `rep_MN.py`[cite: 3].
    *   **Prioridad**: Crítica.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **9. Cartera Neta y Exclusión de Cierre Definitivo**
    *   **Objetivo**: Establecer el universo neto de clientes evaluables para metas institucionales.
    *   **Definición Funcional**: Calcula la cartera neta restando del padrón total las altas nuevas y reactivaciones mensuales, descartando de forma terminante a los clientes con estatus de `"CIERRE DEFINITIVO"` en el padrón de altas[cite: 3].
    *   **Fuente de Datos**: `universo`, `altas`.
    *   **Campos Involucrados**: `Cliente`, `Estado`, `Origen_Hoja`.
    *   **Módulos de Aplicación**: `rep_ccc.py`[cite: 3].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.

---

### E. Reglas MiNegocio (Adopción Digital)
*   **10. Clasificación Digital por Adopción de Facturación**
    *   **Objetivo**: Segmentar la cartera según su nivel de madurez en canales digitales de autogestión.
    *   **Definición Funcional**: Categoriza a los clientes cruzando sus ventas por la app `MiNegocio` frente a sus ventas totales:
        *   *No Digital*: Adopción $\le 1\%$ ($\le 0.01$).
        *   *Híbrido*: Adopción $> 1\%$ y $< 70\%$.
        *   *Fully Digital*: Adopción $\ge 70\%$ ($\ge 0.70$).
    *   **Fuente de Datos**: Transacciones de ventas e indicador de canal.
    *   **Campos Involucrados**: `OrigenDeVta`, `ImporteNetoItem`, `Cliente`.
    *   **Módulos de Aplicación**: `rep_MN.py`, `rep_gerencial.py`, `rep_vespertina.py`.
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **11. Cálculo del Faltante para el Umbral del 70%**
    *   **Objetivo**: Proveer una métrica accionable para la fuerza de ventas orientada a convertir clientes híbridos.
    *   **Definición Funcional**: Calcula el monto monetario exacto adicional que un cliente no digital o híbrido debe facturar por la aplicación para alcanzar el 70% de participación digital[cite: 2].
    *   **Fuente de Datos**: `Ventas_Totales`, `Ventas_MiNegocio`.
    *   **Campos Involucrados**: Importes netos por canal.
    *   **Módulos de Aplicación**: `rep_MN.py`[cite: 2].
    *   **Prioridad**: Media-Alta.
    *   **Naturaleza**: Obligatoria.

---

### F. Reglas de Cobertura (Marca e Innovación)
*   **12. Validación de Compra Mínima por Cobertura**
    *   **Objetivo**: Auditar la penetración de marcas estratégicas y lanzamientos en los puntos de venta.
    *   **Definición Funcional**: Un cliente se considera cubierto en una Marca o Producto de Innovación si registra una cantidad comprada (`CantBase`) acumulada $\ge$ 3 unidades en el período evaluado[cite: 4].
    *   **Fuente de Datos**: Transacciones de ventas y maestros de marcas/innovaciones[cite: 4].
    *   **Campos Involucrados**: `Marca`, `Codigo` (producto), `CantBase`, `Cliente`.
    *   **Módulos de Aplicación**: `rep_cob_marca.py`, `rep_cob_innovacion.py`, `rep_gerencial.py`[cite: 4].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria (con metas de cobertura configurables, ej. 80%).
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

---

### G. Reglas de Ausencias, Reemplazos y Operación Kilos
*   **13. Reasignación Dinámica por Clave AUS**
    *   **Objetivo**: Garantizar que el volumen de preventa no se pierda ante la ausencia temporal de un preventista titular.
    *   **Definición Funcional**: Cruza transacciones con el padrón de ausencias mediante claves compuestas por preventista y fecha (`ClaveAUS`), reasignando el volumen al preventista de reemplazo operativo (`CodVendedorOperativo`)[cite: 3].
    *   **Fuente de Datos**: `vta`, `ausencias`.
    *   **Campos Involucrados**: `CodVendedor`, `FechaCarga`, `FechaEntrega`, `Reemplazo`.
    *   **Módulos de Aplicación**: `rep_ccc.py`, `rep_kilos.py`, `rep_gerencial.py`[cite: 3].
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Obligatoria.
    *   **Candidata a BUSINESS RULES**: **Sí (Obligatoria)**.

*   **14. Proyección Lineal de Kilos por Días Restantes**
    *   **Objetivo**: Estimar el volumen proyectado de cierre mensual para la toma de decisiones gerenciales.
    *   **Definición Funcional**: Multiplica el promedio diario actual del preventista por los días hábiles restantes del mes (pudiendo descontar ineficiencias logísticas mediante el modo de ajuste `AJUSTADO` basado en `Rutas_Ajustadas`).
    *   **Fuente de Datos**: `vta`, `rutas`, `maestro_vendedores`.
    *   **Campos Involucrados**: `PesoKg`, fechas de rutas, `Rutas_Ajustadas`.
    *   **Módulos de Aplicación**: `rep_kilos.py`, `rep_gerencial.py`.
    *   **Prioridad**: Alta.
    *   **Naturaleza**: Configurable (modos `TODO` vs `AJUSTADO`).
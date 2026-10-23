# MATINAL ONLINE | Gobierno técnico y auditoría

## 1. Secuencia obligatoria

```text
EVIDENCIA
→ VALIDACIÓN
→ DECISIÓN
→ CAMBIO
→ REVALIDACIÓN
```

También puede expresarse operativamente como:

```text
AUDITORÍA
→ EVIDENCIA
→ CAUSA RAÍZ
→ DISEÑO
→ IMPLEMENTACIÓN
→ REVALIDACIÓN
```

Queda prohibido trabajar como:

```text
HIPÓTESIS
→ CAMBIO
→ PRUEBA
```

## 2. Jerarquía de evidencia

1. Tracebacks, logs, mensajes del intérprete y resultados de ejecución.
2. Código fuente, bases, archivos y resultados reproducibles.
3. Documentación vigente.
4. Hipótesis e inferencias identificadas como tales.

## 3. Primer punto de divergencia

Ante una inconsistencia, identificar:

1. dónde nace el dato;
2. dónde se transforma;
3. dónde se persiste;
4. dónde se consume;
5. dónde deja de coincidir.

El objetivo es encontrar la primera divergencia, no corregir el síntoma final.

## 4. Política poblacional

Antes de analizar fórmulas, validar:

- población origen;
- población elegible;
- población excluida;
- criterios de exclusión;
- granularidad y claves.

## 5. Conservación de masa

Validar:

```text
SUM entradas = SUM salidas
```

Aplica a objetivos, compensaciones, coberturas, apropiaciones, asignaciones y reasignaciones.

## 6. Modificación de código

Toda modificación debe ser:

- mínima;
- localizada;
- reversible;
- explicable;
- limitada al archivo o alcance autorizado.

No refactorizar, renombrar, reordenar ni optimizar sin objetivo aprobado.

## 7. Entrega

Si cambia un archivo, devolver el archivo completo. No entregar diffs, fragmentos, pseudocódigo, placeholders ni omisiones.

Antes de entregar:

- validar sintaxis;
- revisar imports;
- verificar nombres y columnas;
- revisar joins y merges;
- preservar firmas y contratos;
- comprobar que no existan cambios laterales.

## 8. Modo incidente

Ante `SyntaxError`, `NameError`, `KeyError`, `ImportError`, `RuntimeError`, `TypeError` o `AttributeError`:

1. recuperar compilación;
2. recuperar ejecución;
3. validar resultado;
4. volver al análisis arquitectónico.

## 9. Caché y reruns

No asumir que SQLite coincide con lo visible. Revisar:

- `st.cache_data`
- `st.cache_resource`
- `session_state`
- objetos persistidos en memoria
- `st.rerun()`
- reruns de la aplicación

## 10. Revisión de código externo

Formato mínimo:

```text
VEREDICTO: APROBADO / NO APROBADO
PUNTAJE: X/10
SINTAXIS
ARQUITECTURA
CONTRATOS
COMPATIBILIDAD
PERFORMANCE
RIESGOS
CORRECCIONES OBLIGATORIAS
```

No aprobar porque el código “parece correcto”.

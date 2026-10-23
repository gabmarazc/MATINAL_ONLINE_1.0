# MATINAL ONLINE | Inventario técnico y dependencias

## 1. Archivos raíz relevantes

- `app.py`: entrada, autenticación, filtros y navegación.
- `config.py`: rutas y configuración declarada.
- `data_loader.py`: sincronización de fuentes e inicialización.
- `contexto.py`: generación de documentación contextual.
- `AU.py`: auditoría auxiliar.
- `backup_matinal.py`: respaldo.
- `st_aggrid.py`: soporte de grillas.

## 2. Infraestructura

- `modules/database.py`
- `modules/staging.py`
- `modules/parametros.py`
- `modules/utils.py`
- `modules/logger.py`

## 3. CORE

### Transversal

- `core_operaciones.py`
- `core_ventas_base.py`
- `core_clientes.py`
- `core_vendedores.py`
- `core_validacion_periodo.py`

### Dominio

- `core_cobertura.py`
- `core_tp.py`
- `core_potencial_cliente.py`
- `core_potencial_cliente_segmento.py`

## 4. BUSINESS RULES

- `business_rules_repository.py`
- `business_rules_kilos.py`
- `business_rules_gross.py`
- `business_rules_ccc.py`
- `business_rules_mn.py`
- `business_rules_cobertura.py`
- `business_rules_gerencial.py`
- `business_rules_tp.py`
- `business_rules_objetivo_clientes.py`
- `business_rules_objetivo_segmentos.py`
- `business_rules_objetivo_carteras.py`

## 5. Reportes productivos

- `rep_gerencial_core.py`
- `rep_kilos_core.py`
- `rep_obj_kilos_core.py`
- `rep_ccc_core.py`
- `rep_MN_core.py`
- `rep_cobertura_core.py`
- `rep_tp_core.py`

## 6. Navegación principal

```text
app.py
├── rep_gerencial_core
├── rep_kilos_core
├── rep_obj_kilos_core
├── rep_ccc_core
├── rep_cobertura_core
├── rep_MN_core
├── rep_tp_core
└── parametros
```

## 7. Dependencias resumidas

### Kilos

```text
rep_kilos_core
└── business_rules_kilos
    ├── business_rules_repository
    ├── core_vendedores
    └── core_operaciones
        └── staging
```

### Gross

```text
business_rules_gross
├── core_vendedores
├── core_operaciones
└── staging_maestros
```

Gross forma parte del motor gerencial y no tiene reporte independiente visible.

### Gerencial

```text
rep_gerencial_core
├── business_rules_gerencial
├── rep_ccc_core
├── rep_MN_core
└── database
```

### CCC

```text
rep_ccc_core
├── business_rules_ccc
│   ├── core_operaciones
│   ├── core_clientes
│   ├── core_vendedores
│   ├── database
│   └── ALTAS.xlsx como fallback
└── database
```

### MiNegocio

```text
rep_MN_core
└── business_rules_mn
    ├── core_operaciones
    ├── core_clientes
    └── core_vendedores
```

### Tienda Perfecta

```text
rep_tp_core
└── business_rules_tp
    └── core_tp
        └── database
```

### Cobertura

```text
rep_cobertura_core
├── database
├── core_cobertura
│   ├── core_operaciones
│   ├── core_clientes
│   ├── core_vendedores
│   ├── staging_rutas
│   └── business_rules_cobertura
└── cálculos y pivotes del reporte
```

### Objetivos

```text
rep_obj_kilos_core
└── business_rules_objetivo_segmentos
    └── business_rules_objetivo_carteras
        └── business_rules_objetivo_clientes
            ├── core_potencial_cliente_segmento
            ├── staging_maestros
            └── database
```

## 8. Regla de actualización

Este inventario debe regenerarse cuando:

- se agregue, elimine o mueva un módulo;
- cambie una importación entre capas;
- un reporte pase a Legacy;
- cambie la navegación de `app.py`.

---
name: feature-first-architecture
description: Analiza la arquitectura de un proyecto frontend y propone, sin modificar nada, una reorganización feature-first con diagnóstico, archivos grandes a modularizar, reglas de dependencias y plan de migración incremental. Usar cuando el usuario pida auditar, reorganizar o escalar la estructura de src o una arquitectura por features (feature-first / feature-based folder structure, frontend architecture audit, refactor project structure).
---

# Arquitectura feature-first

Inspecciona el proyecto y entrega una propuesta de reorganización **feature-first** adaptada al stack real. Estructura de referencia:

```text
src/
├── components/
│   ├── features/
│   └── ui/        # UI compartida sin lógica de negocio
├── composables/   # o hooks según el framework
│   └── features/
├── services/
├── store/
├── types/
└── utils/
```

- `components/features`: UI agrupada por funcionalidad.
- `components/ui`: componentes compartidos y genéricos (botones, modales, layout).
- `composables/features` o `hooks/features`: lógica reutilizable por feature.
- `services`: APIs, persistencia e integraciones externas.
- `store`: estado global o compartido, solo cuando sea necesario.
- `types`: contratos y tipos compartidos.
- `utils`: utilidades genéricas, sin lógica de negocio.

Páginas y rutas siguen la convención del framework (p. ej. Next.js `app/`, Nuxt `pages/`, Angular `projects/` o modules) y deben ser finas: componen features, no contienen lógica. No copies esta estructura literalmente si el stack usa otra convención.

## Solo lectura

Esta skill es de análisis. NO:

- crees, edites, muevas, renombres ni elimines archivos;
- instales dependencias;
- cambies configuración;
- ejecutes migraciones;
- modifiques el repositorio de ninguna forma.

Usa solo herramientas y comandos de lectura. No ejecutes `npx` ni nada que descargue paquetes (p. ej. `madge`): si la herramienta no está instalada, detecta ciclos leyendo los imports.

## 1. Inspección

Primero localiza las raíces de código: `src/` o la convención del framework (`app/`, `pages/`, `projects/`). En un monorepo (`apps/*`, `packages/*`), analiza cada app o paquete relevante y entrega la propuesta por paquete.

Identifica:

- framework y stack (lee `package.json`, configs de build, alias de paths);
- estructura de cada raíz de código;
- features existentes;
- componentes, hooks/composables, services, stores, tipos y utilidades;
- responsabilidades mezcladas;
- lógica duplicada;
- componentes con demasiada lógica;
- llamadas HTTP desde UI (`fetch`, `axios`, clientes de API importados en componentes);
- stores sobredimensionados;
- imports cruzados problemáticos e imports profundos a internals de otra feature;
- posibles dependencias circulares;
- archivos excesivamente grandes.

Para tamaños, ejecuta desde la raíz del proyecto, una vez por raíz de código (`<skill-dir>` es el directorio que contiene este SKILL.md):

```bash
bash <skill-dir>/scripts/large-files.sh src 200
```

Lista archivos de código con más de 200 líneas, de mayor a menor, respetando `.gitignore` y excluyendo `*.d.ts` y `*.min.js`. Ignora también código generado, vendorizado o fixtures que el script no filtre.

## 2. Diseño

Favorece:

- alta cohesión por feature;
- bajo acoplamiento;
- separación UI / lógica / infraestructura;
- imports predecibles;
- escalabilidad;
- simplicidad, sin sobrearquitectura.

Una feature no necesita obligatoriamente componentes, store, services y tipos. Solo las carpetas que use. No añadas capas ni abstracciones innecesarias. No inventes módulos que no existan, salvo como ejemplos marcados como tales.

### Tamaño y modularización

| Líneas | Criterio |
|---|---|
| < 200 | Normalmente no requiere división. |
| 200–250 | Revisar, sobre todo UI, páginas, hooks o composables. |
| 250–300 | Evaluar activamente separar. |
| > 300 | Proponer división por responsabilidades salvo razón clara. |
| > 400 | División prácticamente obligatoria; justificar cualquier excepción. |

Divide **por responsabilidad**, no cortando por número de líneas. Prioriza separar cuando haya:

- varios componentes en el mismo archivo;
- lógica de negocio mezclada con UI;
- varios hooks/composables;
- tipos, constantes o configuraciones extensas;
- helpers reutilizables;
- secciones claramente independientes;
- dificultad para navegar, probar o mantener.

Convierte el archivo en carpeta cohesionada:

```text
orders/
├── index.ts
├── types.ts
├── utils.ts
├── useOrders.ts
└── OrdersTable.tsx
```

No propongas dividir si empeora la cohesión, genera archivos triviales o dificulta seguir el flujo.

### Reglas de dependencia

| Origen | Puede importar | No puede importar |
|---|---|---|
| páginas/rutas | features (API pública), `components/ui`, store | services directamente |
| components (UI) | hooks/composables, store, `components/ui`, types, utils | services, clientes HTTP |
| hooks/composables | services, store, types, utils | components |
| store | services, types, utils | components, hooks/composables |
| services | infraestructura externa, types, utils | components, hooks/composables, store |
| types | otros types | todo lo demás |
| utils | otros utils, types genéricos | cualquier feature |
| feature A | API pública de feature B (`index.ts`) | internals de feature B |

Cada feature usada desde fuera expone una API pública (p. ej. `index.ts`). Nada de imports profundos a sus archivos internos. Propón cómo hacerlo cumplir con herramientas (p. ej. `eslint-plugin-boundaries`, `import/no-restricted-paths`, `dependency-cruiser`, `madge` para ciclos), no solo como convención.

## 3. Entrega

Responde únicamente con estas secciones:

1. **Diagnóstico** breve de la arquitectura actual.
2. **Problemas detectados**, con rutas concretas.
3. **Archivos grandes a modularizar**, en formato: `Archivo → líneas aprox. → responsabilidades detectadas → estructura propuesta` (todos los > 300; los de 250–300 con varias responsabilidades van en la sección 2).
4. **Árbol de directorios propuesto.**
5. **Responsabilidad de cada carpeta.**
6. **Reglas de dependencias** y cómo hacerlas cumplir.
7. **Mapeo** estructura actual → propuesta.
8. **Ejemplo** de cómo añadir una nueva feature.
9. **Plan de migración incremental**: pasos pequeños y seguros; refactors sin cambio de conducta, separados de cambios funcionales.
10. **Riesgos o decisiones pendientes.**

Prioriza **cohesión y claridad** por encima de cumplir mecánicamente la estructura o los límites de líneas.

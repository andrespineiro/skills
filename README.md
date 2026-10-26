# skills

Skills personales para agentes. La [CLI de skills](https://github.com/vercel-labs/skills) detecta cada skill en `skills/<nombre>/SKILL.md`.

## Skills

- `feature-first-architecture`: análisis de solo lectura que propone reorganizar el `src` de un proyecto frontend con un enfoque feature-first.

## Instalación

Desde un proyecto:

```bash
npx skills add andrespineiro/skills
```

Listar las skills sin instalarlas:

```bash
npx skills add andrespineiro/skills --list
```

## Añadir una skill

1. Crea `skills/<nombre>/SKILL.md`.
2. Pon en `name` el nombre del directorio. Usa minúsculas, números y guiones.
3. Pon en `description` qué hace la skill y cuándo usarla.
4. Haz commit y push a `main`.

---
name: browser-routine-to-api
description: Replace the browser steps of a Claude Code routine with a script that hits the API directly, with the same auth, and show the token cost diff before changing anything. Use when a routine navigates, clicks or scrapes and the user wants it cheaper, faster or more reliable.
compatibility: Claude Code con routines (herramienta RemoteTrigger).
argument-hint: <routine>
---

Capture the network requests from the last run of the routine the user names. Turn them into a script that hits the API directly with the same auth. Replace the browser steps with the script and show me the diff in token cost before you change anything.

## Reglas que no son obvias

- **El HAR es un secreto**: contiene cookies, tokens y contraseñas en claro. No lo leas con `Read`/`cat`/`grep`; resúmelo con `python3 <dir de este SKILL.md>/scripts/har-summary.py <har>`, que redacta valores. Pide al usuario que lo deje fuera del repo y que lo borre al terminar.
- **Peticiones con efecto en el script, solo con `--execute`**. Sin el flag, muestra lo que enviaría. El prompt nuevo de la routine pasa `--execute`.
- **Diff de tokens honesto**: el log de la routine no trae uso de tokens. Si no puedes medir, estima turno a turno: cada turno reenvía todo el contexto acumulado (definiciones de herramientas, snapshots), separa input/caché/output, explicita supuestos y marca "estimado". Da total por run y por mes según el schedule, en tokens.
- **API interna**: si no es una API pública documentada, pregunta si se puede usar fuera de la web (términos de servicio) y si existe una oficial; no inventes paginación ni endpoints que no viste.
- **Orden tras la aprobación**: script mergeado en la rama que clona la routine → secretos configurados por el usuario en el entorno → `RemoteTrigger update` guardando el prompt anterior para rollback → preguntar antes de `RemoteTrigger run`, avisando de que el run de prueba actúa sobre datos reales.

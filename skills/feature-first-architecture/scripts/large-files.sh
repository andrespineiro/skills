#!/usr/bin/env bash
# Lista archivos de código fuente con más de N líneas (por defecto 200), de mayor a menor.
# En repos git respeta .gitignore (incluye no versionados); fuera de git usa find.
# Excluye código generado (*.d.ts, *.min.js). Rutas relativas al directorio actual.
# Uso: large-files.sh [dir] [min_lines]
set -euo pipefail

dir="${1:-src}"
min="${2:-200}"

[[ -d "$dir" ]] || { echo "No existe el directorio: $dir" >&2; exit 1; }
[[ "$min" =~ ^[0-9]+$ ]] || { echo "min_lines debe ser un entero: $min" >&2; exit 1; }

list_files() {
  if git -C "$dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git ls-files -z --cached --others --exclude-standard -- "$dir"
  else
    find "$dir" \( -name node_modules -o -name .git -o -name dist -o -name build \) -prune -o -type f -print0
  fi
}

list_files | while IFS= read -r -d '' f; do
  case "$f" in
    *.d.ts | *.min.js) continue ;;
    *.ts | *.tsx | *.js | *.jsx | *.mjs | *.cjs | *.vue | *.svelte | *.astro | *.component.html) ;;
    *) continue ;;
  esac
  [[ -f "$f" ]] || continue
  n=$(wc -l <"$f")
  if ((n > min)); then
    printf '%d\t%s\n' "$n" "$f"
  fi
done | sort -rn

#!/usr/bin/env python3
"""
Regenera el tablero HTML a partir de depas.json (que sale de la base de Notion).

    python3 build.py            -> lee depas.json, escribe depas.html

El HTML es la plantilla: se reemplaza solo el bloque entre los marcadores
/* <<<DATOS ... /* DATOS>>> */ , así que cualquier mejora de diseño que se le
haga a depas.html sobrevive a la siguiente regeneración.
"""
import json, re, sys, pathlib
import validar as V

BASE = pathlib.Path(__file__).parent
TPL  = BASE / "index.html"
DATA = BASE / "depas.json"

INI = "/* <<<DATOS — bloque generado desde Notion, no editar a mano */"
FIN = "/* DATOS>>> */"

def js(v):
    """Serializa a JS legible (JSON es JS válido)."""
    return json.dumps(v, ensure_ascii=False)

def bloque(depas):
    filas = []
    for d in depas:
        filas.append(" " + js(d))
    return INI + "\nconst DEPAS = [\n" + ",\n".join(filas) + "\n];\n" + FIN

def main():
    if not DATA.exists():
        sys.exit(f"Falta {DATA}. Genera el JSON desde Notion primero.")
    depas = json.loads(DATA.read_text(encoding="utf-8"))

    errores, avisos = V.validar(depas)
    for a in avisos:
        print(f"  ⚠  {a}")
    if errores:
        for e in errores:
            print(f"  ✕  {e}")
        sys.exit(f"\n{len(errores)} error(es) de validación — no construyo el HTML.")

    html  = TPL.read_text(encoding="utf-8")
    patron = re.compile(re.escape(INI) + r".*?" + re.escape(FIN), re.S)
    if not patron.search(html):
        sys.exit("No encontré los marcadores de datos en depas.html.")
    TPL.write_text(patron.sub(lambda _: bloque(depas), html), encoding="utf-8")
    dentro = sum(1 for d in depas
                 if (V.precio_todo(d) or 0) <= 260000 and d.get("precio") is not None)
    print(f"OK · {len(depas)} depas escritos · {dentro} dentro del tope")

if __name__ == "__main__":
    main()

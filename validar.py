#!/usr/bin/env python3
"""
Valida depas.json ANTES de construir el HTML.
Corre solo desde build.py; también se puede correr suelto:  python3 validar.py

Cada regla nació de una falla real. No borrar reglas sin entender cuál.
"""
import json, re, sys, pathlib
from collections import defaultdict

BASE = pathlib.Path(__file__).parent
TOPE_OK, TOPE_MAX = 250_000, 260_000

# Campos que SIEMPRE deben existir con un valor real
OBLIGATORIOS = ["id", "nombre", "zona", "estado", "quien", "fuente",
                "m2Techados", "dorms", "fotos"]  # precio se valida aparte: puede faltar

# Campos donde "no sé" se escribe null, NUNCA 0 ni false.
# Regla que nació de haber escrito "Depósito: no tiene" cuando el aviso
# simplemente no lo mencionaba.
TRISTATE = ["deposito", "balcon", "medioBano", "estreno"]
NUMERICOS_NULABLES = ["piso", "ascensores", "m2Libres", "antiguedad", "banos"]

ESTADOS = {"por_ver", "contactado", "cita", "visitado", "finalista", "descartado"}
QUIEN   = {"Rodrigo", "Mamá"}

def precio_todo(d):
    if d.get("precio") is None:
        return None
    return d["precio"] + (d.get("precioEst") or 0) + (d.get("precioDep") or 0)

def id_aviso(url):
    """Saca el id numérico del aviso para detectar duplicados entre portales."""
    if not url:
        return None
    m = re.search(r"(\d{7,12})(?:\?|$|-)", url)
    return m.group(1) if m else None

def norm_dir(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def validar(depas):
    errores, avisos = [], []
    vistos_id, vistos_dir, vistos_url = defaultdict(list), defaultdict(list), defaultdict(list)

    for d in depas:
        et = f"[{d.get('id','?')} {d.get('nombre','sin nombre')}]"

        # --- 1. campos obligatorios ---
        for c in OBLIGATORIOS:
            if d.get(c) in (None, "", []):
                errores.append(f"{et} falta '{c}'")

        # --- 2. fotos: la falla #1 fue publicar un depa sin fotos ---
        fotos = d.get("fotos") or []
        if not fotos:
            if d.get("fuente") in ("WhatsApp / PDF", "Referido"):
                avisos.append(f"{et} sin fotos — pedir el material al corredor")
            else:
                errores.append(f"{et} SIN FOTOS — hay que extraer la galería completa del aviso")
        elif len(fotos) <= 5 and d.get("fuente") in ("Urbania", "Nexo Inmobiliario",
                                                     "Properati", "Adondevivir"):
            avisos.append(f"{et} solo {len(fotos)} fotos — los portales suelen tener 10-25. "
                          f"¿Abriste 'Ver todas las fotos'?")
        for f in fotos:
            fs = str(f)
            if not (fs.startswith("http") or fs.startswith("data:image/")):
                errores.append(f"{et} foto con URL inválida: {fs[:60]}")
        if len(fotos) != len(set(fotos)):
            avisos.append(f"{et} tiene fotos repetidas")

        # --- 3. tristate: 0/false no es lo mismo que "no sé" ---
        for c in TRISTATE:
            if c not in d:
                errores.append(f"{et} falta '{c}' — usa null si el aviso no lo dice, no false")
        for c in NUMERICOS_NULABLES:
            if c not in d:
                errores.append(f"{et} falta '{c}' — usa null si no se sabe")

        # --- 4. plata ---
        if d.get("precio") is None:
            avisos.append(f"{et} SIN PRECIO — no entra al ranking ni al gráfico hasta tenerlo. "
                          f"Es el dato que hay que pedir.")
        elif d["precio"] <= 0:
            errores.append(f"{et} precio inválido")
        if "precioEst" not in d or "precioDep" not in d:
            errores.append(f"{et} faltan precioEst / precioDep (0 = incluido en el precio)")
        if not d.get("incluye"):
            avisos.append(f"{et} sin nota 'incluye' — deja escrito si el estacionamiento "
                          f"y el depósito entran o se cobran aparte")
        if not d.get("gastosCierre"):
            avisos.append(f"{et} sin gastos de cierre — alcabala 3% sobre (valor − 10 UIT) "
                          f"+ notariales y registrales")
        if not d.get("mantenimiento"):
            avisos.append(f"{et} sin mantenimiento — es el costo que más se olvida")

        pt = precio_todo(d)
        if pt is not None and pt > TOPE_MAX:
            avisos.append(f"{et} US$ {pt:,} — SOBRE EL TOPE por US$ {pt-TOPE_MAX:,}")

        # --- 5. coherencia ---
        if d.get("m2Techados", 0) <= 0:
            errores.append(f"{et} m2Techados inválido")
        elif d.get("precio") is not None:
            pm2 = d["precio"] / d["m2Techados"]
            if not 800 <= pm2 <= 6000:
                avisos.append(f"{et} US$ {pm2:,.0f}/m² está fuera de rango normal — "
                              f"¿el precio o los m² están mal?")
        if d.get("estado") not in ESTADOS:
            errores.append(f"{et} estado '{d.get('estado')}' no es válido {sorted(ESTADOS)}")
        if d.get("quien") not in QUIEN:
            errores.append(f"{et} 'quien' debe ser Rodrigo o Mamá (evita duplicados)")

        # --- 6. entrega ---
        e = d.get("entrega")
        if e is None:
            avisos.append(f"{et} sin fecha de entrega — preguntar al corredor si está ocupado")
        elif e != "inmediata" and not re.fullmatch(r"\d{4}-\d{2}", str(e)):
            errores.append(f"{et} entrega '{e}' inválida — usa \"inmediata\" o \"AAAA-MM\"")

        # --- 7. commutes: null es válido, 0 es sospechoso ---
        com = d.get("commute", {})
        for k in ("smartfit", "super", "malecon"):
            if k not in com:
                errores.append(f"{et} falta commute.{k} (usa null si aún no se midió)")
            elif com[k] == 0:
                avisos.append(f"{et} commute.{k} = 0 — ¿es null (sin medir) o de verdad 0?")

        # --- 8. duplicados ---
        if d.get("url"):
            vistos_url[d["url"]].append(d["id"])
            ia = id_aviso(d["url"])
            if ia:
                vistos_id[ia].append(d["id"])
        if d.get("direccion"):
            vistos_dir[norm_dir(d["direccion"])].append(d["id"])

    # huella para los que NO tienen link (PDF/WhatsApp): mismo precio + m² + zona
    huellas = defaultdict(list)
    for d in depas:
        if not d.get("url"):
            huellas[(d.get("zona"), d.get("precio"), d.get("m2Techados"))].append(d.get("id"))
    for k, ids in huellas.items():
        if len(ids) > 1 and k[1] is not None:
            avisos.append(f"POSIBLE DUPLICADO sin link: {', '.join(ids)} comparten "
                          f"zona/precio/m² {k} — verificar si es el mismo inmueble")
    # y contra los que sí tienen link
    con_link = {(d.get("zona"), d.get("precio"), d.get("m2Techados")): d.get("id")
                for d in depas if d.get("url")}
    for k, ids in huellas.items():
        if k in con_link:
            avisos.append(f"POSIBLE DUPLICADO: {', '.join(ids)} (sin link) coincide con "
                          f"{con_link[k]} (con aviso) en zona/precio/m²")

    por_id0 = {d.get("id"): d for d in depas}
    for grupo, etiqueta in ((vistos_id, "mismo aviso"), (vistos_url, "misma URL")):
        for k, ids in grupo.items():
            if len(ids) < 2:
                continue
            firmas = {(por_id0[i].get("precio"), por_id0[i].get("m2Techados")) for i in ids}
            if len(firmas) == 1:
                errores.append(f"DUPLICADO ({etiqueta}): {', '.join(ids)} → {k}")
            else:
                avisos.append(f"Mismo link, unidades distintas: {', '.join(ids)} → {k}")

    # Misma dirección puede ser el MISMO edificio con unidades distintas (un proyecto
    # con varias tipologías). Solo es duplicado si además coinciden precio y m².
    por_id = {d.get("id"): d for d in depas}
    for k, ids in vistos_dir.items():
        if len(ids) < 2:
            continue
        firmas = {(por_id[i].get("precio"), por_id[i].get("m2Techados")) for i in ids}
        if len(firmas) == 1:
            errores.append(f"DUPLICADO (misma dirección, mismo precio y m²): {', '.join(ids)} → {k}")
        else:
            avisos.append(f"Mismo edificio, unidades distintas: {', '.join(ids)} → {k}. "
                          f"Correcto si son tipologías diferentes del mismo proyecto.")

    ids = [d.get("id") for d in depas]
    for i in set(ids):
        if ids.count(i) > 1:
            errores.append(f"id repetido: {i}")

    return errores, avisos

def main():
    depas = json.loads((BASE / "depas.json").read_text(encoding="utf-8"))
    errores, avisos = validar(depas)
    for a in avisos:
        print(f"  ⚠  {a}")
    for e in errores:
        print(f"  ✕  {e}")
    if errores:
        print(f"\n{len(errores)} error(es) — no se construye el HTML hasta arreglarlos.")
        sys.exit(1)
    print(f"✓ {len(depas)} depas validados" + (f" · {len(avisos)} aviso(s) para revisar" if avisos else ""))

if __name__ == "__main__":
    main()

# Prospección de departamentos

Tablero para comparar departamentos en venta en Lima. Publicado en GitHub Pages.

**Tope de presupuesto: US$ 260,000 todo incluido** (departamento + estacionamiento + depósito).
US$ 250,000 es la zona cómoda.

## Qué muestra

| Vista | Para qué sirve |
|---|---|
| **Pipeline** | Tablero por estado: Por ver → Contactado → Cita agendada → Visitado → Finalista / Descartado |
| **Comparativa** | Tabla ordenable con el mejor valor de cada criterio resaltado |
| **Cara a cara** | Hasta 4 departamentos lado a lado, fila por fila |
| **Mapa** | Dónde está cada uno, con el color según el precio por m² |
| **Precio / m²** | Dispersión con la banda de presupuesto y el promedio del set |

Cada ficha trae fotos, todos los datos, notas, y un checklist de preguntas para el corredor.

## Cómo se actualiza

Los datos viven en `depas.json`. El HTML es la plantilla: `build.py` valida y reemplaza
solo el bloque marcado entre `/* <<<DATOS` y `/* DATOS>>> */`, así que el diseño sobrevive
a cada regeneración.

```bash
python3 build.py     # valida depas.json y regenera index.html
python3 validar.py   # solo valida, sin construir
```

`build.py` **se niega a construir** si `validar.py` encuentra errores.

## Las reglas del validador

Cada una nació de un error real:

- **Ausencia de dato es `null`, nunca un negativo inventado.** Si el aviso no menciona
  depósito, no significa que no tenga.
- **Ninguna foto entra sin verificar que carga.** Y si un aviso de portal trae 5 fotos o
  menos, avisa: probablemente no se abrió la galería completa.
- **Precio "todo incluido"**: departamento + estacionamiento + depósito. Un estacionamiento
  cobrado aparte cuesta US$ 12,000–18,000 y es lo que más veces rompe el presupuesto.
- **Duplicados** por id de aviso, URL, dirección normalizada, y huella de zona+precio+m²
  para los que llegan por WhatsApp sin link.
- **Un mismo edificio puede tener varias unidades**: solo es duplicado si además coinciden
  precio y m².
- **Un departamento sin precio es válido** — queda registrado pero fuera del ranking y del
  gráfico hasta que se consiga el dato.

## Estructura de un registro

```jsonc
{
  "id": "D01",
  "nombre": "...",
  "zona": "Miraflores",
  "estado": "por_ver",          // por_ver | contactado | cita | visitado | finalista | descartado
  "quien": "Rodrigo",           // quién lo mandó: evita duplicados
  "precio": 220000,             // US$, o null si no se publicó
  "precioEst": null,            // costo del estacionamiento; 0 = incluido; null = por confirmar
  "precioDep": null,            // ídem depósito
  "gastosCierre": 7200,         // alcabala + notariales + registrales
  "m2Techados": 81,
  "dorms": 2, "banos": 2, "medioBano": true,
  "entrega": "inmediata",       // "inmediata" o "AAAA-MM"
  "commute": { "smartfit": null, "super": null, "malecon": 2 },
  "fotos": ["https://...", "data:image/jpeg;base64,..."],
  "geo": [-12.12885, -77.027]   // para el mapa
}
```

## Notas de cálculo

- **Tipo de cambio:** 3.365 soles por dólar (17/08/2026). Está en la constante `TC`.
- **Alcabala:** 3% sobre (valor − 10 UIT). UIT 2026 = S/ 5,500, o sea 10 UIT = S/ 55,000.
  La primera venta de constructora está inafecta salvo el valor del terreno — por eso los
  proyectos nuevos tienen gastos de cierre mucho más bajos.
- **El score** es relativo al set: 100 es el mejor de la lista en cada criterio. Los pesos
  se ajustan desde el panel del tablero.

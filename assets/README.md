# Marca e iconos de Codex Model Router

## Iconos funcionales de la aplicación

El catálogo funcional se unifica con **Lucide 1.51.0**: 39 SVG originales
en `assets/lucide/icons`, licencia íntegra en `assets/lucide/LICENSE` y versión,
integridad del paquete y SHA-256 de cada SVG en `assets/lucide/manifest.json`.
Proceden de `lucide-static` publicado por Lucide; no son dibujos propios.

`tools/vendor_icons.py` comprueba la integridad SHA-512 del paquete y copia
solo los SVG usados. Sus representaciones `monitor-ui/icons.js` y
`MonitorIcons.cs` conservan las primitivas del original para WebKit y WPF.
El PNG template de la bandeja Mac (`monitor-ui/tray-route.png`) es una
rasterización del SVG `route`, sin cambiar el diseño. La licencia también
se incluye en el bundle del monitor (`lucide-license.txt`). Todo funciona localmente.

Los personajes Milo/Lumi/Nori son ilustraciones originales SVG construidas por
la interfaz, independientes del modelo. Checks, números, barras y nodos de la
pipeline representan estados/datos; no se añaden al catálogo Lucide. Los
personajes no usan imágenes generadas ni descargas en tiempo de ejecución.

Los anillos históricos de cuota/contexto, puntos de estado, barras y órbitas son
visualizaciones de datos, no pictogramas del catálogo. El logo existente del
acceso sigue siendo el recurso de marca descrito abajo, separado de Lucide.
Los checkmarks estándar que dibuja el sistema en sus menús no son dibujos
de la aplicación. `Monitor.cs` es un host WinForms legado, no usado por
`build.ps1`; solo usa el recurso de marca y no tiene catálogo propio de glyphs.

Para reproducir/verificar el subconjunto con el paquete público original:

```sh
python3 tools/vendor_icons.py --tarball /ruta/lucide-static-1.51.0.tgz --check
```

Referencia y licencia: [Lucide](https://lucide.dev/),
[licencia ISC y avisos Feather](https://lucide.dev/license).

## Imagen de marca aprobada — 2026-10-09

![Codex Model Router](brand/router-256.png)

El propietario aprobó el símbolo de una entrada que se ramifica hacia tres
modelos: turquesa, dorado y lila sobre grafito. La propuesta se generó con
`image_gen`, sin imágenes de entrada, y se conserva píxel a píxel en
`brand/router-source.png`. El [brief y prompt](../docs/design/brand/README.md)
documentan la procedencia. La licencia del proyecto se aplica a esta marca.

| Archivo | Uso |
| --- | --- |
| `brand/router-source.png` | Máster aprobado, 1254 × 1254 |
| `brand/router-1024.png` | Interfaz, paquetes y acceso Ubuntu |
| `brand/router-256.png` | Documentación, vista previa y ventanas/bandeja Ubuntu |
| `brand/router.ico` | Windows: 16, 24, 32, 48, 64, 128 y 256 px |
| `brand/router.icns` | Bundles de monitor, lanzador y paquete macOS |
| `brand/manifest.json` | Procedencia, paleta, tamaños y SHA-256 |

Los exportados solo cambian formato y resolución: no redibujan ni recortan el
máster. Conserva la proporción cuadrada, los colores y el espacio de seguridad;
no estires el símbolo ni lo uses para representar un modelo concreto. La bandeja
monocroma de Mac sigue usando el pictograma funcional Lucide `route`.

Para regenerar, usa un entorno aislado con `tools/requirements-brand.txt` y
ejecuta `python tools/render_brand_assets.py`. Para verificar sin Pillow:
`python3 tools/render_brand_assets.py --check`. Los paquetes consumen los
exportados incluidos; el usuario final no necesita Pillow ni compilar imágenes.

Los antiguos `codex-official.png`, `codex-ui-1024.png` y `codex.ico`, obtenidos de
un espejo de un listado de Product Hunt, se han retirado del árbol actual y de
sus consumidores. Se conservan únicamente en el historial Git y en una copia
privada local. Esto no reescribe el historial ni acredita permisos sobre aquellas
imágenes históricas. La integración en código no sustituye la instalación activa.

## Tipografía del monitor

La interfaz compartida utiliza Nunito variable (peso 200–1000, estilo normal),
obtenida sin modificaciones del repositorio oficial [Google Fonts](https://github.com/google/fonts/tree/main/ofl/nunito).
El archivo se distribuye localmente en `monitor-ui/fonts/Nunito-variable.ttf`,
con la licencia SIL Open Font License 1.1 íntegra (`OFL-Nunito.txt`) y un manifiesto
con revisión de origen, URL, tamaño y SHA-256. Los tres paquetes copian esta misma
carpeta; el monitor no descarga fuentes al ejecutarse.

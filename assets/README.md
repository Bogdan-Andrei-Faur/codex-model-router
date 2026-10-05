# Icono del acceso personal

## Iconos funcionales de la aplicación

El catálogo funcional se unifica con **Lucide 1.51.0**: 27 SVG originales
en `assets/lucide/icons`, licencia íntegra en `assets/lucide/LICENSE` y versión,
integridad del paquete y SHA-256 de cada SVG en `assets/lucide/manifest.json`.
Proceden de `lucide-static` publicado por Lucide; no son dibujos propios.

`tools/vendor_icons.py` comprueba la integridad SHA-512 del paquete y copia
solo los SVG usados. Sus representaciones `monitor-ui/icons.js` y
`MonitorIcons.cs` conservan las primitivas del original para WebKit y WPF.
El PNG template de la bandeja Mac (`monitor-ui/tray-route.png`) es una
rasterización del SVG `route`, sin cambiar el diseño. La licencia también
se incluye en el bundle del monitor (`lucide-license.txt`). Todo funciona localmente.

Los anillos de cuota/contexto, puntos de estado, barras y órbitas son
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

## Recurso de marca del acceso

`codex-official.png` reproduce el icono azul/violeta de Codex con terminal blanco
de su ficha pública de lanzamiento. Se obtuvo de la imagen del listado de
Product Hunt, enlazada por [ProductCool](https://www.productcool.com/product/codex-by-openai-3):

https://ph-files.imgix.net/64f50b38-7e9e-47ca-b2e9-2939ff10431a.png?w=256&h=256&fit=crop&fm=png

El icono se inspeccionó visualmente y se utiliza para identificar el acceso
personal a Codex. La descarga procede del espejo del listado, no de un paquete
oficial de recursos de marca verificado. No se reivindica autoría de la imagen.

`build.ps1` empaqueta el PNG sin alterarlo en `codex.ico`, para los ejecutables y
accesos de Windows. No modifica los recursos de la aplicación instalada.

`codex-ui-1024.png` es la imagen original de 1024 x 1024 del mismo listado,
descargada sin los parametros de reduccion el 2026-09-21:
https://ph-files.imgix.net/64f50b38-7e9e-47ca-b2e9-2939ff10431a.png
El monitor usa esta version con escalado de alta calidad. El ICO conserva la
version de 256 x 256 para compatibilidad con el formato de iconos de Windows.

# Third-party notices

The root [LICENSE](LICENSE) covers original project material only. It does not
relicense third-party material or restrict rights granted by its own license.
These notices identify the directly vendored visual dependencies; they are not
a complete inventory of the Python, OS or native runtime dependencies.
Installed native resources also include self-contained copies of the Lucide and
Nunito license texts in `licenses/Lucide.txt` and `licenses/Nunito.txt`, beside
`LICENSE` and this file. Ubuntu additionally includes these four notices under
`/usr/share/doc/codex-model-router/`.

| Material | Original terms and notices |
| --- | --- |
| Lucide SVGs and their derived renderings | ISC; some Feather-derived icons additionally carry MIT notices. Full text: `assets/lucide/LICENSE`, also shipped as `ui/lucide-license.txt`. Origin and hashes: `assets/lucide/manifest.json`. |
| Nunito variable font | SIL Open Font License 1.1. Full text: `monitor-ui/fonts/OFL-Nunito.txt`, shipped as `ui/fonts/OFL-Nunito.txt`. Origin and hashes: `monitor-ui/fonts/manifest.json`. |

The current application brand in `assets/brand/` is the owner-approved generated
routing artwork, covered by the project license. Historical third-party Codex
images were retired from the current tree and package consumers on 2026-10-09;
they remain in Git history. The root license grants no rights to those historical
images or marks. Their recorded provenance did not establish redistribution
permission; changing current assets does not resolve historical exposure review.

GitHub, OpenAI, ChatGPT, Codex, Microsoft, Windows, Apple, macOS and Ubuntu names
identify third-party services or platforms. This project does not claim their
marks or imply their endorsement. Bundled runtimes and libraries retain their
respective license terms; public release preparation must verify their notices
and redistribution conditions for the exact packaged artifact.

Frozen Mac/Windows builds additionally copy the installed `cryptography`, `cffi`
and `pycparser` distribution license files into `licenses/<distribution>/`.
Their exact versions come from the pinned build inputs. Ubuntu declares its
system `python3-cryptography` dependency instead of vendoring that wheel.
This does not complete the release artifact inventory: Python/PyInstaller,
OpenSSL and statically linked/transitive Rust library notices must be verified
for each exact public installer before distribution.

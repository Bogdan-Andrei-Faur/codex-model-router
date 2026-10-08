# Opening metric alignment — Ubuntu — 2026-10-08

Artifact `codex-model-router_0.9.6-1~notch34_all.deb`, SHA-256 `07a48b108f1497afdfcf9ef11a2b5300f54585474f3893873746d59d6aa77771`.
Development branch `feature/dynamic-notch-monitor`; baseline `0.9.6`.

During width expansion the two metric labels can wrap differently. Grid stretch
made their containers equally tall, while the native button formatting centered
quota content; their tracks could diverge until the width stabilized. Aligning
Home metric items to the row's end keeps track bottoms aligned through reflow.
No measurement, routing, timing or native host behavior changed.

The new geometry regression reproduces a 24px offset with the old stretch style
at a 560px surface. It passes with the fix across transitional widths, real
animation frames, known/unknown/compacting context and the clickable quota.
The preview fixture also passes. Its return-to-Home wait now waits for the
expected Home height: diagnostics showed its previous condition could pass at
the old 580px height before it settled to 315px. No runtime timing workaround.

Package installation confirmed by `dpkg-query`; runtime activation/readback
was superseded by `1~notch35` (see the Agents simplification receipt). Native GTK fixture was not repeated for this one-rule
CSS correction; physical owner confirmation and Mac/Windows native gates remain
open. The existing live bridge restart and intermittent quota Escape issue are
separate pending items. No remote publication or private data in this receipt.

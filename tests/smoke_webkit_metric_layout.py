"""Check opening metrics in real GTK/WebKit using synthetic data only.

Run: xvfb-run -a /usr/bin/python3 tests/smoke_webkit_metric_layout.py
An optional UI directory lets the same regression exercise extracted packages.
"""
import json
import os
from pathlib import Path
import sys

# Honor the isolated Xvfb DISPLAY even when the caller has a Wayland session.
# Otherwise GTK can use the owner's compositor and animation frames may pause.
os.environ['GDK_BACKEND'] = 'x11'

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import GLib, Gtk, WebKit2

PROBE = r"""
(async()=>{
  await document.fonts.ready;
  const frame=()=>new Promise(requestAnimationFrame), samples=[];
  for(const context of [{context_window:{used_percent:29.1}}, {}, {context_compaction:{state:'compacting'}}]){
    setMode('Compact');
    for(let i=0;i<30;i++)await frame();
    window.receive({connections:1,threads:{a:{name:'Enrutador de IA',status:'active',
      model:'gpt-6-astra',effort:'high',...context},b:{name:'Backend Modular',status:'active'}},
      accountUsage:{windows:[{duration_minutes:10080,remaining_percent:72}],valid_until:Date.now()/1000+3600}});
    setMode('Expanded');
    for(let i=0;i<45;i++){
      await frame();
      const box=document.querySelector('.hero-metrics'), rect=box.getBoundingClientRect(), css=getComputedStyle(box);
      const children=[...box.children].map(n=>n.getBoundingClientRect());
      const bars=[...box.querySelectorAll('[role=progressbar]')].map(n=>n.getBoundingClientRect());
      samples.push({extraHeight:rect.height-parseFloat(css.paddingTop)-parseFloat(css.paddingBottom)-Math.max(...children.map(r=>r.height)),
        barOffset:bars[1].bottom-bars[0].bottom});
    }
  }
  window.metricProbe={samples};
})().catch(error=>window.metricProbe={error:String(error)});
"""


def main():
    ui = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'monitor-ui'
    window = Gtk.Window()
    window.set_default_size(790, 900)
    web = WebKit2.WebView.new_with_context(WebKit2.WebContext.new_ephemeral())
    window.add(web)
    outcome = []

    def result(view, value, _):
        try:
            raw = view.evaluate_javascript_finish(value).to_string()
            if raw != 'null':
                outcome.append(json.loads(raw))
                Gtk.main_quit()
        except Exception as error:
            outcome.append({'error': str(error)})
            Gtk.main_quit()

    def poll():
        web.evaluate_javascript('JSON.stringify(window.metricProbe || null)', -1, None, None, None, result, None)
        return not outcome

    def loaded(view, event):
        if event == WebKit2.LoadEvent.FINISHED:
            view.evaluate_javascript(PROBE, -1, None, None, None, None, None)
            GLib.timeout_add(200, poll)

    web.connect('load-changed', loaded)
    window.show_all()
    web.load_uri((ui / 'index.html').resolve().as_uri())
    GLib.timeout_add_seconds(15, lambda: (Gtk.main_quit(), False)[1])
    Gtk.main()
    window.destroy()
    assert outcome, 'WebKit metric probe timed out'
    assert 'error' not in outcome[0], outcome[0]
    samples = outcome[0]['samples']
    assert len(samples) == 135, len(samples)
    extra = max(abs(s['extraHeight']) for s in samples)
    offset = max(abs(s['barOffset']) for s in samples)
    assert extra < 1, f'Opening retains {extra}px of empty metric height'
    assert offset < 1, f'Metric tracks diverge by {offset}px'
    print('PASS: WebKit opening/reopening has no stale metric space; tracks align for known/unknown/compacting context')


if __name__ == '__main__':
    main()

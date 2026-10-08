"""Linux/WebKit integration check after linux.py setup; run under xvfb-run."""
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from codex_model_router.monitor.monitor_linux import Monitor, GLib


def main():
    with tempfile.TemporaryDirectory(prefix='router-usage-gtk-') as tmp:
        root = Path(tmp); (root / 'state').mkdir()
        (root / 'preview.json').write_text(json.dumps({'threads': {'sample': {
            'name': 'Vista de prueba', 'status': 'active', 'model': 'gpt-6.1-sol',
            'context_window': {'used_percent': 37, 'used_tokens': 37000, 'capacity_tokens': 100000}}},
            'account_usage': {'remaining_percent': 76, 'valid_until': time.time() + 60}}))
        app = Monitor(root, preview=True)
        errors = []
        started = time.monotonic()
        def compaction_complete(web, result, _data):
            try:
                data = json.loads(web.evaluate_javascript_finish(result).to_string())
                assert data['started'] and data['animated'] and data['label'] and data['completed'] and data['measured'], data
                print(json.dumps({'webkit_gtk': True, 'quota_centered': True, 'agents_centered': True,
                                  'panel_quota_and_details': True, 'compaction_lifecycle': True}))
            except Exception as error:
                errors.append(str(error))
            finally:
                app.quit()
        def panel_complete(web, result, _data):
            try:
                data = json.loads(web.evaluate_javascript_finish(result).to_string())
                assert data['visible'] and data['details'] and data['quota'] == '76%', data
                script = """JSON.stringify((()=>{
                  const row={name:'Vista de prueba',status:'active',model:'gpt-6.1-sol'};
                  window.receive({threads:{sample:{...row,context_compaction:{state:'compacting'}}},ui:{mode:'Expanded',reduced:false}});
                  const ring=document.querySelector('.featured-row .compacting-ring');
                  const result={started:!!ring,animated:!!ring&&getComputedStyle(ring).animationName==='context-compacting',
                    label:document.querySelector('.featured-row .avatar').getAttribute('aria-label').includes('Compactando contexto')};
                  window.receive({threads:{sample:{...row,context_compaction:{state:'awaiting_usage'}}}});
                  result.completed=!document.querySelector('.compacting-ring')&&document.querySelector('.featured-row .avatar').title.includes('esperando nueva medición');
                  window.receive({threads:{sample:{...row,context_window:{used_percent:20,used_tokens:20,capacity_tokens:100}}}});
                  result.measured=document.querySelector('.featured-row .avatar').title.includes('Contexto usado: 20 %');
                  return result;})())"""
                app.web.evaluate_javascript(script, -1, None, app.page, None, compaction_complete, None)
            except Exception as error:
                errors.append(str(error))
                app.quit()
        def inspect_panel():
            script = """JSON.stringify((()=>{
              const button=document.querySelector('#quota-panel');button.click();
              return {quota:button.textContent,visible:button.getBoundingClientRect().width===44,
                details:!document.querySelector('#quota-panel-details').hidden &&
                  document.querySelector('#quota-panel-details').textContent.includes('Cuota disponible: 76 %')};})())"""
            app.web.evaluate_javascript(script, -1, None, app.page, None, panel_complete, None)
            return False
        def complete(web, result, _data):
            try:
                data = json.loads(web.evaluate_javascript_finish(result).to_string())
                assert data['quota'] == '76%', data
                assert '37 %' in data['context'], data
                assert abs(data['progress'] - .37) < .00001, data
                assert data['fit'], data
                assert data['centered'] and data['noCount'], data
                app.set_mode('Expanded')
                GLib.timeout_add(600, inspect_panel)
            except Exception as error:
                errors.append(str(error))
                app.quit()
        def inspect():
            if time.monotonic() - started > 20:
                errors.append('WebKit preview timed out'); app.quit(); return False
            if not app.ready or not app.last_payload:
                return True
            script = """JSON.stringify((()=>{
              const circle=document.querySelector('#agents .context-ring .usage-progress');
              const agent=document.querySelector('#agents').getBoundingClientRect(),quota=document.querySelector('#quota').getBoundingClientRect();
              return {quota:document.querySelector('#quota').textContent,
                context:document.querySelector('#agents .avatar').getAttribute('aria-label'),
                progress:1-Number(circle.getAttribute('stroke-dashoffset'))/Number(circle.getAttribute('stroke-dasharray')),
                fit:document.documentElement.scrollWidth<=innerWidth,
                noCount:!document.querySelector('#count'),centered:Math.abs(agent.y+agent.height/2-quota.y-quota.height/2)<.1};})())"""
            app.web.evaluate_javascript(script, -1, None, app.page, None, complete, None)
            return False
        GLib.timeout_add(250, inspect)
        app.run([sys.argv[0]])
        if errors:
            raise RuntimeError('; '.join(errors))


if __name__ == '__main__':
    main()

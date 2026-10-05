"""Vendor an exact, integrity-checked Lucide SVG subset; never invent artwork.

The web nodes and WPF geometries below are mechanical representations of the
original SVG primitives. Runtime does not download or execute upstream code.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.51.0'
URL = 'https://registry.npmjs.org/lucide-static/-/lucide-static-' + VERSION + '.tgz'
INTEGRITY = 'sha512-ts58ApMc5w5SHHUJBtGO+mgf9lo79FApQ1LttKQoJiMrWNZt8zxWA7R6owK6DoGA3XLjJXc/7rDJh1feonl79g=='
CATEGORIES = {'audit':'clipboard-check', 'tests':'flask-conical', 'architecture':'network',
              'correction':'bug', 'text':'text', 'interface':'panels-top-left', 'research':'search',
              'configuration':'settings-2', 'automation':'workflow', 'general':'circle-plus',
              'data':'database', 'performance':'gauge', 'deployment':'rocket',
              'versioning':'git-branch', 'integration':'plug', 'accessibility':'accessibility'}
CONTROLS = ['panel-left-open','panel-left-close','sliders-horizontal','x','pause','play',
            'circle-check','circle','check','plus','route']


def geometry(tag, attrs):
    """Convert supported SVG primitives to WPF's equivalent path grammar."""
    def n(key, default=0):
        return float(attrs.get(key, default))
    def f(value):
        return format(value, '.12g')
    if tag == 'path':
        return attrs['d']
    if tag in ('circle', 'ellipse'):
        x,y=n('cx'),n('cy');rx=n('r') if tag=='circle' else n('rx');ry=rx if tag=='circle' else n('ry')
        return f'M{f(x-rx)},{f(y)} A{f(rx)},{f(ry)} 0 1 0 {f(x+rx)},{f(y)} A{f(rx)},{f(ry)} 0 1 0 {f(x-rx)},{f(y)}'
    if tag == 'line':
        return f'M{f(n("x1"))},{f(n("y1"))} L{f(n("x2"))},{f(n("y2"))}'
    if tag in ('polyline', 'polygon'):
        values=attrs['points'].replace(',', ' ').split()
        if len(values)%2:raise ValueError('Unpaired SVG point')
        points=[','.join(values[i:i+2]) for i in range(0,len(values),2)]
        return 'M'+' L'.join(points)+(' Z' if tag=='polygon' else '')
    if tag == 'rect':
        x,y,w,h=n('x'),n('y'),n('width'),n('height');rx=min(n('rx',attrs.get('ry',0)),w/2);ry=min(n('ry',rx),h/2)
        if not rx or not ry:return f'M{f(x)},{f(y)} H{f(x+w)} V{f(y+h)} H{f(x)} Z'
        return f'M{f(x+rx)},{f(y)} H{f(x+w-rx)} A{f(rx)},{f(ry)} 0 0 1 {f(x+w)},{f(y+ry)} V{f(y+h-ry)} A{f(rx)},{f(ry)} 0 0 1 {f(x+w-rx)},{f(y+h)} H{f(x+rx)} A{f(rx)},{f(ry)} 0 0 1 {f(x)},{f(y+h-ry)} V{f(y+ry)} A{f(rx)},{f(ry)} 0 0 1 {f(x+rx)},{f(y)} Z'
    raise ValueError('Unsupported SVG primitive: '+tag)


def artifacts(raw):
    expected=INTEGRITY.split('-',1)[1]
    if base64.b64encode(hashlib.sha512(raw).digest()).decode()!=expected:
        raise ValueError('Lucide package integrity mismatch')
    archive=tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')
    meta=json.load(archive.extractfile('package/package.json'))
    if meta['version']!=VERSION:raise ValueError('Lucide version mismatch')
    files={};nodes={};paths={}
    for name in sorted(set(CATEGORIES.values())|set(CONTROLS)):
        original=archive.extractfile('package/icons/'+name+'.svg').read()
        root=ET.fromstring(original)
        if root.attrib.get('viewBox')!='0 0 24 24' or root.attrib.get('fill')!='none':raise ValueError('Unexpected SVG format')
        data=[]
        for child in root:
            tag=child.tag.rsplit('}',1)[-1];attrs=dict(child.attrib)
            if any(k not in {'d','cx','cy','r','rx','ry','x','y','width','height','x1','y1','x2','y2','points'} for k in attrs):
                raise ValueError('Unsupported SVG attribute: '+name)
            data.append([tag,attrs])
        nodes[name]=data;paths[name]=' '.join(geometry(tag,attrs) for tag,attrs in data)
        files['assets/lucide/icons/'+name+'.svg']=original
    license_text=archive.extractfile('package/LICENSE').read()
    files['assets/lucide/LICENSE']=license_text
    files['monitor-ui/lucide-license.txt']=license_text
    manifest={'package':'lucide-static','version':VERSION,'tarball':URL,'integrity':INTEGRITY,
              'license':'ISC with upstream Feather MIT notices','categories':CATEGORIES,
              'svg_sha256':{name:hashlib.sha256(files['assets/lucide/icons/'+name+'.svg']).hexdigest() for name in nodes}}
    files['assets/lucide/manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    header='/* Lucide '+VERSION+' original icon data. See lucide-license.txt; update with tools/vendor_icons.py. */\n'
    js=header+'(function(scope){\n  const catalog='+json.dumps({'version':VERSION,'categories':CATEGORIES,'nodes':nodes},ensure_ascii=False,separators=(',',':'))+';\n  if(typeof module!=="undefined"&&module.exports)module.exports=catalog;else scope.RouterIcons=catalog;\n})(typeof globalThis!=="undefined"?globalThis:this);\n'
    files['monitor-ui/icons.js']=js.encode()
    cs='// Lucide '+VERSION+' SVG primitives, mechanically converted; original artwork in assets/lucide/icons.\n// ISC/Feather MIT notices: assets/lucide/LICENSE. Do not edit paths; use tools/vendor_icons.py.\n'
    cs+='using System;\nusing System.Collections.Generic;\ninternal sealed partial class ModernRouterMonitor\n{\n    static readonly Dictionary<string,string> LucidePaths = new Dictionary<string,string> {\n'
    cs+=',\n'.join('        { '+json.dumps(name)+', '+json.dumps(path)+' }' for name,path in paths.items())
    cs+='\n    };\n    static string LucidePath(string name) { string path; if(!LucidePaths.TryGetValue(name,out path))throw new ArgumentException("Unknown Lucide icon", "name");return path; }\n}\n'
    files['MonitorIcons.cs']=cs.encode()
    return files


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tarball',type=Path);p.add_argument('--check',action='store_true');args=p.parse_args()
    raw=args.tarball.read_bytes() if args.tarball else urllib.request.urlopen(URL,timeout=30).read()
    files=artifacts(raw)
    for relative,content in files.items():
        target=ROOT/relative
        if args.check:
            if not target.is_file() or target.read_bytes()!=content:raise ValueError('Vendored artifact drift: '+relative)
        else:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    print(json.dumps({'lucide_version':VERSION,'upstream_integrity_verified':True,'original_svg_count':len(set(CATEGORIES.values())|set(CONTROLS)),'artifacts_checked':args.check}))


if __name__=='__main__':main()

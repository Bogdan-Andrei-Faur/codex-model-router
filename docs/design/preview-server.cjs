// Read-only local preview: only the proposal and its icon are exposed.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const routes={'/':['monitor-directions.html','text/html; charset=utf-8'],
  '/monitor-directions.html':['monitor-directions.html','text/html; charset=utf-8'],
  '/assets/codex-official.png':['../../assets/codex-official.png','image/png']};
http.createServer((req,res)=>{
  const entry=routes[new URL(req.url,'http://localhost').pathname];
  if(req.method!=='GET'||!entry){res.writeHead(404);res.end();return}
  res.writeHead(200,{'Content-Type':entry[1],'Cache-Control':'no-store'});
  fs.createReadStream(path.resolve(__dirname,entry[0])).pipe(res);
}).listen(8769,'127.0.0.1',()=>console.log('Design preview: http://127.0.0.1:8769'));

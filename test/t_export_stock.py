import json, re, sys, threading, http.server, functools, time
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lots=json.load(open(ROOT+'/test/lots_2026-11-07.json',encoding='utf-8'))['lots']
F={
 'f1':('pks_cindy.json',{'v':'4.78','who':'cindy','at':'2026-11-07T10:00:00Z','count':len(lots),'lots':lots}),
 's1':('pkstk_devA.json',{'v':'4.78','dev':'devA','nom':'S25','at':'2026-11-07T10:00:00Z','stamp':1,'delta':{'sv1-1|n|nm':2},'ov':{},'done':{},'box':{},'stick':{}}),
 's2':('pkstk_devB.json',{'v':'4.78','dev':'devB','nom':'Tablette','at':'2026-11-07T10:00:00Z','stamp':1,'delta':{'sv1-1|p|nm':1},'ov':{},'done':{},'box':{},'stick':{}}),
 'm1':('pkstkmv_devA_2026-11.json',{'dev':'devA','nom':'S25','moves':[{'t':'2026-11-07T09:00:00Z','c':'sv1-1','v':'n','e':'nm','d':2}]}),
 'm2':('pkstkmv_devB_2026-10.json',{'dev':'devB','nom':'Tablette','moves':[{'t':'2026-10-07T09:00:00Z','c':'sv1-1','v':'p','e':'nm','d':1}]}),
 'm3':('pkstkmv_devA_fait.json',{'ok':1}),
}
FAIL=set(sys.argv[1:])
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8765),functools.partial(H,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
def drive(route):
    u=urlparse(route.request.url); q=parse_qs(u.query)
    m=re.search(r'/files/([^/?]+)$',u.path)
    if m and q.get('alt')==['media']:
        fid=m.group(1)
        if fid in FAIL: return route.fulfill(status=500,body='x')
        if fid not in F: return route.fulfill(status=404,body='')
        return route.fulfill(status=200,content_type='application/json',body=json.dumps(F[fid][1]))
    if u.path.endswith('/files') and 'q' in q:
        qq=q['q'][0]; out=[]
        for fid,(n,_) in F.items():
            c=re.search(r"name contains '([^']*)'",qq); e=re.search(r"name = '([^']*)'",qq)
            if (c and c.group(1) in n) or (e and e.group(1)==n): out.append({'id':fid,'name':n,'modifiedTime':'2026-11-07T10:00:00.000Z'})
        return route.fulfill(status=200,content_type='application/json',body=json.dumps({'files':out}))
    if route.request.method!='GET':
        print('ECRITURE INATTENDUE',route.request.method,u.path); return route.fulfill(status=200,content_type='application/json',body='{"id":"w"}')
    return route.fulfill(status=200,content_type='application/json',body='{}')
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(accept_downloads=True,viewport={'width':1100,'height':800},service_workers='block')
    ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
    ctx.route('**/www.googleapis.com/**',drive)
    ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
    ctx.add_init_script("localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');localStorage.setItem('pks_dev','devA');localStorage.setItem('pks_devnom','S25');")
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8765/index.html'); pg.wait_for_timeout(4000)
    print('version',pg.evaluate('APP_VERSION'),'lots',pg.evaluate('lots.length'),'token',pg.evaluate('token'),'toast',pg.inner_text('#toast'))
    pg.click('#btnAcc'); pg.wait_for_selector('#a_stkx')
    print('bouton:',pg.inner_text('#a_stkx').replace('\n',' | '))
    if FAIL:
        pg.click('#a_stkx'); pg.wait_for_timeout(1500)
        print('toast:',pg.inner_text('#toast'),'| bouton:',pg.inner_text('#a_stkx').replace('\n',' | '))
    else:
        with pg.expect_download(timeout=8000) as dl: pg.click('#a_stkx')
        d=dl.value; path='/tmp/'+d.suggested_filename; d.save_as(path)
        j=json.load(open(path,encoding='utf-8'))
        print('fichier:',d.suggested_filename,'count',j['count'],[f['name'] for f in j['fichiers']])
        print('contenu identique à Drive:',all(f['data']==F[f['id']][1] for f in j['fichiers']),'| lots exclus:',not any(f['name'].startswith('pks_') for f in j['fichiers']))
        print('dev',j['dev'],j['devNom'],'attente',{k:len(v) for k,v in j['attente'].items()})
        pg.wait_for_timeout(300); print('toast:',pg.inner_text('#toast'))
    print('erreurs JS:',errs)
    b.close()
srv.shutdown()

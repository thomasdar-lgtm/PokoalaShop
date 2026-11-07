"""Test 4.82 : scans provisoires de Règne Delta (pika-collect) puis bascule sur TCGdex.
Vrais clics ; Drive, TCGdex et pika-collect simulés. python3 test/t_scans_me6.py"""
import json, re, os, threading, http.server, functools
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lots=json.load(open(ROOT+'/test/lots_2026-11-07.json',encoding='utf-8'))['lots']
stk=json.load(open(ROOT+'/test/stock_2026-11-07.json',encoding='utf-8'))
F={f['id']:f for f in stk['fichiers']}
F['lotsC']={'name':'pks_cindy.json','modifiedTime':'2026-11-07T14:05:00.000Z','data':{'v':'4.81','who':'cindy','count':len(lots),'lots':lots}}
PNG=open(ROOT+'/icons/'+sorted(os.listdir(ROOT+'/icons'))[0],'rb').read()
ETAT={'pub':False}
SYM=re.search(r"CACHE_SYM = '([^']+)'",open(ROOT+'/sw.js').read()).group(1); REQ=[]
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8767),functools.partial(H,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
def drive(route):
    r=route.request; u=urlparse(r.url)
    if r.method!='GET': return route.fulfill(status=200,content_type='application/json',body='{"id":"x"}')
    m=re.search(r'/files/([^/?]+)$',u.path)
    if m and 'alt=media' in u.query:
        f=F.get(m.group(1)); return route.fulfill(status=200 if f else 404,content_type='application/json',body=json.dumps(f['data']) if f else '')
    q=re.search(r"q=([^&]*)",u.query); from urllib.parse import unquote_plus; qq=unquote_plus(q.group(1)) if q else ''
    c=re.search(r"name contains '([^']*)'",qq); e=re.search(r"name = '([^']*)'",qq)
    out=[{'id':k,'name':f['name'],'modifiedTime':f['modifiedTime']} for k,f in F.items() if (c and c.group(1) in f['name']) or (e and e.group(1)==f['name'])]
    return route.fulfill(status=200,content_type='application/json',body=json.dumps({'files':out}))
def tcgapi(route):
    u=route.request.url; REQ.append(('api',u))
    if u.endswith('/sets/me06'):
        if not ETAT['pub']: return route.fulfill(status=404,body='')
        return route.fulfill(status=200,content_type='application/json',headers={'access-control-allow-origin':'*'},
            body=json.dumps({'id':'me06','cards':[{'id':'me06-001','localId':'001','name':'Scarhino','image':'https://assets.tcgdex.net/fr/me/me06/001'}]}))
    return route.fulfill(status=200,content_type='application/json',headers={'access-control-allow-origin':'*'},body='[]')
def img(route):
    u=route.request.url
    if '/me06/' in u or 'pika-collect' in u: REQ.append(('img',u))
    if 'assets.tcgdex.net' in u and '/me06/' in u and not ETAT['pub']: return route.fulfill(status=404,body='')
    return route.fulfill(status=200,content_type='image/png',headers={'access-control-allow-origin':'*'},body=PNG)
def compte(t): return len([1 for k,u in REQ if t(k,u)])
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1100,'height':800},service_workers='block')
    ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
    ctx.route('**/www.googleapis.com/**',drive)
    ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
    ctx.route('**/api.tcgdex.net/**',tcgapi)
    for h in ['assets.tcgdex.net','pika-collect.fr','images.pokemontcg.io','images.scrydex.com','assets.pokemon.com']: ctx.route('**/%s/**'%h,img)
    ctx.add_init_script("if(!sessionStorage.getItem('i')){sessionStorage.setItem('i','1');localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');localStorage.setItem('pks_dev','mvdtytc1vf7kr7');localStorage.setItem('pks_devnom','Oppo');}")
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    def ouvrir_dlr():
        pg.click('.nv[data-t="stock"]'); pg.wait_for_timeout(1500)
        pg.click('.stkSet[data-stkset="me6"]'); pg.wait_for_timeout(3000)
    # 1. TCGdex pas publie
    pg.goto('http://127.0.0.1:8767/index.html'); pg.wait_for_timeout(11000)
    ouvrir_dlr()
    print('[non publié] demandes API me06 :',compte(lambda k,u:k=='api' and u.endswith('/sets/me06')),
          '| images pika :',compte(lambda k,u:k=='img' and 'pika-collect' in u),
          '| images TCGdex me06 :',compte(lambda k,u:k=='img' and 'assets.tcgdex.net' in u))
    print('  TCGdex me06 demandées :',sorted(set(u for k,u in REQ if k=='img' and 'assets.tcgdex.net' in u)))
    srcs=pg.eval_on_selector_all('img[src*="me06"],img[src*="pika"]','els=>els.slice(0,2).map(e=>e.src)')
    print('  exemples affichés :',srcs)
    # 2. retour dans l'app dans l'heure : pas de nouvelle question a TCGdex
    n0=compte(lambda k,u:k=='api' and u.endswith('/sets/me06'))
    pg.reload(); pg.wait_for_timeout(11000)
    print('[rechargement < 1 h] nouvelles demandes API me06 :',compte(lambda k,u:k=='api' and u.endswith('/sets/me06'))-n0)
    # 3. TCGdex publie ; bouton Verifier les nouvelles cartes (vrai clic)
    ETAT['pub']=True
    pg.evaluate("caches.open('pokoalashop-img2').then(c=>Promise.all([c.put('https://pika-collect.fr/img/card-images/me06/001-480.webp',new Response('x')),c.put('https://assets.tcgdex.net/fr/me/me06/001/low.webp',new Response('404')),c.put('https://assets.tcgdex.net/fr/me/me05/001/low.webp',new Response('ok'))]).then(()=>caches.open(CACHE_SYM_NOM)).then(c=>Promise.all([c.put('https://assets.tcgdex.net/univ/me/me06/symbol.webp',new Response('404')),c.put('https://assets.tcgdex.net/univ/me/me05/symbol.webp',new Response('ok'))])))".replace('CACHE_SYM_NOM',repr(SYM)))
    pg.click('#btnAcc'); pg.wait_for_selector('#a_newc'); pg.click('#a_newc'); pg.wait_for_timeout(3000)
    print('[publié, clic Vérifier] tcgok :',pg.evaluate("localStorage.getItem('pks_tcgok')"),'| toast :',pg.inner_text('#toast'))
    print('  cache après purge :',sorted(pg.evaluate("Promise.all(['pokoalashop-img2',%r].map(n=>caches.open(n).then(c=>c.keys()))).then(a=>[].concat(...a).map(r=>r.url))"%SYM)))
    REQ.clear(); ouvrir_dlr()
    print('  images TCGdex me06 :',compte(lambda k,u:k=='img' and 'assets.tcgdex.net' in u),'| images pika :',compte(lambda k,u:k=='img' and 'pika-collect' in u))
    print('  exemples affichés :',pg.eval_on_selector_all('img[src*="me06"]','els=>els.slice(0,2).map(e=>e.src)'))
    # 4. plus aucune verification une fois bascule
    REQ.clear(); pg.evaluate("localStorage.setItem('pks_tcgchk','0')"); pg.reload(); pg.wait_for_timeout(11000)
    print('[après bascule] demandes API me06 :',compte(lambda k,u:k=='api' and u.endswith('/sets/me06')))
    print('erreurs JS :',[e for e in errs if 'google is not defined' not in e])
    b.close()
srv.shutdown()

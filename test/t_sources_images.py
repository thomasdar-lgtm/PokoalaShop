"""4.86 : sources d'images demandées quand TCGdex échoue (vrais clics).
EV06 doit encore passer par pokemon.fr ; EV07-EV10 ne doivent plus le demander.
python3 test/t_sources_images.py"""
import json, re, os, threading, http.server, functools
from urllib.parse import urlparse, unquote_plus
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lots=json.load(open(ROOT+'/test/lots_2026-11-07.json',encoding='utf-8'))['lots']
stk=json.load(open(ROOT+'/test/stock_2026-11-07.json',encoding='utf-8'))
F={f['id']:f for f in stk['fichiers']}
F['lotsC']={'name':'pks_cindy.json','modifiedTime':'2026-11-07T14:05:00.000Z','data':{'v':'4.81','who':'cindy','count':len(lots),'lots':lots}}
REQ=[]
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8770),functools.partial(H,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
def drive(route):
    r=route.request; u=urlparse(r.url)
    if r.method!='GET': return route.fulfill(status=200,content_type='application/json',body='{"id":"x"}')
    m=re.search(r'/files/([^/?]+)$',u.path)
    if m and 'alt=media' in u.query:
        f=F.get(m.group(1)); return route.fulfill(status=200 if f else 404,content_type='application/json',body=json.dumps(f['data']) if f else '')
    q=re.search(r"q=([^&]*)",u.query); qq=unquote_plus(q.group(1)) if q else ''
    c=re.search(r"name contains '([^']*)'",qq); e=re.search(r"name = '([^']*)'",qq)
    out=[{'id':k,'name':f['name'],'modifiedTime':f['modifiedTime']} for k,f in F.items() if (c and c.group(1) in f['name']) or (e and e.group(1)==f['name'])]
    return route.fulfill(status=200,content_type='application/json',body=json.dumps({'files':out}))
def img(route):
    u=route.request.url; REQ.append(u)
    return route.fulfill(status=404,body='')      # toutes les sources echouent : on voit toute la chaine
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1100,'height':800},service_workers='block')
    ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
    ctx.route('**/www.googleapis.com/**',drive)
    ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
    for h in ['assets.tcgdex.net','assets.pokemon.com','images.pokemontcg.io']: ctx.route('**/%s/**'%h,img)
    ctx.add_init_script("localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');localStorage.setItem('pks_dev','mvdtytc1vf7kr7');localStorage.setItem('pks_devnom','Oppo');")
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8770/index.html'); pg.wait_for_timeout(7000)
    pg.click('.nv[data-t="stock"]'); pg.wait_for_timeout(1200)
    for sid,nom in [('sv6','EV06'),('sv7','EV07'),('sv8','EV08'),('sv9','EV09'),('sv10','EV10')]:
        REQ.clear()
        pg.click('.stkSet[data-stkset="%s"]'%sid); pg.wait_for_timeout(2500)
        print('%s : TCGdex %d | pokemon.fr %d | pokemontcg.io %d'%(nom,
            sum('assets.tcgdex.net' in u and 'symbol' not in u for u in REQ),
            sum('assets.pokemon.com' in u for u in REQ),
            sum('images.pokemontcg.io' in u and 'symbol' not in u for u in REQ)))
        pg.click('[data-stkback]'); pg.wait_for_timeout(800)
    print('erreurs JS :',[e for e in errs if 'google is not defined' not in e])
    b.close()
srv.shutdown()

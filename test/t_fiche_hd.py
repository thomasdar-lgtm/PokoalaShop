"""4.88 : (1) taille REELLE de l'image affichee dans la fiche carte (vrais
serveurs TCGdex et pokemon.fr) ; (2) Foudre Noire (zsv10pt5) : plus de carte
parasite, stock du n°80 intact. python3 test/t_fiche_hd.py"""
import json, re, os, threading, http.server, functools
from urllib.parse import urlparse, unquote_plus
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lots=json.load(open(ROOT+'/test/lots_2026-11-07.json',encoding='utf-8'))['lots']
stk=json.load(open(ROOT+'/test/stock_2026-11-07.json',encoding='utf-8'))
F={f['id']:f for f in stk['fichiers']}
F['lotsC']={'name':'pks_cindy.json','modifiedTime':'2026-11-07T14:05:00.000Z','data':{'v':'4.81','who':'cindy','count':len(lots),'lots':lots}}
ECR=[]
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8771),functools.partial(H,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
def drive(route):
    r=route.request; u=urlparse(r.url)
    if r.method!='GET': ECR.append(u.path); return route.fulfill(status=200,content_type='application/json',body='{"id":"x"}')
    m=re.search(r'/files/([^/?]+)$',u.path)
    if m and 'alt=media' in u.query:
        f=F.get(m.group(1)); return route.fulfill(status=200 if f else 404,content_type='application/json',body=json.dumps(f['data']) if f else '')
    q=re.search(r"q=([^&]*)",u.query); qq=unquote_plus(q.group(1)) if q else ''
    c=re.search(r"name contains '([^']*)'",qq); e=re.search(r"name = '([^']*)'",qq)
    out=[{'id':k,'name':f['name'],'modifiedTime':f['modifiedTime']} for k,f in F.items() if (c and c.group(1) in f['name']) or (e and e.group(1)==f['name'])]
    return route.fulfill(status=200,content_type='application/json',body=json.dumps({'files':out}))
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':412,'height':860},is_mobile=True,has_touch=True,service_workers='block')
    ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
    ctx.route('**/www.googleapis.com/**',drive)
    ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
    for h in ['assets.tcgdex.net','assets.pokemon.com']: ctx.route('**/%s/**'%h,lambda r:r.continue_())   # vrais serveurs
    ctx.add_init_script("localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');localStorage.setItem('pks_dev','mvdtytc1vf7kr7');localStorage.setItem('pks_devnom','Oppo');")
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('requestfailed',lambda r: print('   échec réseau :',r.url,r.failure) if 'high.webp' in r.url else None)
    pg.on('response',lambda r: print('   réponse',r.status,r.url) if 'high.webp' in r.url and r.status!=200 else None)
    pg.goto('http://127.0.0.1:8771/index.html'); pg.wait_for_timeout(7000)
    pg.click('.nv[data-t="stock"]'); pg.wait_for_timeout(1200)
    tot0=pg.evaluate("Object.keys(stock).reduce(function(s,k){return s+stock[k]},0)")
    for sid in ['sv1','sv6']:
        pg.click('.stkSet[data-stkset="%s"]'%sid); pg.wait_for_timeout(1500)
        pg.locator('[data-stkid]').first.click()
        pg.wait_for_function("(function(){var i=document.querySelector('#sheet .shImg');return i&&i.complete&&i.naturalWidth>0})()",timeout=20000)
        r=pg.eval_on_selector('#sheet .shImg','i=>[i.naturalWidth,i.naturalHeight,i.currentSrc]')
        print('fiche %s : image affichée %d×%d  %s'%(sid,r[0],r[1],r[2]))
        pg.click('#shBack'); pg.wait_for_timeout(500); pg.click('[data-stkback]'); pg.wait_for_timeout(800)
    # Foudre Noire
    pg.click('.stkSet[data-stkset="zsv10pt5"]'); pg.wait_for_timeout(2000)
    ids=pg.eval_on_selector_all('[data-stkid]','els=>els.map(e=>e.getAttribute("data-stkid"))')
    print('Foudre Noire : %d cartes affichées | zsv10pt5-80 affichée %d fois | zsv10pt5-60 %d fois'%(len(ids),ids.count('zsv10pt5-80'),ids.count('zsv10pt5-60')))
    print('  noms : n°60 =',pg.evaluate("cdbById['zsv10pt5-60'].n"),'| n°80 =',pg.evaluate("cdbById['zsv10pt5-80'].n"),'| Lançargot dans la liste :',pg.evaluate("stkArr.filter(function(c){return c.n==='Lançargot'}).map(function(c){return c.i}).join(',')") if pg.evaluate("typeof stkArr!=='undefined'") else '')
    print('  stock zsv10pt5-80 :',pg.evaluate("Object.keys(stock).filter(function(k){return k.indexOf('zsv10pt5-80|')===0}).map(function(k){return k+'='+stock[k]}).join(' ')"),
          '| zsv10pt5-60 :',pg.evaluate("Object.keys(stock).filter(function(k){return k.indexOf('zsv10pt5-60|')===0}).map(function(k){return k+'='+stock[k]}).join(' ')"))
    tot1=pg.evaluate("Object.keys(stock).reduce(function(s,k){return s+stock[k]},0)")
    print('total stock avant/après :',tot0,tot1,'| écritures Drive :',len(ECR))
    pg.fill('#stkq','lancargot'); pg.wait_for_timeout(800)
    print('recherche « lancargot » dans Foudre Noire :',pg.eval_on_selector_all('[data-stkid]','els=>els.map(e=>e.getAttribute("data-stkid"))'))
    print('erreurs JS :',[e for e in errs if 'google is not defined' not in e])
    b.close()
srv.shutdown()

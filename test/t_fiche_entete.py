"""4.84 : l'en-tete de la fiche carte (retour + nom + numero) reste fixe au defilement.
python3 test/t_fiche_entete.py  (vue telephone 412x915 et tablette 1100x800)"""
import json, re, os, threading, http.server, functools
from urllib.parse import urlparse, unquote_plus
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lots=json.load(open(ROOT+'/test/lots_2026-11-07.json',encoding='utf-8'))['lots']
stk=json.load(open(ROOT+'/test/stock_2026-11-07.json',encoding='utf-8'))
F={f['id']:f for f in stk['fichiers']}
F['lotsC']={'name':'pks_cindy.json','modifiedTime':'2026-11-07T14:05:00.000Z','data':{'v':'4.81','who':'cindy','count':len(lots),'lots':lots}}
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8769),functools.partial(H,directory=ROOT))
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
with sync_playwright() as p:
    b=p.chromium.launch()
    PNG=open('/home/claude/me06/pika/084.webp','rb').read() if os.path.exists('/home/claude/me06/pika/084.webp') else open(ROOT+'/icons/'+sorted(os.listdir(ROOT+'/icons'))[0],'rb').read()
    for nom,vp,mob in [('telephone',{'width':412,'height':640},True),('tablette',{'width':1100,'height':800},False)]:
        ctx=b.new_context(viewport=vp,is_mobile=mob,has_touch=mob,service_workers='block')
        ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
        ctx.route('**/www.googleapis.com/**',drive)
        ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
        for h in ['assets.tcgdex.net','pika-collect.fr','images.pokemontcg.io']: ctx.route('**/%s/**'%h,lambda r:r.fulfill(status=200,content_type='image/webp',body=PNG))
        ctx.add_init_script("localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');localStorage.setItem('pks_dev','mvdtytc1vf7kr7');localStorage.setItem('pks_devnom','Oppo');")
        pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.goto('http://127.0.0.1:8769/index.html'); pg.wait_for_timeout(7000)
        pg.click('.nv[data-t="stock"]'); pg.wait_for_timeout(1200)
        pg.click('.stkSet[data-stkset="me6"]'); pg.wait_for_timeout(1200)
        pg.locator('[data-stkid]').first.click(); pg.wait_for_timeout(1500)
        y0=pg.eval_on_selector('.shHd2','e=>e.getBoundingClientRect().top'); s0=pg.eval_on_selector('#sheet','e=>e.getBoundingClientRect().top')
        pg.screenshot(path='/tmp/entete_%s_0.png'%nom)
        # vrai geste : molette / glisser au milieu de la fiche
        bx=pg.eval_on_selector('#sheet','e=>{var r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}')
        pg.mouse.move(bx[0],min(bx[1],vp['height']-100)); 
        for i in range(8): pg.mouse.wheel(0,250); pg.wait_for_timeout(120)
        pg.wait_for_timeout(500)
        st=pg.evaluate("['#sheet','#ovl','.ovl'].map(function(q){var e=document.querySelector(q);return q+'='+(e?e.scrollTop:'-')}).join(' ')+' html='+document.scrollingElement.scrollTop")
        y1=pg.eval_on_selector('.shHd2','e=>e.getBoundingClientRect().top')
        pg.screenshot(path='/tmp/entete_%s_1.png'%nom)
        print(nom,': défilement',st,'px | en-tête avant',round(y0),'après',round(y1),'(haut de la fiche',round(s0),')',
              '| visible :',pg.is_visible('#shBack'))
        pg.click('#shBack'); pg.wait_for_timeout(500)
        print('   flèche retour après défilement → fiche fermée :',not pg.evaluate('sheetOpen'),'| erreurs JS :',[e for e in errs if 'google is not defined' not in e])
        ctx.close()
    b.close()
srv.shutdown()

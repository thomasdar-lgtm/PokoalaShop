"""4.90 : canal de vente (Vinted Thomas / Vinted Cindy / Main propre).
Vrais clics sur les vraies données (export du 07/11). python3 test/t_canal.py"""
import json, re, os, threading, http.server, functools, csv, io
from urllib.parse import urlparse, unquote_plus
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lots=json.load(open(ROOT+'/test/lots_2026-11-07.json',encoding='utf-8'))['lots']
stk=json.load(open(ROOT+'/test/stock_2026-11-07.json',encoding='utf-8'))
F={f['id']:f for f in stk['fichiers']}
F['lotsC']={'name':'pks_cindy.json','modifiedTime':'2026-11-07T14:05:00.000Z','data':{'v':'4.89','who':'cindy','count':len(lots),'lots':lots}}
ECR=[]
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8773),functools.partial(H,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
def drive(route):
    r=route.request; u=urlparse(r.url)
    if r.method!='GET':
        m=re.search(r'/files/([^/?]+)$',u.path); fid=m.group(1) if m else None
        body=r.post_data or ''
        if fid=='lotsC':
            try:
                d=json.loads(body); F['lotsC']['data']=d; ECR.append(d)
            except Exception: pass
        return route.fulfill(status=200,content_type='application/json',body=json.dumps({'id':fid or 'neuf'}))
    m=re.search(r'/files/([^/?]+)$',u.path)
    if m and 'alt=media' in u.query:
        f=F.get(m.group(1)); return route.fulfill(status=200 if f else 404,content_type='application/json',body=json.dumps(f['data']) if f else '')
    q=re.search(r"q=([^&]*)",u.query); qq=unquote_plus(q.group(1)) if q else ''
    c=re.search(r"name contains '([^']*)'",qq); e=re.search(r"name = '([^']*)'",qq)
    out=[{'id':k,'name':f['name'],'modifiedTime':f['modifiedTime']} for k,f in F.items() if (c and c.group(1) in f['name']) or (e and e.group(1)==f['name'])]
    return route.fulfill(status=200,content_type='application/json',body=json.dumps({'files':out}))
def avec_cv(d): return {l['id']:l.get('cv') for l in d['lots'] if 'cv' in l}
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1100,'height':860},accept_downloads=True,service_workers='block')
    ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
    ctx.route('**/www.googleapis.com/**',drive)
    ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
    ctx.add_init_script("if(!sessionStorage.getItem('i')){sessionStorage.setItem('i','1');localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');localStorage.setItem('pks_dev','mvdtytc1vf7kr7');localStorage.setItem('pks_devnom','Oppo');}")
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8773/index.html'); pg.wait_for_timeout(7000)
    # 1. historique : anciens lots = Vinted Thomas, sans aucune ecriture
    pg.click('.nv[data-t="histo"]'); pg.wait_for_timeout(1000)
    print('1. totaux par canal :',pg.inner_text('.cvSum').replace('\n',' '),'| Revenus en-tête :',pg.inner_text('#s4'),'| écritures Drive :',len(ECR))
    pg.screenshot(path='/tmp/canal_histo.png')
    # 2. vente simple : Main propre
    pg.click('.nv[data-t="vitrine"]'); pg.wait_for_timeout(800)
    lid=pg.locator('[data-sell]').first.get_attribute('data-sell')
    pg.locator('[data-sell]').first.click(); pg.wait_for_selector('#f_cv')
    print('2. vente simple — canal présélectionné :',pg.inner_text('#f_cv button.on'),'| libellé acheteur :',pg.inner_text('#f_achl'))
    pg.click('#f_cv [data-cvch="mp"]'); print('   après « Main propre » : libellé :',pg.inner_text('#f_achl'))
    pg.screenshot(path='/tmp/canal_vente.png')
    pg.fill('#f_pv','15'); pg.click('#k3'); pg.wait_for_timeout(4000)
    d=ECR[-1] if ECR else None
    print('   écrit sur Drive : lots avec cv =',avec_cv(d) if d else None,'(lot vendu',lid,')')
    # 3. vente suivante : canal memorise
    pg.locator('[data-sell]').first.click(); pg.wait_for_selector('#f_cv')
    print('3. vente suivante — présélection :',pg.inner_text('#f_cv button.on'))
    pg.click('#x3'); pg.wait_for_timeout(500)
    # 4. vente multiple : appui long puis 2e lot, Vinted Cindy
    sells=pg.locator('[data-sell]')
    id1=sells.nth(0).get_attribute('data-sell'); id2=sells.nth(1).get_attribute('data-sell')
    box=sells.nth(0).bounding_box(); pg.mouse.move(box['x']+10,box['y']+10); pg.mouse.down(); pg.wait_for_timeout(700); pg.mouse.up(); pg.wait_for_timeout(500)
    # a la souris, le clic qui suit l'appui long est absorbe (suppressClick) : comportement existant,
    # propre a la souris (le toucher a son propre chemin) ; on le consomme par un clic neutre
    if pg.evaluate('selCount()')==1 and pg.evaluate('suppressClick'): pg.mouse.click(5,5); pg.wait_for_timeout(200)
    pg.locator('.card[data-open="%s"] .cNm'%id2).click(); pg.wait_for_timeout(500)
    print('   lots sélectionnés :',pg.evaluate('selCount()'))
    pg.click('#selGo'); pg.wait_for_selector('#ms_cv')
    print('4. vente multiple — présélection :',pg.inner_text('#ms_cv button.on'))
    pg.click('#ms_cv [data-cvch="vc"]'); pg.click('#msk'); pg.wait_for_timeout(4000)
    cv=avec_cv(ECR[-1]); print('   écrit : ',{k:cv.get(k) for k in (id1,id2)},'| total lots avec cv :',len(cv))
    # 5. modifier un ancien lot vendu : enregistrer sans toucher, puis changer
    old=[l['id'] for l in lots if l['st']!='vitrine' and l['st'] in ('vendu','expedie')][0]
    pg.evaluate("sheetEdit(%r)"%old); pg.wait_for_selector('#f_cv')   # ouverture directe : la fiche Modifier est la meme que via l'historique
    print('5. Modifier un ancien lot — canal affiché :',pg.inner_text('#f_cv button.on'))
    n0=len(ECR); pg.click('#k4'); pg.wait_for_timeout(4000)
    print('   enregistré sans changer : cv écrit pour ce lot ?', old in avec_cv(ECR[-1]) if len(ECR)>n0 else 'pas d\'écriture')
    pg.evaluate("sheetEdit(%r)"%old); pg.wait_for_selector('#f_cv'); pg.click('#f_cv [data-cvch="vc"]'); pg.click('#k4'); pg.wait_for_timeout(4000)
    print('   changé en Vinted Cindy : cv =',avec_cv(ECR[-1]).get(old))
    # 6. filtre historique
    pg.click('.nv[data-t="histo"]'); pg.wait_for_timeout(800)
    print('6. totaux :',pg.inner_text('.cvSum').replace('\n',' '))
    pg.click('[data-cvf="vc"]'); pg.wait_for_timeout(600)
    print('   filtre Vinted Cindy :',pg.inner_text('.secH'),'| étiquettes visibles :',sorted(set(pg.eval_on_selector_all('.hList .cvTag','e=>e.map(x=>x.textContent)'))))
    pg.click('[data-cvf="mp"]'); pg.wait_for_timeout(600); print('   filtre Main propre :',pg.inner_text('.secH'))
    pg.click('[data-cvf=""]'); pg.wait_for_timeout(600); print('   Tous les canaux :',pg.inner_text('.secH'))
    # 7. fiche du lot + export
    pg.evaluate("sheetView(%r)"%lid); pg.wait_for_timeout(500); print('7. fiche du lot :',[t for t in pg.inner_text('#sheet').split('\n') if 'Canal' in t or 'Main' in t][:2]); pg.click('#rox'); pg.wait_for_timeout(400)
    pg.click('#btnAcc'); pg.wait_for_selector('#a_cs')
    with pg.expect_download() as dl: pg.click('#a_cs')
    txt=open(dl.value.path(),encoding='utf-8-sig').read()
    rows=list(csv.reader(io.StringIO(txt),delimiter=';'))
    i=rows[0].index('Canal'); import collections
    print('   export : colonne', rows[0][i],'|',collections.Counter(r[i] for r in rows[1:] if len(r)>i and r[0]))
    print('erreurs JS :',[e for e in errs if 'google is not defined' not in e])
    b.close()
srv.shutdown()

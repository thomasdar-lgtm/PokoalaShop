"""Test 4.80 « Quel appareil es-tu ? » sur les vrais exports du 07/11.
Usage : python3 test/t_identite.py <scenario>   (s25 | vide | oppo | normal | nouveau | saisie | nom | nomvide)"""
import json, re, sys, os, threading, http.server, functools
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC=sys.argv[1]
lots=json.load(open(ROOT+'/test/lots_2026-11-07.json',encoding='utf-8'))['lots']
stk=json.load(open(ROOT+'/test/stock_2026-11-07.json',encoding='utf-8'))
F={f['id']:{'name':f['name'],'modifiedTime':f['modifiedTime'],'data':f['data']} for f in stk['fichiers']}
F['lotsC']={'name':'pks_cindy.json','modifiedTime':'2026-11-07T14:05:00.000Z','data':{'v':'4.78','who':'cindy','count':len(lots),'lots':lots}}
ECR=[]
PANNE=set()   # noms de fichiers dont la lecture echoue (apres la 1re lecture)
LU={}
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8766),functools.partial(H,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
def drive(route):
    r=route.request; u=urlparse(r.url); q=parse_qs(u.query)
    if r.method!='GET':
        m=re.search(r'/files/([^/?]+)$',u.path); fid=m.group(1) if m else None
        body=r.post_data or ''
        ECR.append((r.method,F[fid]['name'] if fid in F else '(création)',body))
        if fid in F:
            try: F[fid]['data']=json.loads(body)
            except Exception: pass
        return route.fulfill(status=200,content_type='application/json',body=json.dumps({'id':fid or 'neuf'}))
    m=re.search(r'/files/([^/?]+)$',u.path)
    if m and q.get('alt')==['media']:
        fid=m.group(1)
        if fid not in F: return route.fulfill(status=404,body='')
        LU[fid]=LU.get(fid,0)+1
        if F[fid]['name'] in PANNE and LU[fid]>1: return route.fulfill(status=500,body='')
        return route.fulfill(status=200,content_type='application/json',body=json.dumps(F[fid]['data']))
    if u.path.endswith('/files') and 'q' in q:
        qq=q['q'][0]; out=[]
        c=re.search(r"name contains '([^']*)'",qq); e=re.search(r"name = '([^']*)'",qq)
        for fid,f in F.items():
            n=f['name']
            if (c and c.group(1) in n) or (e and e.group(1)==n): out.append({'id':fid,'name':n,'modifiedTime':f['modifiedTime']})
        return route.fulfill(status=200,content_type='application/json',body=json.dumps({'files':out}))
    return route.fulfill(status=200,content_type='application/json',body='{}')
INIT={'s25':{'pks_dev':'mw4pmh3rylp1ug'},'vide':{},'oppo':{'pks_dev':'mw4pmh3rylp1ug'},
      'normal':{'pks_dev':'mvdtytc1vf7kr7','pks_devnom':'Oppo'},'nouveau':{'pks_dev':'mw4pmh3rylp1ug'},'saisie':{'pks_dev':'mw4pmh3rylp1ug'},
      'nom':{'pks_dev':'mvdtytc1vf7kr7','pks_devnom':'Oppo'},'nomvide':{'pks_dev':'mvdtytc1vf7kr7'}}[SC]
js="if(!sessionStorage.getItem('init')){sessionStorage.setItem('init','1');localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');"+''.join("localStorage.setItem(%r,%r);"%kv for kv in INIT.items())+"}"
def total(pg): return pg.evaluate("Object.keys(stock).reduce(function(s,k){return s+stock[k]},0)")
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1100,'height':800},service_workers='block')
    ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
    ctx.route('**/www.googleapis.com/**',drive)
    ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
    ctx.add_init_script(js)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8766/index.html'); pg.wait_for_timeout(6000)
    print('DEV au départ',pg.evaluate('DEV'),'| total stock',total(pg))
    vis=pg.is_visible('text=Quel appareil es-tu ?')
    print('question affichée:',vis)
    if vis: print('choix:',[t.replace('\n',' · ') for t in pg.locator('[data-idch]').all_inner_texts()])
    if SC=='saisie':
        S25='pkstk_mvz6xb9bmb5lvt.json'; base=dict([f for f in F.values() if f['name']==S25][0]['data']['delta'])
        PANNE.add(S25)   # pire cas : apres le rechargement, la couche reprise ne se relit pas
        for fid,f in F.items():
            if f['name']==S25: LU[fid]=0
        pg.click('[data-idch]:has-text("S25")'); pg.wait_for_timeout(6000)
        print('après reprise (Drive en panne pour S25): DEV',pg.evaluate('DEV'),'myDelta = Drive:',pg.evaluate('myDelta')==base)
        pg.click('.nv[data-t="stock"]'); pg.wait_for_timeout(1500)
        pg.fill('#stkq' if pg.is_visible('#stkq') else '#q','Pikachu'); pg.wait_for_timeout(1500)
        pg.locator('.stkRow[data-stkid]').first.click(); pg.wait_for_timeout(800)
        cid=pg.locator('[data-stkd$="|nm|1"]').first.get_attribute('data-stkd').split('|')
        k='|'.join(cid[:3])
        pg.locator('[data-stkd$="|nm|1"]').first.click(); pg.wait_for_timeout(4500)
        w=[x for x in ECR if x[1]==S25]
        print('écritures sur la couche S25:',len(w))
        if w:
            nd=json.loads(w[-1][2])['delta']; attendu=dict(base); attendu[k]=attendu.get(k,0)+1
            if not attendu[k]: del attendu[k]
            print('carte',k,'| couche écrite = Drive + la saisie :',nd==attendu,'| entrées',len(base),'->',len(nd))

    if SC in('s25','vide'):
        avant=total(pg)
        pg.click('[data-idch]:has-text("S25")'); pg.wait_for_timeout(6000)
        print('après reprise: DEV',pg.evaluate('DEV'),'nom',pg.evaluate('devNom()'),'| total stock',total(pg),'(avant',avant,')')
        print('question encore affichée:',pg.is_visible('text=Quel appareil es-tu ?'))
        S25='pkstk_mvz6xb9bmb5lvt.json'; base=[f for f in F.values() if f['name']==S25][0]['data']['delta']
        print('couche S25 reprise en mémoire identique à Drive:',pg.evaluate('myDelta')==base)
    if SC=='oppo':
        pg.click('[data-idch]:has-text("Oppo")'); pg.wait_for_timeout(500)
        print('confirmation:',pg.inner_text('#sheet').replace('\n',' | ')[:200])
        pg.click('#x_idno'); pg.wait_for_timeout(300)
        print('retour à la liste:',pg.is_visible('text=Quel appareil es-tu ?'),'DEV',pg.evaluate('DEV'))
    if SC in('nom','nomvide'):
        pg.click('#btnAcc'); pg.wait_for_selector('#a_devz')
        print('champ de saisie visible:',pg.is_visible('#f_devnom'),'| affichage:',pg.inner_text('#a_devz').replace('\n',' | '))
        pg.wait_for_timeout(600); pg.screenshot(path='/tmp/nom_%s_1.png'%SC)
        if SC=='nom':
            pg.click('#a_devmod'); print('après Modifier: champ',pg.is_visible('#f_devnom'),pg.input_value('#f_devnom'))
            pg.click('#a_devx'); print('après Annuler: champ',pg.is_visible('#f_devnom'),'|',pg.inner_text('#a_devz'))
            pg.click('#a_devmod'); pg.fill('#f_devnom','Oppo Cindy'); pg.click('#a_devnom')
        else:
            pg.fill('#f_devnom','Oppo'); pg.click('#a_devnom')
        pg.wait_for_timeout(4000)
        print('après Enregistrer: champ',pg.is_visible('#f_devnom'),'|',pg.inner_text('#a_devz'),'| devNom',pg.evaluate('devNom()'))
        w=[json.loads(b)['nom'] for m,n,b in ECR if n=='pkstk_mvdtytc1vf7kr7.json']
        print('nom écrit dans la couche Oppo:',w)
        pg.screenshot(path='/tmp/nom_%s_2.png'%SC)
    if SC=='nouveau':
        pg.click('[data-idch="nouv"]'); pg.wait_for_timeout(300)
        pg.reload(); pg.wait_for_timeout(6000)
        print('après rechargement: question',pg.is_visible('text=Quel appareil es-tu ?'),'DEV',pg.evaluate('DEV'))
    print('écritures Drive:',[(m,n) for m,n,_ in ECR])
    print('erreurs JS:',[e for e in errs if 'google is not defined' not in e])
    pg.screenshot(path='/tmp/id_%s.png'%SC)
    b.close()
srv.shutdown()

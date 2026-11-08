"""Gestes retour (Android) dans l'onglet Stock. python3 test/t_retour.py
Chaque scénario : ouvrir, puis 'retour' répétés ; on note l'écran après chaque retour.
'SORTIE' = l'historique de l'app est épuisé (Android fermerait l'app)."""
import json, re, os, sys, threading, http.server, functools
from urllib.parse import urlparse, unquote_plus
from playwright.sync_api import sync_playwright
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lots=json.load(open(ROOT+'/test/lots_2026-11-07.json',encoding='utf-8'))['lots']
stk=json.load(open(ROOT+'/test/stock_2026-11-07.json',encoding='utf-8'))
F={f['id']:f for f in stk['fichiers']}
F['lotsC']={'name':'pks_cindy.json','modifiedTime':'2026-11-07T14:05:00.000Z','data':{'v':'4.81','who':'cindy','count':len(lots),'lots':lots}}
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8768),functools.partial(H,directory=ROOT))
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
ECRAN="""()=>{ if(location.href.indexOf('127.0.0.1')<0) return 'SORTIE';
 var s=[]; s.push('onglet='+tab); if(stkSet) s.push('extension='+stkSet); if(stkNever) s.push('jamais-fait'); if(stkInv) s.push('inventaire');
 if(sheetOpen) s.push('FICHE'); if($('lb').classList.contains('on')) s.push('ZOOM'); var q=$('q'); if(q&&q.value) s.push('recherche='+q.value);
 return s.join(' ')+'  [historique='+history.length+' etat='+JSON.stringify(history.state)+']'; }"""
def retours(pg,n):
    for i in range(n):
        pg.wait_for_timeout(PAUSE)   # l'utilisateur regarde l'ecran : plus d'activation en cours
        try: pg.go_back(timeout=1500)
        except Exception: pass
        pg.wait_for_timeout(400)
        try: e=pg.evaluate(ECRAN)
        except Exception: e='SORTIE'
        try: sans=pg.evaluate('window.__sans.length')
        except Exception: sans='-'
        print('   retour %d -> %s   | entrées ajoutées sans geste depuis le dernier retour (Chrome sauterait un écran) : %s'%(i+1,e,sans))
        if e=='SORTIE': break
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':1100,'height':800},service_workers='block')
    ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
    ctx.route('**/www.googleapis.com/**',drive)
    ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
    PNG=open(ROOT+'/icons/'+sorted(os.listdir(ROOT+'/icons'))[0],'rb').read()
    for h in ['assets.tcgdex.net','pika-collect.fr','images.pokemontcg.io','images.scrydex.com']: ctx.route('**/%s/**'%h,lambda r:r.fulfill(status=200,content_type='image/png',body=PNG))
    ctx.add_init_script("""window.__sans=[];
  /* regle de Chrome : une entree ajoutee sans activation utilisateur en cours
     (navigator.userActivation.isActive, ~5 s apres un geste) fait sauter
     l'entree courante au retour suivant */
  var _ps=history.pushState.bind(history);
  history.pushState=function(st,t){ if(navigator.userActivation && !navigator.userActivation.isActive) window.__sans.push(JSON.stringify(st)); return _ps(st,t); };""")
    ctx.add_init_script("if(!sessionStorage.getItem('i')){sessionStorage.setItem('i','1');localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');localStorage.setItem('pks_dev','mvdtytc1vf7kr7');localStorage.setItem('pks_devnom','Oppo');}")
    def neuf():
        pg=ctx.new_page(); pg.goto('http://127.0.0.1:8768/index.html'); pg.wait_for_timeout(7000)
        pg.click('.nv[data-t="stock"]'); pg.wait_for_timeout(1200); return pg
    PAUSE=6000
    SC=sys.argv[1:] or ['ext','extplus','recherche','zoom']
    if 'ext' in SC:
        print('A. Stock > extension > carte, puis retours'); pg=neuf()
        pg.click('.stkSet[data-stkset="me6"]'); pg.wait_for_timeout(1200)
        pg.locator('.stkRow[data-stkid], [data-stkid]').first.click(); pg.wait_for_timeout(800)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,5); pg.close()
    if 'extplus' in SC:
        print('B. Stock > extension > carte > « + » sur une quantité, puis retours'); pg=neuf()
        pg.click('.stkSet[data-stkset="me6"]'); pg.wait_for_timeout(1200)
        pg.locator('[data-stkid]').first.click(); pg.wait_for_timeout(800)
        pg.locator('[data-stkd$="|nm|1"]').first.click(); pg.wait_for_timeout(600)
        pg.locator('[data-stkd$="|nm|-1"]').first.click(); pg.wait_for_timeout(600)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,5); pg.close()
    if 'recherche' in SC:
        print('C. Stock > recherche « Pikachu » > carte, puis retours'); pg=neuf()
        pg.locator('#q').press_sequentially('Pikachu',delay=60); pg.wait_for_timeout(1200)
        pg.locator('[data-stkid]').first.click(); pg.wait_for_timeout(800)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,5); pg.close()
    if 'zoom' in SC:
        print('D. Stock > extension > carte > zoom image, puis retours'); pg=neuf()
        pg.click('.stkSet[data-stkset="me6"]'); pg.wait_for_timeout(1200)
        pg.locator('[data-stkid]').first.click(); pg.wait_for_timeout(800)
        pg.click('.shImg'); pg.wait_for_timeout(600)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,6); pg.close()
    if 'bouton' in SC:
        print('E. Stock > extension > carte, fermée par sa flèche, puis retours'); pg=neuf()
        pg.click('.stkSet[data-stkset="me6"]'); pg.wait_for_timeout(1200)
        pg.locator('[data-stkid]').first.click(); pg.wait_for_timeout(800)
        pg.click('#shBack'); pg.wait_for_timeout(600)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,4); pg.close()
    if 'compte' in SC:
        print('F. Vitrine > Compte, puis retours'); pg=ctx.new_page(); pg.goto('http://127.0.0.1:8768/index.html'); pg.wait_for_timeout(7000)
        pg.click('#btnAcc'); pg.wait_for_timeout(600)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,3); pg.close()
    if 'jamais' in SC:
        print('G. Stock > Jamais fait, puis retours'); pg=neuf()
        pg.click('[data-stknv]'); pg.wait_for_timeout(1500)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,4); pg.close()
    if 'rechext' in SC:
        print('H. Stock > extension > recherche dans l\'extension « ex », puis retours'); pg=neuf()
        pg.click('.stkSet[data-stkset="me6"]'); pg.wait_for_timeout(1200)
        pg.locator('#stkq').press_sequentially('ex',delay=80); pg.wait_for_timeout(800)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,4); pg.close()
    if 'croix' in SC:
        print('I. Stock > recherche « Pika », effacée par la croix, puis retours'); pg=neuf()
        pg.locator('#q').press_sequentially('Pika',delay=80); pg.wait_for_timeout(800)
        pg.click('#qClr'); pg.wait_for_timeout(600)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,3); pg.close()
    if 'clavier' in SC:
        print('J. Stock > recherche « Pi », effacée au clavier, puis retours'); pg=neuf()
        pg.locator('#q').press_sequentially('Pi',delay=80); pg.wait_for_timeout(500)
        pg.locator('#q').press('Backspace'); pg.locator('#q').press('Backspace'); pg.wait_for_timeout(600)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,3); pg.close()
    if 'onglet' in SC:
        print('K. Stock > recherche, puis onglet Vitrine, puis retours'); pg=neuf()
        pg.locator('#q').press_sequentially('Pika',delay=80); pg.wait_for_timeout(600)
        pg.click('.nv[data-t="vitrine"]'); pg.wait_for_timeout(800)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,3); pg.close()
    if 'vitrine' in SC:
        print('L. Vitrine > recherche, puis retours'); pg=ctx.new_page(); pg.goto('http://127.0.0.1:8768/index.html'); pg.wait_for_timeout(7000)
        pg.locator('#q').press_sequentially('Pika',delay=80); pg.wait_for_timeout(600)
        print('   ouvert :',pg.evaluate(ECRAN)); retours(pg,3); pg.close()
    b.close()
srv.shutdown()

"""4.89 : « Cartes du lot » — extension tapée seule (nom ou code) ⇒ cartes en
stock de cette extension, triées par numéro. Vrais clics et vraie saisie.
python3 test/t_lot_extension.py"""
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
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8772),functools.partial(H,directory=ROOT))
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
ATTENDU="""(function(sids){ var ok={}; sids.forEach(function(s){ok[s]=1});
  var n=0; for(var k in stock){ if(!(stock[k]>0)||pickLot&&lotCards(pickLot)[k]) continue; var c=k.split('|')[0],d=c.lastIndexOf('-'); if(ok[c.slice(0,d)]) n++; } return n; })"""
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':412,'height':860},is_mobile=True,has_touch=True,service_workers='block')
    ctx.route(re.compile(r'https://(?!127).*'),lambda r:r.fulfill(status=404,body=''))
    ctx.route('**/www.googleapis.com/**',drive)
    ctx.route('**/accounts.google.com/**',lambda r:r.fulfill(status=200,body=''))
    ctx.add_init_script("localStorage.setItem('pks_tk',JSON.stringify({t:'TOK',e:Date.now()+3600e3}));localStorage.setItem('pks_who','cindy');localStorage.setItem('pks_dev','mvdtytc1vf7kr7');localStorage.setItem('pks_devnom','Oppo');")
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://127.0.0.1:8772/index.html'); pg.wait_for_timeout(7000)
    pg.locator('[data-pk]').first.click(); pg.wait_for_selector('#f_pick',timeout=15000); pg.wait_for_timeout(1500)
    # extension la plus fournie en stock, pour verifier la limite de 400
    gros=pg.evaluate("""(function(){var n={};for(var k in stock){if(!(stock[k]>0))continue;var c=k.split('|')[0],d=c.lastIndexOf('-');var s=c.slice(0,d);n[s]=(n[s]||0)+1;}
      var b=Object.keys(n).sort(function(a,c){return n[c]-n[a]})[0];var st=cdb.sets.filter(function(x){return x.id===b})[0];return [b,st.name,n[b]];})()""")
    for saisie,sids in [('Règne Delta',['me6']),('dlr',['me6']),('regne delta',['me6']),('151',['sv3pt5']),('MEW',['sv3pt5']),(gros[1],[gros[0]]),('ronflex dlr',None),('arceus',['pl4'])]:
        pg.fill('#f_pick',''); pg.wait_for_timeout(400)
        pg.locator('#f_pick').press_sequentially(saisie,delay=40); pg.wait_for_timeout(1500)
        heads=pg.eval_on_selector_all('#pk_res .pkH','e=>e.map(x=>x.textContent)')
        # lignes de la section extension seulement (entre son titre et le titre suivant)
        SECT="""(function(){var out=[],on=false;document.querySelectorAll('#pk_res > *').forEach(function(x){
          if(x.classList.contains('pkH')){on=/en stock \\(/.test(x.textContent);return;} if(on&&x.classList.contains('pkR'))out.push(x.querySelector('small').textContent);});return out;})()"""
        sect=pg.evaluate(SECT)
        rows=len(sect)
        info='titres %s | lignes %d'%(heads,rows)
        if sids:
            att=pg.evaluate(ATTENDU+'(%s)'%json.dumps(sids))
            info+=' | attendu en stock %d'%att
        if saisie in ('Règne Delta','151'):
            n=[int(re.search(r'N° (\d+)',t).group(1)) for t in sect if re.search(r'N° (\d+)',t)]
            info+=' | triés par numéro : %s (%s…)'%(n==sorted(n),n[:8])
        msg=pg.eval_on_selector_all('#pk_res .pkE','e=>e.map(x=>x.textContent)')
        if msg: info+=' | message %s'%msg
        print('« %s » → %s'%(saisie,info))
    # limite : on l'abaisse a 50 pour l'eprouver (aucune extension ne depasse 400 en stock)
    pg.evaluate('PICK_MAX=50'); pg.fill('#f_pick',''); pg.locator('#f_pick').press_sequentially('151',delay=40); pg.wait_for_timeout(1500)
    print('limite abaissée à 50, « 151 » → lignes',len(pg.evaluate(SECT)),'| message',pg.eval_on_selector_all('#pk_res .pkE','e=>e.map(x=>x.textContent)'))
    pg.fill('#f_pick',''); pg.locator('#f_pick').press_sequentially('mew pikachu',delay=40); pg.wait_for_timeout(1500)
    print('affinage proposé « mew pikachu » → titres',pg.eval_on_selector_all('#pk_res .pkH','e=>e.map(x=>x.textContent)'),'| cartes',pg.eval_on_selector_all('#pk_res .pkR b','e=>e.map(x=>x.textContent).slice(0,4)'))
    pg.evaluate('PICK_MAX=400'); pg.fill('#f_pick',''); pg.locator('#f_pick').press_sequentially('151',delay=40); pg.wait_for_timeout(1500)
    # ajout d'une carte depuis le resultat extension (1re ligne de la section 151)
    ECR.clear()
    btn=pg.locator('#pk_res .pkR').first.locator('[data-pick$="|1"]')
    k=btn.get_attribute('data-pick'); btn.click(); pg.wait_for_timeout(1500)
    heads=pg.eval_on_selector_all('#pk_res .pkH','e=>e.map(x=>x.textContent)')
    print('« + » sur %s → titres %s | carte dans le lot : %s | écritures Drive : %s'%(k,heads,pg.evaluate("lotCards(pickLot)[%r]"%'|'.join(k.split('|')[:3])),ECR))
    print('écritures Drive :',len(ECR),'| erreurs JS :',[e for e in errs if 'google is not defined' not in e])
    b.close()
srv.shutdown()

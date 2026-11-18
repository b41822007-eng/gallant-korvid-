from flask import Flask, request, jsonify, session, redirect
import sqlite3, hashlib
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = "gallan-keepers-2026"
DB = "gallan.db"

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def init():
    con = db(); cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, name TEXT, phone TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS animals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, tag TEXT, type TEXT, name TEXT, age INTEGER, status TEXT DEFAULT 'Healthy', disease TEXT DEFAULT '-')")
    cur.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, animal_type TEXT, vaccine TEXT, date TEXT, repeat_days INTEGER, status TEXT DEFAULT 'Pending')")
    cur.execute("CREATE TABLE IF NOT EXISTS production (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, animal_tag TEXT, event TEXT, count INTEGER, date TEXT, note TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS finance (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT, category TEXT, amount INTEGER, date TEXT, note TEXT)")
    # User wa kujaribu
    try:
        cur.execute("INSERT INTO users (username,password,name,phone) VALUES (?,?,?,?)", ("admin", hashlib.sha256("1234".encode()).hexdigest(), "Benjamin", "0755-000000"))
    except: pass
    con.commit(); con.close()
init()
def hp(p): return hashlib.sha256(p.encode()).hexdigest()

DISEASES = {
    "kuku": [{"s":["kuhara","manyoya"],"d":"Newcastle (Mdondo)","t":"Chanjo ya Newcastle + Vitamini. Tenga kuku.","l":"Hatari Sana"},{"s":["kukohoa","macho"],"d":"Gumboro / Mafua","t":"Antibiotic + Maji safi","l":"Hatari"}],
    "mbuzi": [{"s":["kuhara","kukonda"],"d":"Minyoo","t":"Albendazole, Rudia wiki 2","l":"Wastani"},{"s":["homa","mate"],"d":"PPR","t":"Chanjo ya PPR + Daktari HARAKA","l":"Hatari Sana"}],
    "ngombe": [{"s":["homa","kuto kula"],"d":"Ndigana (ECF)","t":"Buparvaquone - Daktari HARAKA","l":"Hatari Sana"},{"s":["maziwa","uvimbe"],"d":"Mastitis","t":"Antibiotic ya kiwele + Kamua maziwa","l":"Wastani"}]
}
VACCINES = {
    "kuku":[{"v":"Newcastle (Mdondo)","days":90},{"v":"Gumboro","days":21},{"v":"Fowl Pox","days":365}],
    "mbuzi":[{"v":"PPR","days":365},{"v":"Minyoo","days":60}],
    "ngombe":[{"v":"Ndigana (ECF)","days":365},{"v":"Foot & Mouth","days":180},{"v":"Minyoo","days":90}]
}

HTML = r'''<!DOCTYPE html><html lang="sw"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GALLAN KEEPERS</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Segoe UI,Arial}body{background:#FFF8E1}
header{background:linear-gradient(135deg,#2E7D32,#FF9800);color:#fff;text-align:center;padding:28px 15px}
.container{max-width:900px;margin:15px auto;padding:0 12px}.dashboard{display:flex;gap:10px;margin-bottom:15px}
.card{flex:1;padding:16px;border-radius:14px;text-align:center;color:#fff}.green{background:#43A047}.red{background:#E53935}.blue{background:#1E88E5}
.box{background:#fff;padding:18px;border-radius:14px;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,.08)}
input,select,textarea{width:100%;padding:11px;margin-bottom:9px;border:1.5px solid #ddd;border-radius:10px}
button{width:100%;padding:12px;background:#2E7D32;color:#fff;border:none;border-radius:10px;font-weight:bold;cursor:pointer}
.lang{position:fixed;top:10px;right:10px;z-index:999;background:#fff;border-radius:30px;padding:4px;display:flex;box-shadow:0 2px 10px rgba(0,0,0,.2)}
.lang button{width:auto;padding:7px 13px;border-radius:20px}.animal{display:flex;justify-content:space-between;padding:10px;border-bottom:1px solid #eee}
.badge{padding:4px 10px;border-radius:20px;font-size:12px;font-weight:bold}.Healthy{background:#C8E6C9}.Sick{background:#FFCDD2}
.small{width:auto;padding:6px 11px;font-size:13px;margin-left:5px}.del{background:#E53935}.hidden{display:none}
</style></head><body>
<div class="lang"><button onclick="setLang('sw')" id="b-sw" style="background:#2E7D32;">🇹🇿 SW</button><button onclick="setLang('en')" id="b-en" style="background:#eee;color:#333;">🇬🇧 EN</button></div>
<header><h1 data-i18n="title">🐔🐐🐄 GALLAN KEEPERS</h1><p>Benjamin Yona Simon | Ilboru High School | <span id="uname"></span> | <a href="/logout" style="color:white;">Logout</a></p></header>
<div class="container" id="main" style="display:none;">
<div class="dashboard"><div class="card green"><h2 id="total">0</h2><p data-i18n="total">Wanyama Wote</p></div><div class="card red"><h2 id="sick">0</h2><p data-i18n="sick">Wagonjwa</p></div><div class="card blue"><h2 id="healthy">0</h2><p data-i18n="healthy">Wazima</p></div></div>

<div class="box"><h2 data-i18n="scanBtn">📷 SCAN DALILI ZA MNYAMA</h2>
<select id="s_type"><option value="kuku">🐔 Kuku</option><option value="mbuzi">🐐 Mbuzi</option><option value="ngombe">🐄 Ng'ombe</option></select>
<video id="camera" autoplay playsinline style="width:100%;border-radius:10px;background:#000;display:none;"></video><img id="preview" style="width:100%;border-radius:10px;display:none;">
<button onclick="openCam()" style="background:#FF9800;">📷 Fungua Kamera</button><button onclick="takePhoto()" style="background:#333;margin-top:8px;">📸 Piga Picha</button>
<input type="file" accept="image/*" onchange="previewImg(event)">
<textarea id="s_symptoms" placeholder="Andika dalili: kuhara, kukonda, kuto kula..."></textarea>
<button onclick="doScan()" style="background:#E53935;">🔍 SCAN SASA</button><div id="scanRes" class="hidden" style="background:#FFF3E0;padding:12px;border-radius:10px;margin-top:10px;"></div></div>

<div class="box"><h2 data-i18n="add">➕ Sajili Mnyama Mpya</h2>
<input id="tag" placeholder="Tag: KUKU-001"><select id="type"><option value="kuku">🐔 Kuku</option><option value="mbuzi">🐐 Mbuzi</option><option value="ngombe">🐄 Ng'ombe</option></select>
<input id="name" placeholder="Jina la Mnyama"><input id="age" type="number" placeholder="Umri (Miezi)">
<button onclick="addAnimal()" data-i18n="btnReg">Sajili Mnyama</button><div id="list" style="margin-top:10px;"></div></div>

<div class="box" style="border:2px solid #FF9800;"><h2 data-i18n="vac">💉 CHANJO REMINDER</h2>
<div id="vacAlert" style="display:none;background:#FFEBEE;color:#C62828;padding:10px;border-radius:10px;font-weight:bold;margin-bottom:10px;"></div>
<select id="rem_type" onchange="loadVac()"><option value="kuku">🐔 Kuku</option><option value="mbuzi">🐐 Mbuzi</option><option value="ngombe">🐄 Ng'ombe</option></select>
<select id="rem_vaccine"></select><input id="rem_date" type="date">
<button onclick="addRem()" style="background:#FF9800;" data-i18n="btnVac">⏰ WEKA KIKUMBUSHO</button><div id="remList" style="margin-top:10px;"></div></div>

<div class="box" style="border:2px solid #4CAF50;"><h2 data-i18n="prod">🥚🐣 KUTAGA & KUZAA</h2>
<div class="dashboard"><div class="card" style="background:#FF9800;"><h2 id="mayaiT">0</h2><p>Mayai</p></div><div class="card" style="background:#E91E63;"><h2 id="kuzaaT">0</h2><p>Waliozaliwa</p></div><div class="card" style="background:#00BCD4;"><h2 id="maziwaT">0</h2><p>Lita Maziwa</p></div></div>
<select id="prod_type"><option value="kuku">🐔 Kuku</option><option value="mbuzi">🐐 Mbuzi</option><option value="ngombe">🐄 Ng'ombe</option></select>
<select id="prod_event"><option value="mayai">🥚 Mayai</option><option value="kuzaa">🐣 Kuzaa</option><option value="maziwa">🥛 Maziwa (Lita)</option></select>
<input id="prod_tag" placeholder="Tag ya Mnyama"><input id="prod_count" type="number" placeholder="Idadi (mf: 45)"><input id="prod_date" type="date">
<button onclick="addProd()" style="background:#4CAF50;" data-i18n="btnProd">➕ REKODI UZALISHAJI</button><div id="prodList" style="margin-top:10px;"></div></div>

<div class="box" style="border:2px solid #1E88E5;"><h2 data-i18n="biz">💰 BIASHARA - Mapato na Matumizi</h2>
<div class="dashboard"><div class="card green"><h2 id="mapato">0</h2><p>Mapato (Tsh)</p></div><div class="card red"><h2 id="matumizi">0</h2><p>Matumizi (Tsh)</p></div><div class="card" style="background:#673AB7;"><h2 id="faida">0</h2><p>Faida</p></div></div>
<canvas id="chart" width="400" height="150" style="width:100%;background:#f9f9f9;border-radius:10px;"></canvas><p id="advice" style="background:#E3F2FD;padding:10px;border-radius:10px;margin-top:10px;font-weight:bold;"></p>
<select id="fin_kind"><option value="mapato">💰 MAPATO</option><option value="matumizi">💸 MATUMIZI</option></select>
<select id="fin_cat"><option>Mayai</option><option>Maziwa</option><option>Kuku</option><option>Mbuzi</option><option>Ngombe</option><option>Chakula</option><option>Dawa</option><option>Banda</option></select>
<input id="fin_amount" type="number" placeholder="Kiasi Tsh"><input id="fin_date" type="date"><input id="fin_note" placeholder="Maelezo">
<button onclick="addFin()" style="background:#1E88E5;" data-i18n="btnFin">💾 HIFADHI MUAMALA</button><div id="finList" style="margin-top:10px;"></div></div>
</div>

<div class="container" id="loginBox">
<div class="box" style="max-width:420px;margin:40px auto;text-align:center;"><h2>🔐 Ingia / Jisajili</h2>
<input id="l_user" placeholder="Username"><input id="l_pass" type="password" placeholder="Password">
<button onclick="doLogin()">INGIA</button><p style="margin:12px 0;">Au Jisajili Mpya:</p>
<input id="r_name" placeholder="Jina Kamili"><input id="r_user" placeholder="Username Mpya"><input id="r_pass" type="password" placeholder="Password Mpya">
<button onclick="doReg()" style="background:#FF9800;">JISAJILI BURE</button><p id="msg" style="color:red;margin-top:10px;"></p><p style="font-size:13px;color:#666;margin-top:10px;">Kujaribu: Username: <b>admin</b> / Password: <b>1234</b></p></div></div>

<script>
const TR={sw:{title:"🐔🐐🐄 GALLAN KEEPERS",total:"Wanyama Wote",sick:"Wagonjwa",healthy:"Wazima",scanBtn:"📷 SCAN DALILI ZA MNYAMA",add:"➕ Sajili Mnyama Mpya",btnReg:"Sajili Mnyama",vac:"💉 CHANJO REMINDER",btnVac:"⏰ WEKA KIKUMBUSHO",prod:"🥚🐣 KUTAGA & KUZAA",btnProd:"➕ REKODI UZALISHAJI",biz:"💰 BIASHARA - Mapato na Matumizi",btnFin:"💾 HIFADHI MUAMALA"},en:{title:"🐔🐐🐄 GALLAN KEEPERS",total:"Total Animals",sick:"Sick",healthy:"Healthy",scanBtn:"📷 SCAN ANIMAL SYMPTOMS",add:"➕ Register New Animal",btnReg:"Register Animal",vac:"💉 VACCINE REMINDER",btnVac:"⏰ SET REMINDER",prod:"🥚🐣 LAYING & BIRTH",btnProd:"➕ RECORD PRODUCTION",biz:"💰 BUSINESS - Income & Expenses",btnFin:"💾 SAVE TRANSACTION"}};
function setLang(l){localStorage.setItem('gl',l);let t=TR[l];document.querySelectorAll('[data-i18n]').forEach(e=>{if(t[e.getAttribute('data-i18n')])e.innerText=t[e.getAttribute('data-i18n')]});document.getElementById('b-sw').style.background=l=='sw'?'#2E7D32':'#eee';document.getElementById('b-sw').style.color=l=='sw'?'white':'#333';document.getElementById('b-en').style.background=l=='en'?'#2E7D32':'#eee';document.getElementById('b-en').style.color=l=='en'?'white':'#333';}
setLang(localStorage.getItem('gl')||'sw');
let stream=null;
async function openCam(){try{stream=await navigator.mediaDevices.getUserMedia({video:true});let v=document.getElementById('camera');v.style.display='block';v.srcObject=stream;}catch(e){alert("Kamera haikupatikana, tumia Upload");}}
function takePhoto(){let v=document.getElementById('camera'),c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);let p=document.getElementById('preview');p.src=c.toDataURL();p.style.display='block';if(stream)stream.getTracks().forEach(t=>t.stop());alert("Picha imepigwa! Sasa andika dalili na SCAN.");}
function previewImg(e){let r=new FileReader();r.onload=()=>{let p=document.getElementById('preview');p.src=r.result;p.style.display='block';};r.readAsDataURL(e.target.files[0]);}
async function doScan(){let res=await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:s_type.value,symptoms:s_symptoms.value})});let d=await res.json();let b=document.getElementById('scanRes');b.classList.remove('hidden');b.innerHTML=`<b>🩺 ${d.disease}</b><br>Uhakika: ${d.confidence}<br>Dawa: ${d.treatment}`;}
async function doLogin(){let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:l_user.value,password:l_pass.value})});let d=await r.json();if(d.success){checkAuth();}else msg.innerText=d.error;}
async function doReg(){let r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:r_name.value,username:r_user.value,password:r_pass.value})});let d=await r.json();if(d.success){alert("Umefanikiwa! Sasa Ingia");}else msg.innerText=d.error;}
async function checkAuth(){let r=await fetch('/api/me');let d=await r.json();if(d.logged){document.getElementById('main').style.display='block';document.getElementById('loginBox').style.display='none';document.getElementById('uname').innerText=d.name;loadAll();}else{document.getElementById('main').style.display='none';document.getElementById('loginBox').style.display='block';}}
async function loadAll(){loadAnimals();loadVac();loadRem();loadProd();loadBiz();}
async function loadAnimals(){let r=await fetch('/api/animals');let data=await r.json();total.innerText=data.length;sick.innerText=data.filter(a=>a.status=='Sick').length;healthy.innerText=data.filter(a=>a.status=='Healthy').length;list.innerHTML=data.map(a=>`<div class="animal"><div><b>${a.name}</b> (${a.type}) - ${a.tag}<br><small>${a.disease}</small></div><div><button class="small" onclick="heal(${a.id})">✅ Pona</button><button class="small del" onclick="delA(${a.id})">🗑️</button></div></div>`).join('')||"Hakuna mnyama";}
async function addAnimal(){await fetch('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tag:tag.value,type:type.value,name:name.value,age:age.value})});alert("Amesajiliwa!");loadAnimals();}
async function heal(id){await fetch(`/api/heal/${id}`,{method:'POST'});loadAnimals();}
async function delA(id){await fetch(`/api/delete/${id}`,{method:'DELETE'});loadAnimals();}
async function loadVac(){let r=await fetch(`/api/vaccines/${rem_type.value}`);let d=await r.json();rem_vaccine.innerHTML=d.map(v=>`<option value="${v.v}" data-days="${v.days}">${v.v}</option>`).join('');}
async function addRem(){let sel=rem_vaccine;let days=sel.options[sel.selectedIndex]?.getAttribute('data-days')||90;await fetch('/api/reminder/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({animal_type:rem_type.value,vaccine:sel.value,date:rem_date.value,repeat_days:parseInt(days)})});alert("Kikumbusho kimewekwa!");loadRem();}
async function loadRem(){let r=await fetch('/api/reminders');let data=await r.json();let urg=data.filter(x=>x.status=='Pending'&&x.days_left<=3).length;let ab=document.getElementById('vacAlert');if(urg>0){ab.style.display='block';ab.innerText=`⚠️ Una chanjo ${urg} zinazokaribia!`;}else ab.style.display='none';remList.innerHTML=data.filter(x=>x.status=='Pending').map(x=>`<div style="padding:10px;background:#FFF3E0;border-radius:10px;margin-bottom:6px;display:flex;justify-content:space-between;"><span><b>${x.vaccine}</b> - ${x.date} (${x.days_left} siku)</span><button class="small" onclick="doneRem(${x.id})">✅ Nimechanja</button></div>`).join('')||"Hakuna kikumbusho";}
async function doneRem(id){await fetch(`/api/reminder/done/${id}`,{method:'POST'});loadRem();}
async function addProd(){await fetch('/api/production/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:prod_type.value,tag:prod_tag.value,event:prod_event.value,count:parseInt(prod_count.value)||0,date:prod_date.value||new Date().toISOString().slice(0,10),note:''})});loadProd();loadBiz();}
async function loadProd(){let r=await fetch('/api/production');let d=await r.json();prodList.innerHTML=d.slice(0,8).map(p=>`<div style="padding:8px;border-bottom:1px solid #eee;">${p.date} - ${p.event} (${p.type}) - <b>${p.count}</b></div>`).join('')||"";}
async function addFin(){await fetch('/api/finance/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:fin_kind.value,category:fin_cat.value,amount:parseInt(fin_amount.value)||0,date:fin_date.value||new Date().toISOString().slice(0,10),note:fin_note.value})});loadBiz();}
async function loadBiz(){let r=await fetch('/api/finance/summary');let d=await r.json();mapato.innerText=d.mapato.toLocaleString();matumizi.innerText=d.matumizi.toLocaleString();faida.innerText=d.faida.toLocaleString();mayaiT.innerText=d.mayai_total;kuzaaT.innerText=d.kuzaa_total;maziwaT.innerText=d.maziwa_total;advice.innerText=d.faida>0?`✅ Faida Tsh ${d.faida.toLocaleString()}. Ongeza kuku!`:d.faida<0?`⚠️ Hasara Tsh ${Math.abs(d.faida).toLocaleString()}. Punguza matumizi.`:"ℹ️ Ingiza mauzo ya leo.";let cv=document.getElementById('chart'),ctx=cv.getContext('2d');ctx.clearRect(0,0,400,150);let mx=Math.max(d.mapato,d.matumizi,1);ctx.fillStyle="#43A047";ctx.fillRect(50,140-(d.mapato/mx*110),80,(d.mapato/mx*110));ctx.fillStyle="#E53935";ctx.fillRect(180,140-(d.matumizi/mx*110),80,(d.matumizi/mx*110));ctx.fillStyle="#673AB7";ctx.fillRect(310,140-(Math.abs(d.faida)/mx*110),80,(Math.abs(d.faida)/mx*110));ctx.fillStyle="#333";ctx.fillText("Mapato",60,148);ctx.fillText("Matumizi",185,148);ctx.fillText("Faida",320,148);let rf=await fetch('/api/finance/list');let fd=await rf.json();finList.innerHTML=fd.slice(0,8).map(f=>`<div style="padding:8px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;"><span>${f.date} - ${f.category}</span><b style="color:${f.kind=='mapato'?'green':'red'}">${f.kind=='mapato'?'+':'-'} ${f.amount.toLocaleString()}</b></div>`).join('');}
checkAuth();
</script></body></html>'''

@app.route("/")
def home(): return HTML
@app.route("/logout")
def logout(): session.clear(); return redirect("/")
@app.route("/api/me")
def me(): return jsonify({"logged": 'user_id' in session, "name": session.get('name','')})
@app.route("/login", methods=["POST"])
def login():
    d=request.json; con=db(); cur=con.cursor(); cur.execute("SELECT * FROM users WHERE username=? AND password=?", (d['username'], hp(d['password']))); u=cur.fetchone(); con.close()
    if u: session['user_id']=u['id']; session['name']=u['name']; return jsonify({"success":True})
    return jsonify({"success":False,"error":"Username au Password sio sahihi"})
@app.route("/register", methods=["POST"])
def register():
    d=request.json; con=db(); cur=con.cursor()
    try: cur.execute("INSERT INTO users (username,password,name,phone) VALUES (?,?,?,?)", (d['username'], hp(d['password']), d.get('name',''), '')); con.commit(); return jsonify({"success":True})
    except: return jsonify({"success":False,"error":"Username imetumika"})
    finally: con.close()
@app.route("/api/animals")
def animals():
    if 'user_id' not in session: return jsonify([])
    con=db(); cur=con.cursor(); cur.execute("SELECT * FROM animals WHERE user_id=? ORDER BY id DESC",(session['user_id'],)); rows=[dict(r) for r in cur.fetchall()]; con.close(); return jsonify(rows)
@app.route("/api/add", methods=["POST"])
def add():
    d=request.json; con=db(); cur=con.cursor(); cur.execute("INSERT INTO animals (user_id,tag,type,name,age) VALUES (?,?,?,?,?)",(session['user_id'],d['tag'],d['type'],d['name'],d.get('age',0))); con.commit(); con.close(); return jsonify({"success":True})
@app.route("/api/heal/<int:aid>", methods=["POST"])
def heal(aid): con=db(); cur=con.cursor(); cur.execute("UPDATE animals SET status='Healthy', disease='-' WHERE id=?",(aid,)); con.commit(); con.close(); return jsonify({"success":True})

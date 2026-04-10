from flask import Flask, render_template_string, request, redirect, session
from database import get_metrics, get_latest_records
import sqlite3
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = "secret123"
socketio = SocketIO(app, cors_allowed_origins="*")

conn = sqlite3.connect("metrics.db", check_same_thread=False)
cursor = conn.cursor()

users = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"}
}

LOGIN_HTML = """
<html>
<body style="display:flex;justify-content:center;align-items:center;height:100vh;">
<form method="POST">
<h2>Login</h2>
<input name="username"><br><br>
<input name="password" type="password"><br><br>
<button type="submit">Login</button>
</form>
</body>
</html>
"""

MAIN_HTML = """
<html>
<head>
<title>Monitoring Dashboard</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/echarts/dist/echarts.min.js"></script>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>

<style>
body{background:#f4f4f4;font-family:'Segoe UI';}
.header{background:black;color:white;padding:20px;border-radius:12px;text-align:center;position:relative;}
.card-box{background:white;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.1);}
.metric{font-size:26px;font-weight:bold;}
.table-box{background:white;padding:20px;border-radius:12px;box-shadow:0 4px 15px rgba(0,0,0,0.1);margin-top:20px;}
.table thead{background:black;color:white;}
.table tbody tr:hover{background:#eee;}
.btn-menu{background:black;color:white;border:none;width:35px;height:35px;border-radius:8px;}

.logout-btn{
    position:absolute;
    top:15px;
    right:15px;
    background:#1f2937;
    color:white;
    padding:6px 14px;
    border-radius:6px;
    text-decoration:none;
    font-size:14px;
    transition:0.2s;
}

.logout-btn:hover{
    background:#111827;
}
</style>

</head>

<body>

<div class="container mt-4">

<div class="header">
<h2>Distributed Monitoring</h2>
<a href="/logout" class="logout-btn">Logout</a>
</div>

<div id="alertBox"></div>

<div class="row text-center mt-3">
<div class="col-md-4"><div class="card-box">Avg CPU<div id="avgCpu" class="metric">0%</div></div></div>
<div class="col-md-4"><div class="card-box">Avg Memory<div id="avgMem" class="metric">0%</div></div></div>
<div class="col-md-4"><div class="card-box">Avg Disk<div id="avgDisk" class="metric">0%</div></div></div>
</div>

<div id="chart" style="height:350px;margin-top:20px;"></div>

<div class="table-box">
<table class="table text-center">
<thead>
<tr>
<th>Node</th><th>IP</th><th>CPU</th><th>Memory</th><th>Disk</th><th></th>
</tr>
</thead>
<tbody id="table"></tbody>
</table>
</div>

</div>

<script>

let chart = echarts.init(document.getElementById("chart"));
const socket = io();

socket.on("update", function(d){

let t="",cpu=0,mem=0,disk=0;
let alerts=[];

d.nodes.forEach(n=>{
cpu+=n.cpu;
mem+=n.memory;
disk+=n.disk;

let cpuStyle="",memStyle="",diskStyle="";

if(n.cpu >= 90){
    cpuStyle="style='color:#dc2626;font-weight:bold'";
    alerts.push({text:`${n.node} CPU CRITICAL`,color:"#dc2626"});
}
else if(n.cpu >= 70){
    cpuStyle="style='color:#ea580c;font-weight:bold'";
    alerts.push({text:`${n.node} CPU WARNING`,color:"#ea580c"});
}

if(n.memory >= 90){
    memStyle="style='color:#dc2626;font-weight:bold'";
    alerts.push({text:`${n.node} MEMORY CRITICAL`,color:"#dc2626"});
}
else if(n.memory >= 75){
    memStyle="style='color:#ea580c;font-weight:bold'";
    alerts.push({text:`${n.node} MEMORY WARNING`,color:"#ea580c"});
}

if(n.disk >= 95){
    diskStyle="style='color:#dc2626;font-weight:bold'";
    alerts.push({text:`${n.node} DISK CRITICAL`,color:"#dc2626"});
}
else if(n.disk >= 80){
    diskStyle="style='color:#ea580c;font-weight:bold'";
    alerts.push({text:`${n.node} DISK WARNING`,color:"#ea580c"});
}

t+=`<tr>
<td><strong>${n.node}</strong></td>
<td>${n.ip}</td>
<td ${cpuStyle}>${n.cpu}%</td>
<td ${memStyle}>${n.memory}%</td>
<td ${diskStyle}>${n.disk}%</td>
<td><button class="btn-menu" onclick="openNode('${n.node}')">⋮</button></td>
</tr>`;
});

table.innerHTML=t;

avgCpu.innerText=(cpu/d.nodes.length).toFixed(1)+"%";
avgMem.innerText=(mem/d.nodes.length).toFixed(1)+"%";
avgDisk.innerText=(disk/d.nodes.length).toFixed(1)+"%";

if(alerts.length){
    alertBox.innerHTML = alerts.map(a => `
        <div style="background:${a.color};color:white;padding:8px 16px;margin:6px auto;border-radius:999px;width:fit-content;">
            ⚠ ${a.text}
        </div>
    `).join("");
}else{
    alertBox.innerHTML="";
}

chart.setOption({
color:["#000","#444","#888"],
tooltip:{trigger:"axis"},
legend:{data:["CPU","Memory","Disk"]},
dataZoom:[{type:"inside"}],
xAxis:{type:"category",data:d.time},
yAxis:{type:"value",max:100},
series:[
{name:"CPU",type:"line",smooth:true,data:d.cpu_history},
{name:"Memory",type:"line",smooth:true,data:d.memory_history},
{name:"Disk",type:"line",smooth:true,data:d.disk_history}
]
});
});

function openNode(node){
window.location.href="/node_page/"+node;
}

</script>

</body>
</html>
"""

NODE_HTML = """
<html>
<head>
<title>Node</title>

<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/echarts/dist/echarts.min.js"></script>
<script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>

<style>
body{background:#f4f4f4;}
.header{background:black;color:white;padding:15px;border-radius:10px;text-align:center;}
.card{background:white;padding:15px;margin:10px;border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,0.1);}
.metric{font-size:22px;font-weight:bold;}
.table thead{background:black;color:white;}
</style>
</head>

<body>

<div class="container mt-4">

<div class="header"><h3>Node: {{node}}</h3></div>
<div id="nodeAlertBox"></div>

<div class="row text-center">
<div class="col-md-4"><div class="card">Avg CPU<div id="avgCPU" class="metric"></div></div></div>
<div class="col-md-4"><div class="card">Avg Memory<div id="memVal" class="metric"></div></div></div>
<div class="col-md-4"><div class="card">Avg Disk<div id="diskVal" class="metric"></div></div></div>
</div>

<div id="chart" style="height:350px;"></div>

<table class="table mt-4 text-center">
<thead><tr><th>#</th><th>CPU</th><th>Memory</th><th>Disk</th></tr></thead>
<tbody id="tableBody"></tbody>
</table>

</div>

<script>

let chart = echarts.init(document.getElementById("chart"));
const socket = io();

socket.on("node_update", function(d){

if(d.node !== "{{node}}") return;

avgCPU.innerText=d.avg_cpu+"%";
memVal.innerText=d.avg_mem+"%";
diskVal.innerText=d.disk_latest+"%";

chart.setOption({
color:["#000","#444","#888"],
tooltip:{trigger:"axis"},
legend:{data:["CPU","Memory","Disk"]},
xAxis:{type:"category",data:d.time},
yAxis:{type:"value",max:100},
series:[
{name:"CPU",type:"line",smooth:true,data:d.cpu},
{name:"Memory",type:"line",smooth:true,data:d.memory},
{name:"Disk",type:"line",smooth:true,data:d.disk}
]
});

let rows="";
for(let i=0;i<d.cpu.length;i++){
rows+=`<tr>
<td>${i+1}</td>
<td>${d.cpu[i]}</td>
<td>${d.memory[i]}</td>
<td>${d.disk[i]}</td>
</tr>`;
}
tableBody.innerHTML=rows;

});

</script>

</body>
</html>
"""

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        if u in users and users[u]["password"] == p:
            session["user"] = u
            session["role"] = users[u]["role"]
            return redirect("/")
    return LOGIN_HTML

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template_string(MAIN_HTML)

@app.route("/node_page/<node>")
def node_page(node):
    if "user" not in session:
        return redirect("/login")
    return render_template_string(NODE_HTML, node=node)

def push_updates():
    while True:
        nodes = get_metrics()
        h = get_latest_records()

        socketio.emit("update", {
            "nodes": nodes,
            "cpu_history":[r[0] for r in h][::-1],
            "memory_history":[r[1] for r in h][::-1],
            "disk_history":[r[2] for r in h][::-1],
            "time":list(range(len(h)))
        })

        for n in nodes:
            cursor.execute("""
            SELECT cpu,memory,disk,timestamp FROM metrics
            WHERE node=? ORDER BY timestamp DESC LIMIT 10
            """,(n["node"],))

            rows = cursor.fetchall()

            if not rows:
                continue

            socketio.emit("node_update", {
                "node": n["node"],
                "cpu":[r[0] for r in rows[::-1]],
                "memory":[r[1] for r in rows[::-1]],
                "disk":[r[2] for r in rows[::-1]],
                "time":list(range(len(rows))),
                "avg_cpu":round(sum(r[0] for r in rows)/len(rows),1),
                "avg_mem":round(sum(r[1] for r in rows)/len(rows),1),
                "disk_latest":rows[0][2]
            })

        socketio.sleep(3)

if __name__ == "__main__":
    socketio.start_background_task(push_updates)
    socketio.run(app, port=5000)
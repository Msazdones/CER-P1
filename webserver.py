from flask import Flask, render_template, redirect, request, url_for, session
import redis
from redis.commands.json.path import Path
import hashlib
import netifaces as ni
import os
import json

server_ip = ni.ifaddresses('enp0s3')[ni.AF_INET][0]['addr']
server_port = 5000

app = Flask(__name__)
app.secret_key = "ayush"

db_users = redis.Redis(host="localhost", port=6379, db=1)
db_measures = redis.Redis(host="localhost", port=6379, db=0)

@app.route('/')  
def home(): 
    cnt = db_measures.json().get("Counter", Path.root_path())
    last_measure = db_measures.json().get("Measure_"+str(cnt["cnt"]), Path.root_path())
    return render_template("homepage.html", measure=last_measure["EUR/USD_value"])

@app.route('/register')
def register():
    if "username" in session:
        return redirect("http://"+server_ip+":"+str(server_port)+"/profile", code=302)
    else:
        return render_template("register.html")

@app.route('/success_reg', methods=['POST'])
def success_reg():
    if (db_users.json().get(request.form["username"], Path.root_path())):
        return render_template("register.html",  script_alert="<tr><td style='color:red'>El usuario ya existe</td><td>")
    else:
        passwd_hashed = hashlib.sha256(bytearray(request.form["pass"], "utf8")).hexdigest()
        print(passwd_hashed)
        db_users.json().set(request.form["username"], Path.root_path(), {"email" : request.form["email"], "password" : passwd_hashed, "measures_local" : 0, "measures_online" : 0})
        return redirect("http://"+server_ip+":"+str(server_port)+"/", code=302)

@app.route('/login')
def login():
    if "username" in session:
        return redirect("http://"+server_ip+":"+str(server_port)+"/profile", code=302)
    else:
        return render_template("login.html")

@app.route('/success_log', methods=['POST'])
def success_log():
    user = db_users.json().get(request.form["username"], Path.root_path())
    if(user):
        passwd_hashed = hashlib.sha256(bytearray(request.form["pass"], "utf8")).hexdigest()
        if (user["password"] == passwd_hashed):
            session["username"] = request.form["username"]
            return redirect("http://"+server_ip+":"+str(server_port)+"/profile", code=302)
        else:
            return render_template("login.html",  script_alert="<tr><td style='color:red'>Credenciales incorrectas</td><td>")
    else:
        return render_template("login.html",  script_alert="<tr><td style='color:red'>Credenciales incorrectas</td><td>")

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect("http://"+server_ip+":"+str(server_port)+"/", code=302)

@app.route('/profile')
def profile():
    if "username" in session:
        json_file = db_users.json().get(session["username"], Path.root_path())
        return render_template("profile.html", script_alert=session["username"],
            num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
            num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))
    else:
        return render_template("login.html")

@app.route('/av_local', methods=['POST'])
def av_local():
    cnt = db_measures.json().get("Counter", Path.root_path())
    values = []
    for i in range(0, cnt["cnt"]+1):
        measure = db_measures.json().get("Measure_"+str(i), Path.root_path())
        measure = float(measure["EUR/USD_value"].split(",")[0] + "." + measure["EUR/USD_value"].split(",")[1])
        values.append(measure)
    average = get_average(values) 

    json_file = db_users.json().get(session["username"], Path.root_path())
    json_file["measures_local"] = json_file["measures_local"] +1
    db_users.json().set(session["username"], Path.root_path(), json_file)
    return render_template("profile.html", av_local_value="Valor medio de las medidas de la base de datos local: " + str(average),
        num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
        num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))

@app.route('/av_remote', methods=['POST'])
def av_remote():
    os.system('curl "https://api.thingspeak.com/channels/1909196/fields/1.json?result=2" -o /home/xubuntu/uni/computacion/p1/code/env/app-code/page_data/jsondata.json')
    f = open("/home/xubuntu/uni/computacion/p1/code/env/app-code/page_data/jsondata.json", "r")
    f = str(f.read())
    jsonobj = json.loads(f)
    values = []
    for i in jsonobj["feeds"]:
        values.append(float(i["field1"]))
    average = get_average(values) 

    json_file = db_users.json().get(session["username"], Path.root_path())
    json_file["measures_online"] = json_file["measures_online"] +1
    db_users.json().set(session["username"], Path.root_path(), json_file)
    return render_template("profile.html", av_local_value="Valor medio de las medidas de la base de datos remota: " + str('%.4f'%(average)),
        num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
        num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))

@app.route('/external_graphs', methods=['POST'])
def external_graphs():
    if "username" in session:
        return render_template("graph.html")
    else:
        return render_template("login.html")   

def get_average(values):
    result = 0
    for i in values:
        print (values)
        result = result + i
    print(len(values))
    result = result / len(values)
    return result

if __name__ == "__main__":
    app.run(host=server_ip, port=server_port, debug=True)
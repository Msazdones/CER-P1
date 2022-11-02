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
    return render_template("profile.html", script_alert=session["username"], av_local_value="Valor medio de las medidas de la base de datos local: " + str(average),
        num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
        num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))

@app.route('/av_remote', methods=['POST'])
def av_remote():
    os.system('curl "https://api.thingspeak.com/channels/1909196/fields/1.json?result=2" -o /home/cer/computacion/p1/code/env/app-code/page_data/jsondata.json')
    f = open("/home/cer/computacion/p1/code/env/app-code/page_data/jsondata.json", "r")
    f = str(f.read())
    jsonobj = json.loads(f)
    values = []
    for i in jsonobj["feeds"]:
        values.append(float(i["field1"]))
    average = get_average(values) 

    json_file = db_users.json().get(session["username"], Path.root_path())
    json_file["measures_online"] = json_file["measures_online"] +1
    db_users.json().set(session["username"], Path.root_path(), json_file)
    return render_template("profile.html", script_alert=session["username"], av_local_value="Valor medio de las medidas de la base de datos remota: " + str('%.4f'%(average)),
        num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
        num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))

@app.route('/external_graphs', methods=['POST'])
def external_graphs():
    if "username" in session:
        return render_template("graph.html")
    else:
        return render_template("login.html")   

@app.route('/umbral_1', methods=['POST'])
def umbral_1():
    if "username" in session:
        cnt = db_measures.json().get("Counter", Path.root_path())
        values = []
        string=""
        for i in range(0, cnt["cnt"]+1):
            measure = db_measures.json().get("Measure_"+str(cnt["cnt"]-i), Path.root_path())
            measure = float(measure["EUR/USD_value"].split(",")[0] + "." + measure["EUR/USD_value"].split(",")[1])
            
            if ((measure > float(request.form["value_umbral1"])) and (len(values) < 5)):
                values.append(measure)
                string = string + str(measure) + ", "
        return render_template("profile.html", script_alert=session["username"], values_umbral_1= "Ultimos valores: " + string[0:len(string)-1])
    else:
        return render_template("login.html")

@app.route('/umbral_2', methods=['POST'])
def umbral_2():
    if "username" in session:  
        session["cnt_umbral2"] = db_measures.json().get("Counter", Path.root_path())["cnt"]
        session["umbral2"] = request.form["value_umbral2"]
        session["max_umbral_cnt"] = 5
        session["umbral2_vals"] = ""
        json_file = db_users.json().get(session["username"], Path.root_path())  
        return render_template("profile.html", script_alert=session["username"], 
            umbral2='<script>$(document).ready(function(){ var ajaxDelay = 10000;setInterval(function(){var jqxhr = $.get( "umbral_2_val", function(data) {if(data=="fin"){window.location.href = "/umbral2_list";}else{document.getElementById("umbral_2_value").innerHTML = document.getElementById("umbral_2_value").innerHTML + data;}});}, ajaxDelay);});</script>',
            num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
            num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))
    else:
        return render_template("login.html")

cnt_global = 0
@app.route('/umbral_2_val')
def umbral_2_val():
    if "username" in session:
        print(session["max_umbral_cnt"])
        if (session["max_umbral_cnt"] > 0):
            cnt = db_measures.json().get("Counter", Path.root_path())["cnt"]
            print (session["cnt_umbral2"], cnt)
            
            if(cnt > session["cnt_umbral2"]):
                measure = db_measures.json().get("Measure_"+str(cnt), Path.root_path())
                measure = float(measure["EUR/USD_value"].split(",")[0] + "." + measure["EUR/USD_value"].split(",")[1])
                session["cnt_umbral2"] = session["cnt_umbral2"]+1
                if(float(session["umbral2"]) > float(measure)):
                    session["cnt_umbral2"] = session["cnt_umbral2"]+1
                    return ""
                else:
                    measure = str(measure) + ", "
                    session["umbral2_vals"] = session["umbral2_vals"] +  measure
                    session["max_umbral_cnt"] = session["max_umbral_cnt"] -1
                    return measure
            else:
                return ""
        else:
            return "fin"
    else:
        return render_template("login.html")

@app.route('/umbral2_list')
def umbral2_list():
    if "username" in session:
        json_file = db_users.json().get(session["username"], Path.root_path())
        return render_template("profile.html", script_alert=session["username"], umbral2list =  session["umbral2_vals"],
            num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
            num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))
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
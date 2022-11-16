#librerías empleadas
from flask import Flask, render_template, redirect, request, url_for, session
import redis
from redis.commands.json.path import Path
import hashlib
import netifaces as ni
import os
import json

server_ip = ni.ifaddresses('enp0s3')[ni.AF_INET][0]['addr'] #obtencion direccion IP de la interfaz de red
server_port = 5000 #puerto del servidor web

app = Flask(__name__)
app.secret_key = "ayush"

db_users = redis.Redis(host="localhost", port=6379, db=1)   #conexiones con las bases de datos de redis
db_measures = redis.Redis(host="localhost", port=6379, db=0)

"""
Ŕecurso raíz, página principal del servidor web
"""
@app.route('/')  
def home(): 
    cnt = db_measures.json().get("Counter", Path.root_path())
    last_measure = db_measures.json().get("Measure_"+str(cnt["cnt"]), Path.root_path()) #extracción de la ultima medida tomada
    return render_template("homepage.html", measure=last_measure["EUR/USD_value"]) #retorno de la plantilla con la informacion

"""
Recurso para registro de cuentas de usuario
"""
@app.route('/register')
def register():
    #se comprueba si ya existe una sesión
    if "username" in session:
        #devuelve pagina de perfil
        return redirect("http://"+server_ip+":"+str(server_port)+"/profile", code=302)
    else:
        #devuelve pagina de registro
        return render_template("register.html")

"""
Recurso para comprobar datos de registro y actualizar base de datos de usuarios
"""
@app.route('/success_reg', methods=['POST'])
def success_reg():
    #comprueba si existe ya un usuario con ese mismo nombre
    if (db_users.json().get(request.form["username"], Path.root_path())):
        #si existe, retorna error
        return render_template("register.html",  script_alert="<tr><td style='color:red'>El usuario ya existe</td><td>")
    else:
        #si no, hashea la contraseña y almacena los datos en la base de datos
        passwd_hashed = hashlib.sha256(bytearray(request.form["pass"], "utf8")).hexdigest()
        db_users.json().set(request.form["username"], Path.root_path(), {"email" : request.form["email"], "password" : passwd_hashed, "measures_local" : 0, "measures_online" : 0})
        #redirige a la página principal
        return redirect("http://"+server_ip+":"+str(server_port)+"/", code=302)

"""
Recurso para acceder a las cuentas de usuario
"""
@app.route('/login')
def login():
    #se comprueba si ya existe una sesión
    if "username" in session:
        return redirect("http://"+server_ip+":"+str(server_port)+"/profile", code=302)
    else:
        return render_template("login.html") #devuelve la pagina de login

"""
Recurso para comprobar datos de login con la base de datos de usuarios
"""
@app.route('/success_log', methods=['POST'])
def success_log():
    user = db_users.json().get(request.form["username"], Path.root_path())
    #si el usuario existe
    if(user): 
        passwd_hashed = hashlib.sha256(bytearray(request.form["pass"], "utf8")).hexdigest()
        #comprueba la contraseña
        if (user["password"] == passwd_hashed):
            #si es correcta, le da acceso
            session["username"] = request.form["username"]
            return redirect("http://"+server_ip+":"+str(server_port)+"/profile", code=302)
        else:
            #si no es correcta le devuelve un error
            return render_template("login.html",  script_alert="<tr><td style='color:red'>Credenciales incorrectas</td><td>")
    else:
        #si no eexiste le devuelve un error
        return render_template("login.html",  script_alert="<tr><td style='color:red'>Credenciales incorrectas</td><td>")

"""
Recurso para finalizar la sesion y cerrar la cuenta
"""
@app.route('/logout')
def logout():
    #extracción de usuario de la sesion 
    session.pop('username', None)
    #redireccion a la pagina principal
    return redirect("http://"+server_ip+":"+str(server_port)+"/", code=302)

"""
Recurso de pagina de perfil de usuario
"""
@app.route('/profile')
def profile():
    #se comprueba si ya existe una sesion
    if "username" in session:
        #devuelve la pagina de perfil personalizada para el usuario determinado, obteniendo el nombre de usuario y el numero de medidas realizadas de la base de datos
        json_file = db_users.json().get(session["username"], Path.root_path())
        return render_template("profile.html", script_alert=session["username"],
            num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
            num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))
    else:
        return render_template("login.html")

"""
Recurso para realizar media de todas las medidas de la base de datos local
"""
@app.route('/av_local', methods=['POST'])
def av_local():
    cnt = db_measures.json().get("Counter", Path.root_path()) #obtencion del numero de medidas 
    values = []
    #preparacion de las muestras
    for i in range(0, cnt["cnt"]+1): 
        measure = db_measures.json().get("Measure_"+str(i), Path.root_path())
        measure = float(measure["EUR/USD_value"].split(",")[0] + "." + measure["EUR/USD_value"].split(",")[1])
        values.append(measure)
    #realizacion de la media
    average = get_average(values) 

    #actualizacion del numero de medidas locales asociado al usuario 
    json_file = db_users.json().get(session["username"], Path.root_path())
    json_file["measures_local"] = json_file["measures_local"] +1
    db_users.json().set(session["username"], Path.root_path(), json_file)
    #retorno de la pagina con la informacion
    return render_template("profile.html", script_alert=session["username"], av_local_value="Valor medio de las medidas de la base de datos local: " + str(average),
        num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
        num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))

"""
Recurso para realizar media de todas las medidas de la base de datos remota
"""
@app.route('/av_remote', methods=['POST'])
def av_remote():
    #obtencion de las muestras
    os.system('curl "https://api.thingspeak.com/channels/1909196/fields/1.json?result=2" -o /home/cer/computacion/p1/code/env/app-code/page_data/jsondata.json')
    f = open("/home/cer/computacion/p1/code/env/app-code/page_data/jsondata.json", "r")
    f = str(f.read())
    jsonobj = json.loads(f)
    values = []
    #preparacion de las muestras
    for i in jsonobj["feeds"]:
        values.append(float(i["field1"]))
    #realizacion de la media    
    average = get_average(values) 

    #actualizacion del numero de medidas remotas asociado al usuario 
    json_file = db_users.json().get(session["username"], Path.root_path())
    json_file["measures_online"] = json_file["measures_online"] +1
    db_users.json().set(session["username"], Path.root_path(), json_file)
    #retorno de la pagina con la informacion
    return render_template("profile.html", script_alert=session["username"], av_local_value="Valor medio de las medidas de la base de datos remota: " + str('%.4f'%(average)),
        num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
        num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))

"""
Recurso para la obtencion de los graficos externos de la base de datos remota
"""
@app.route('/external_graphs', methods=['POST'])
def external_graphs():
    #se comprueba si ya existe una sesión
    if "username" in session:
        #devuelve la pagina con la gráfica
        return render_template("graph.html")
    else:
        return render_template("login.html")   

"""
Recurso para enviar el umbral y recibir las 5 ultimas muestras que superen dicho valor
"""
@app.route('/umbral_1', methods=['POST'])
def umbral_1():
    #se comprueba si ya existe una sesión
    if "username" in session:
        #obtención del numero de medidas de la base de datos local
        cnt = db_measures.json().get("Counter", Path.root_path())
        values = []
        string=""
        for i in range(0, cnt["cnt"]+1):
            measure = db_measures.json().get("Measure_"+str(cnt["cnt"]-i), Path.root_path())
            measure = float(measure["EUR/USD_value"].split(",")[0] + "." + measure["EUR/USD_value"].split(",")[1])
            
            #se comprueba si las medidas superan el umbral
            if ((measure > float(request.form["value_umbral1"])) and (len(values) < 5)):
                values.append(measure)
                string = string + str(measure) + ", "
        #se retorna una pagina con la informacion de las cinco ultimas medidas que han cumplido el umbral determinado
        return render_template("profile.html", script_alert=session["username"], values_umbral_1= "Ultimos valores: " + string[0:len(string)-1])
    else:
        return render_template("login.html")

"""
Recurso para establecimiento del umbral actual, que determina que 5 nuevas muestras se enviaran al cliente
"""
@app.route('/umbral_2', methods=['POST'])
def umbral_2():
    #se comprueba si ya existe una sesión
    if "username" in session:  
        #actualizacion de las variables de sesion para llevar la cuenta de la ultima medida registrada (para guardarlas a partir de esta)
        session["cnt_umbral2"] = db_measures.json().get("Counter", Path.root_path())["cnt"]
        session["umbral2"] = request.form["value_umbral2"] #guardado del valor del umbral
        session["max_umbral_cnt"] = 5 #establecimiento del maximo de medidas
        session["umbral2_vals"] = "" #lista de valores
        json_file = db_users.json().get(session["username"], Path.root_path()) 
        #devuelve la pagina con el script de AJAX integrado  
        return render_template("profile.html", script_alert=session["username"], 
            umbral2='<script>$(document).ready(function(){ var ajaxDelay = 10000;setInterval(function(){var jqxhr = $.get( "umbral_2_val", function(data) {if(data=="fin"){window.location.href = "/umbral2_list";}else{document.getElementById("umbral_2_value").innerHTML = document.getElementById("umbral_2_value").innerHTML + data;}});}, ajaxDelay);});</script>',
            num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
            num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))
    else:
        return render_template("login.html")
 
"""
Recurso para solicitar si hay medidas que hayan superado el umbral desde que se inicio el proceso
"""
@app.route('/umbral_2_val')
def umbral_2_val():
    #se comprueba si ya existe una sesión
    if "username" in session:
        print(session["max_umbral_cnt"])
        #comprueba si quedan medidas por transmitir
        if (session["max_umbral_cnt"] > 0):
            cnt = db_measures.json().get("Counter", Path.root_path())["cnt"]
            print (session["cnt_umbral2"], cnt)
            
            #comprueba si hay medidas nuevas
            if(cnt > session["cnt_umbral2"]):
                measure = db_measures.json().get("Measure_"+str(cnt), Path.root_path())
                measure = float(measure["EUR/USD_value"].split(",")[0] + "." + measure["EUR/USD_value"].split(",")[1])
                session["cnt_umbral2"] = session["cnt_umbral2"]+1
                
                #comprueba si la nueva medida supera el umbral
                if(float(session["umbral2"]) > float(measure)):
                    session["cnt_umbral2"] = session["cnt_umbral2"]+1
                    return ""
                else:
                    measure = str(measure) + ", "
                    session["umbral2_vals"] = session["umbral2_vals"] +  measure
                    session["max_umbral_cnt"] = session["max_umbral_cnt"] -1
                    #devuelve las medidas
                    return measure
            else:
                return ""
        else:
            return "fin"
    else:
        return render_template("login.html")

"""
Recurso enviado tras la finalizacion del proceso para obtener la pagina completa y actualizada (eliminando el script de AJAX)
"""
@app.route('/umbral2_list')
def umbral2_list():
    #se comprueba si ya existe una sesión
    if "username" in session:
        json_file = db_users.json().get(session["username"], Path.root_path())
        #envio de la pagina con los datos actualizados
        return render_template("profile.html", script_alert=session["username"], umbral2list =  session["umbral2_vals"],
            num_measures_local= "Numero de medidas realizadas local: " + str(json_file["measures_local"]),
            num_measures_online= "Numero de medidas realizadas online: " + str(json_file["measures_online"]))
    else:
        return render_template("login.html")

"""
Funcion para calcular la media de datos pasados como array
"""
def get_average(values):
    result = 0
    for i in values:
        print (values)
        result = result + i
    print(len(values))
    result = result / len(values)
    #retorno de resultado
    return result

if __name__ == "__main__":
    app.run(host=server_ip, port=server_port, debug=True)

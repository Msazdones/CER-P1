#librerias empleadas
import time
import re
import os
import redis
from redis.commands.json.path import Path
from datetime import datetime

"""
Función que descarga y extrae la informacion del valor EUR/USD de una pagina web
"""
def download_and_parse_file():
	#realizacion de la peticion web y guardado de la pagina en archivo html
	os.system('curl https://es.investing.com/currencies/eur-usd -o /home/cer/computacion/p1/code/env/app-code/page_data/data')
	#apertura y lectura del archivo html guardado
	f = open("/home/cer/computacion/p1/code/env/app-code/page_data/data", "r")
	f = str(f.read())
	#busqueda del valor numerico mediante expresiones regulares
	value = re.findall('[0-9,]+', str(re.findall('data-test="instrument-price-last"[0-9,<>]*', f)))[0]
	return value #retorno del valor

"""
Funcion que obtiene y devuelve la fecha y la hora del momento de ser llamada en un formato DD/MM/YY hh:mm
"""
def obtain_date():
	now = datetime.now()
	return str(now.day)+'/'+str(now.month)+'/'+str(now.year)+' '+str(now.hour)+':'+str(now.minute) 

"""
Funcion para introducir informacion en la base de datos de Redis y en ThingSpeak
"""
def set_database_content(content, db, cnt):
	#introduccion de datos en base de datos de redis (local)
	db.json().set("Measure_"+str(cnt), Path.root_path(), content)
	db.json().set("Counter", Path.root_path(), {"cnt" : cnt})

	#introduccion de datos en la base de datos de thingspeak (remota) a traves de peticion web
	os.system('curl "https://api.thingspeak.com/update?api_key=UJUT54QP7JYM2WQB&field1=' +  content["EUR/USD_value"].split(",")[0] + '.' + content["EUR/USD_value"].split(",")[1] + '"')

"""
Cuerpo principal del programa
"""
def main():
	#identificador de la base de datos de muestras
	db = redis.Redis(host="localhost", port=6379, db=0)
	cnt = 0
	#bucle infinito, el programa toma muestras cada 2s indefinidamente
	while True:
		#obtencion de la muestra y la fecha y hora
		value = download_and_parse_file()
		date = obtain_date()
		
		#formateo de los datos para el almacenamiento correcto
		content = {"EUR/USD_value" : value, "Date" : date}
		#introduccion de los datos en base de datos
		set_database_content(content, db, cnt)
		cnt = cnt+1
		#el programa se duerme dos minutos
		time.sleep(120)

if __name__ == "__main__":
	main()

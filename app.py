import time
import re
import os
import redis
from redis.commands.json.path import Path
from datetime import datetime

def download_and_parse_file():
	os.system('curl https://es.investing.com/currencies/eur-usd -o /home/xubuntu/uni/computacion/p1/code/env/app-code/page_data/data')
	f = open("/home/xubuntu/uni/computacion/p1/code/env/app-code/page_data/data", "r")
	f = str(f.read())
	value = re.findall('[0-9,]+', str(re.findall('data-test="instrument-price-last"[0-9,<>]*', f)))[0]
	return value

def obtain_date():
	now = datetime.now()
	return str(now.day)+'/'+str(now.month)+'/'+str(now.year)+' '+str(now.hour)+':'+str(now.minute) 

def set_database_content(content, db, cnt):
	db.json().set("Measure_"+str(cnt), Path.root_path(), content)
	db.json().set("Counter", Path.root_path(), {"cnt" : cnt})

	os.system('curl "https://api.thingspeak.com/update?api_key=UJUT54QP7JYM2WQB&field1=' +  content["EUR/USD_value"].split(",")[0] + '.' + content["EUR/USD_value"].split(",")[1] + '"')
	os.system('curl "https://thingspeak.com/channels/1909196/charts/1?bgcolor=%23ffffff&color=%23d62020&dynamic=true&results=60&type=line&update=15" -o /home/xubuntu/uni/computacion/p1/code/env/app-code/templates/graph.html')

def main():
	db = redis.Redis(host="localhost", port=6379, db=0)
	cnt = 0
	while True:
		value = download_and_parse_file()
		date = obtain_date()
		
		content = {"EUR/USD_value" : value, "Date" : date}
		set_database_content(content, db, cnt)
		cnt = cnt+1
		time.sleep(120)

if __name__ == "__main__":
	main()

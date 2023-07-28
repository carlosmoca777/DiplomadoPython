#Monitor de temperatura V3
import network
import time
import urequests
import machine
from machine import Pin, ADC, PWM
from utime import sleep, sleep_ms
from dht import DHT22
import ujson
from utelegram import Bot
from _thread import start_new_thread, allocate_lock

s_dht1 = DHT22(Pin(15))#Establece pin para el sensor 1
s_water = ADC(Pin(34))#Establece en pin para el sensor de agua

buzzer = machine.PWM(machine.Pin(33), freq=1023, duty=0)

rele= Pin(25, Pin.OUT) # Rele control de energia
rele_fan = Pin(27, Pin.OUT)#Rele control de ventilacion

TOKEN = '6355819266:AAEcH7qkDwDJ5B1VTLrHlBVHu1v2TTcOKMw'
bot = Bot(TOKEN)
URL="https://api.thingspeak.com/update?api_key=1D32OCEAFN4LDADT"

#Declaracion de las variables 

#def cortaEnergia():

def conectaWifi(red, password):
    global miRed
    miRed = network.WLAN(network.STA_IF)
    if not miRed.isconnected():
        miRed.active(True)
        miRed.connect(red, password)
        print('Conectando a la red', red + "…")
        timeout = time.time()
        while not miRed.isconnected():
            if (time.ticks_diff(time.time(), timeout) > 10):
                return False
    return True
   
#Metodo hilo principal que ejecuta activa wifi
def loop1():  
    while True:
        if conectaWifi("Wokwi-GUEST", ""):
            print("Conexión exitosa!")
            print('Datos de la red (IP/netmask/gw/DNS):', miRed.ifconfig())
            print("Conectado!")
            start_new_thread(loop2, ())  # Iniciar loop2 en un hilo separado
            break
        else:
            print("Imposible conectar")
            miRed.active(False)
        sleep_ms(5000)  # Esperar 5 segundos antes de intentar nuevamente la conexión

#Hilo que realiza monitoreo de los sensores
def loop2():
    while True:
        s_dht1.measure()
        temp_dht1=s_dht1.temperature()
        hum_dht1=s_dht1.humidity()
    
        read_water = s_water.read_u16()
        print("---Datos del RACK----")
        print("Sensor DHT1 Temperatura:{} C   Humedad:{}% ".format(temp_dht1,hum_dht1))
        print("------------------------------------------")        
        #Control del agua en el rack
        percent_water = read_water * (100 / 65535)
        if percent_water <= 10:
            print("No se detecta agua ... todo normal")
            lectura=rele.value()
            if lectura == 1:
                print("Fujo normal de energia")
            else:
                print("Activa normal de energia")
                rele.on()
        else:
            print("Agua detectada porcentaje de agua: {:.2f}% ".format(percent_water))
            rele.off()# Corta energia
            print("----------->>corta Energia")

        # Verificar si la temperatura es mayor a 35 grados
        if temp_dht1 > 25:
            print("¡Alarma! La temperatura ha superado los 25 grados.")
            print("----------->>Encender Alarma")
            buzzer.duty(1023)
            time.sleep(5) # Mantener el buzzer activo por 5 segundos
            buzzer.duty(0)
            rele_fan.on() # Enciende ventilacion auxiliar
            print("----------->>Encendiendo ventilacion")  
        else:
            print("Todo Normal ....")
            print("ventilacion esta apagada")
            buzzer.duty(0)
            print("Alarma apagada")
            rele_fan.off() # Apaga ventilacion auxiliar
        
        enviaData(temp_dht1, hum_dht1, temp_dht2, hum_dht2, percent_water)
             
        sleep_ms(3000)  # Hacer una pausa de 5 segundos

def enviaData(temp_dht1, hum_dht1, temp_dht2, hum_dht2, percent_water):
    respuesta = urequests.get(URL+"&field1="+str(temp_dht1)+"&field2="+str(hum_dht1)+"&field3="+str(temp_dht2)+"&field4="+str(hum_dht2)+"&field5="+str(percent_water))# para thingspeak
    #respuesta = urequests.get(url+"&value1="+str(tem)+"&value2="+str(hum))# para ifttt
    print(respuesta.text)
    print(respuesta.status_code)
    respuesta.close ()
    time.sleep(1)
    

# Iniciar el bucle principal en un hilo separado
start_new_thread(loop1, ())

@bot.add_message_handler('ini')
def help(update):
    update.reply("""Monitor DataSense:
    \n Presione 1 para consulta temperatura sensor 1
    
    \n Presione 2 para consulta humedad sensor 1
    
    \n Presione 3 para verificar agua
    """)
    print("-------------------------->>Conectando con Telegram ......")

@bot.add_message_handler('1')
def help(update):
    global t_tem1
    s_dht1.measure()
    t_tem1=s_dht1.temperature()
    sub = "Temperatura: {:.1f} °C".format(t_tem1)
    update.reply(sub +" » DHT1")
    print("----------->> Temperatura sensor1 enviada a telegram: ", sub, type(sub) )
    print("----------->> enviando...... ")

@bot.add_message_handler('2')
def help(update):
    global t_hum1
    s_dht1.measure()
    t_hum1=s_dht1.humidity()
    sub3 = "Humedad: {:.1f} ˙%".format(t_hum1)
    update.reply(sub3 +" » DHT1")
    print("----------->>Humedad sensor 1 enviada a telegram: ", sub3, type(sub3) )
    print("----------->> enviando...... ")

@bot.add_message_handler('3')
def help(update):
    global t_water
    t_water = s_water.read_u16()
    percent_water = t_water * (100 / 65535)
    if percent_water <= 10:
        sub5 = "No se detecto agua en el rack: {:.1f} ˙%".format(percent_water)
        update.reply(sub5 +" » Sensor")
        print("No se detecta agua")
    else:
        sub5 = "Alerta se detecto agua en el rack: {:.1f} ˙%".format(percent_water)
        update.reply(sub5 +" » Sensor")   
        print("Agua detectada porcentaje de agua: {:.2f}% ".format(percent_water))

#@bot.add_message_handler('6')
#def help(update):
#    activaFan()
#
#@bot.add_message_handler('6')
#def help(update):
#    activaFan()
#    
#@bot.add_message_handler('99')
#def help(update):
#    rele.off()# Corta la energia
#    update.reply("Cortando energia")
#    print("----------->> enviando...... ")  

# Iniciar el bucle de bot de Telegram en el hilo principal    
bot.start_loop()    

sleep_ms(10000) #Esperar a que se conecte
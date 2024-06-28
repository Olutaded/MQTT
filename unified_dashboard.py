import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as mqtt
import random
import threading
import time
from queue import Queue

broker_address = "localhost"  # Use the IP address of your MQTT broker

# Global variables to store sensor data
temperature = 0.0
motion_detected = False
light_status = "OFF"

# Queue to update the dashboard in the main thread
update_queue = Queue()

# MQTT client for temperature sensor
def temperature_sensor():
    def on_connect(client, userdata, flags, rc):
        print("Temperature Sensor: Connected with result code " + str(rc))

    client = mqtt.Client(client_id="TemperatureSensor", userdata=None, protocol=mqtt.MQTTv311, transport="tcp", clean_session=True)
    client.on_connect = on_connect

    client.connect(broker_address, port=1883, keepalive=60)
    client.loop_start()

    try:
        while True:
            global temperature
            temperature = round(random.uniform(20.0, 25.0), 2)
            client.publish("home/temperature", temperature)
            print(f"Published: Temperature {temperature}°C")
            time.sleep(5)
    except KeyboardInterrupt:
        print("Temperature sensor stopped.")
    finally:
        client.loop_stop()

# MQTT client for motion sensor
def motion_sensor():
    def on_connect(client, userdata, flags, rc):
        print("Motion Sensor: Connected with result code " + str(rc))

    client = mqtt.Client(client_id="MotionSensor", userdata=None, protocol=mqtt.MQTTv311, transport="tcp", clean_session=True)
    client.on_connect = on_connect

    client.connect(broker_address, port=1883, keepalive=60)
    client.loop_start()

    try:
        while True:
            global motion_detected
            motion_detected = random.choice([0, 1])
            client.publish("home/motion", motion_detected)
            print(f"Published: Motion detected {motion_detected}")
            time.sleep(5)
    except KeyboardInterrupt:
        print("Motion sensor stopped.")
    finally:
        client.loop_stop()

# MQTT client for light controller
def light_controller():
    def on_connect(client, userdata, flags, rc):
        print("Light Controller: Connected with result code " + str(rc))
        client.subscribe("home/motion")

    def on_message(client, userdata, message):
        global light_status
        motion = bool(int(message.payload.decode()))
        if motion:
            light_status = "ON"
            print("Light ON: Motion detected")
        else:
            light_status = "OFF"
            print("Light OFF: No motion detected")
        update_queue.put(("light_status", light_status))

    client = mqtt.Client(client_id="LightController", userdata=None, protocol=mqtt.MQTTv311, transport="tcp", clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker_address, port=1883, keepalive=60)

    try:
        print("Starting light controller...")
        client.loop_forever()
    except KeyboardInterrupt:
        print("Light controller stopped.")
    finally:
        client.loop_stop()

# MQTT client for dashboard
def dashboard():
    def on_connect(client, userdata, flags, rc):
        print("Dashboard: Connected with result code " + str(rc))
        client.subscribe("home/temperature")
        client.subscribe("home/motion")

    def on_message(client, userdata, message):
        if message.topic == "home/temperature":
            temperature = float(message.payload.decode())
            update_queue.put(("temperature", temperature))
        elif message.topic == "home/motion":
            motion_detected = bool(int(message.payload.decode()))
            update_queue.put(("motion_detected", motion_detected))

    client = mqtt.Client(client_id="Dashboard", userdata=None, protocol=mqtt.MQTTv311, transport="tcp", clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker_address, port=1883, keepalive=60)

    try:
        print("Starting dashboard...")
        client.loop_forever()
    except KeyboardInterrupt:
        print("Dashboard stopped.")
    finally:
        client.loop_stop()

# Update the dashboard GUI with the latest data
def update_dashboard():
    try:
        while True:
            item_type, value = update_queue.get(block=False)
            if item_type == "temperature":
                temperature_label.config(text=f"Temperature: {value}°C")
            elif item_type == "motion_detected":
                motion_label.config(text=f"Motion detected: {value}")
            elif item_type == "light_status":
                light_label.config(text=f"Light: {value}")
    except:
        pass
    finally:
        root.after(1000, update_dashboard)

# Main function to create and run the GUI
def run_dashboard():
    global root, temperature_label, motion_label, light_label

    root = tk.Tk()
    root.title("Smart Home Monitoring System")

    mainframe = ttk.Frame(root, padding="150 150 150 150")
    mainframe.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    temperature_label = ttk.Label(mainframe, text="Temperature: 0°C")
    temperature_label.grid(row=0, column=0, pady=10)

    motion_label = ttk.Label(mainframe, text="Motion detected: False")
    motion_label.grid(row=1, column=0, pady=10)

    light_label = ttk.Label(mainframe, text="Light: OFF")
    light_label.grid(row=2, column=0, pady=10)

    root.after(1000, update_dashboard)
    root.mainloop()

# Run the MQTT clients in separate threads
if __name__ == "__main__":
    try:
        threading.Thread(target=temperature_sensor, daemon=True).start()
        threading.Thread(target=motion_sensor, daemon=True).start()
        threading.Thread(target=light_controller, daemon=True).start()
        threading.Thread(target=dashboard, daemon=True).start()
        run_dashboard()
    except KeyboardInterrupt:
        print("Exiting program.")



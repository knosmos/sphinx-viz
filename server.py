import time
import threading
import struct

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import serial
import serial.tools.list_ports

""" == SERVER SETUP == """

POLL_INTERVAL = 0.05

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

""" == SERIAL SETUP == """

ports = serial.tools.list_ports.comports()
print("AVAILABLE PORTS:")
for port, desc, hwid in sorted(ports):
    print("{}: {} [{}]".format(port, desc, hwid))
if len(ports) > 1:
    port = input("SELECT PORT > ")
    if port == "":
        port = sorted(ports)[0][0]
else:
    ports = []
    while len(ports) == 0:
        ports = serial.tools.list_ports.comports()
    port = ports[0][0]
print(f"SELECTED PORT: {port}")
serial_port = serial.Serial(port, baudrate=9600, timeout=1)

""" == CONFIGURATION == """

"""
struct sensor_data {
    int16_t altitude_bmp;	// altitude_bmp = altitude (m) * 4
    int16_t altitude_tof;	// altitude_tof = altitude (mm)
    int16_t gyro_lsm[3];	// gyro_lsm = gyro (millideg/sec) / 70
    int16_t accel_lsm[3];	// accel_lsm = accel (millig) / 0.122
    int16_t mag_lis[3];      // mag_lis = magnetometer (normalized: -1, 1) * 2^10
    int8_t gyro_bno[3];	// gyro_bno = gyro (degrees)

    double lat_cd;		// lat_cd = latitude (non-RTK)
    double lon_cd;		// lon_cd = longitude (non-RTK)
    double lat_rtk;		// lat_rtk = latitude (RTK)
    double lon_rtk;	// lon_rtk = longitude (RTK)

    
    double bmp_lpf;         // meters
    double gyro_lpf[3];     // deg / s
    double attitude_lpf[4]; // quaternion

    double thrust; 
    double moment; 
    double beta_y_deg; 
    double beta_z_deg; 

    uint16_t props_top_pwm; // pwm (1000-2500)
    uint16_t props_btm_pwm; // pwm (1000-2500)
    uint16_t tvc_y_deg; // degs
    uint16_t tvc_z_deg; // degs
    
    uint8_t temp;		// temp = power board core temp (C) * 255 / 64
    uint8_t batt_voltage; 	// batt_voltage = battery voltage (V) * 255 / 16
    uint8_t servo_voltage;	// servo_voltage = servo voltage (V) * 255 / 8
    uint8_t count;
};
"""

SENSOR_STATE = {
    "altitude_bmp": 0,
    "altitude_tof": 0,
    "gyro_lsm": [0, 0, 0],
    "accel_lsm": [0, 0, 0],
    "mag_lis": [0, 0, 0],
    "gyro_bno": [0, 0, 0],
    "lat_cd": 0.0,
    "lon_cd": 0.0,
    "lat_rtk": 0.0,
    "lon_rtk": 0.0,

    # lpf outputs
    "bmp_lpf": 0.0, 
    "gyro_lpf": [0, 0, 0], 
    "attitude_lpf": [0, 0, 0, 0], 

    # controls outputs (phase 1)
    "thrust": 0.0, 
    "moment": 0.0, 
    "beta_y_deg": 0.0, 
    "beta_z_deg": 0.0, 

    # controls outputs (phase 2)
    "props_top_pwm": 0, 
    "props_btm_pwm": 0, 
    "tvc_y_deg": 0, 
    "tvc_z_deg": 0, 



    "temperature": 0.0,
    "esc_voltage": 0.0,
    "servo_voltage": 0.0,
    "connected": False,
    "connection_reliability": 0.0,
    "health": [
        ["GPS", False],
        ["RTK", False],
        ["BMP", False],
        ["TOF", False],
        ["LSM", False],
        ["LIS", False],
        ["BNO", False],
        ["AUX", False],
    ]
}

STRUCT_FORMAT = "<11h3b16d4H5B"
STRUCT_LENGTH = struct.calcsize(STRUCT_FORMAT)

CONNECTION_TIMEOUT = 5.0
LAST_RECEIVED_TIME = time.time()
COUNTS = []

" == SERIAL LOGIC =="

current_data = bytearray()

def receive_data():
    if serial_port.in_waiting > 0:
        packet = serial_port.read(serial_port.in_waiting)
        if packet.endswith(b"\r\n"):
            packet = packet[:-2]
        if packet:
            # debug_hex = " ".join(f"{b:02x}" for b in packet)
            # print("!!! RAW:", debug_hex)
            # print(f"!!! RAW LENGTH: {len(packet)} (expected {STRUCT_LENGTH})")
            return packet
    return None

def update_thread():
    global SENSOR_STATE, current_data, LAST_RECEIVED_TIME
    while True:
        data = receive_data()
        if data is not None:
            current_data.extend(data)

        # print(current_data)

        while len(current_data) >= STRUCT_LENGTH:
            next_start = current_data.find(b"67")
            data_start = next_start + 2
            frame = bytes(current_data[data_start:data_start+STRUCT_LENGTH])

            print(frame)
            current_data = current_data[data_start+STRUCT_LENGTH:]

            try:
                unpacked = struct.unpack(STRUCT_FORMAT, frame)

                # Field offsets in <11h3b4d3B payload:
                SENSOR_STATE["altitude_bmp"] = unpacked[0] / 10.0
                SENSOR_STATE["altitude_tof"] = unpacked[1] / 1000
                SENSOR_STATE["gyro_lsm"] = [x * 70.0 for x in unpacked[2:5]]
                SENSOR_STATE["accel_lsm"] = [x * 0.122 for x in unpacked[5:8]]
                SENSOR_STATE["mag_lis"] = [x / 1024.0 for x in unpacked[8:11]]
                SENSOR_STATE["gyro_bno"] = list(unpacked[11:14])
                SENSOR_STATE["lat_cd"] = unpacked[14]
                SENSOR_STATE["lon_cd"] = unpacked[15]
                SENSOR_STATE["lat_rtk"] = unpacked[16]
                SENSOR_STATE["lon_rtk"] = unpacked[17]

                SENSOR_STATE["bmp_lpf"] = unpacked[18]
                SENSOR_STATE["gyro_lpf"] = unpacked[19:22]
                SENSOR_STATE["attitude_lpf"] = unpacked[22:26]

                SENSOR_STATE["thrust"] = unpacked[26]
                SENSOR_STATE["moment"] = unpacked[27]
                SENSOR_STATE["beta_y_deg"] = unpacked[28]
                SENSOR_STATE["beta_z_deg"] = unpacked[29]

                SENSOR_STATE["props_top_pwm"] = unpacked[30]
                SENSOR_STATE["props_btm_pwm"] = unpacked[31]
                SENSOR_STATE["tvc_y_deg"] = unpacked[32]
                SENSOR_STATE["tvc_z_deg"] = unpacked[33]


                SENSOR_STATE["temperature"] = unpacked[34] * 64 / 255.
                SENSOR_STATE["esc_voltage"] = unpacked[35] * 16 / 255.
                SENSOR_STATE["servo_voltage"] = unpacked[36] * 8 / 255

                for i, sensor in enumerate(SENSOR_STATE["health"]):
                    SENSOR_STATE["health"][i][1] = bool(unpacked[37] & (1 << (7-i)))

                LAST_RECEIVED_TIME = time.time()
                COUNTS.append(unpacked[38])
                if len(COUNTS) > 5:
                    COUNTS.pop(0)

            except Exception as e:
                print(f"Error parsing data: {frame.hex()} ({e})")
        if time.time() - LAST_RECEIVED_TIME > CONNECTION_TIMEOUT:
            SENSOR_STATE["connected"] = False
            SENSOR_STATE["connection_reliability"] = 0.0
        else:
            SENSOR_STATE["connected"] = True
            if len(COUNTS) > 1:
                received_packets = 1
                expected_packets = 1
                for i in range(1, len(COUNTS)):
                    delta = (COUNTS[i] - COUNTS[i - 1]) % 256
                    if delta == 0:
                        continue
                    received_packets += 1
                    expected_packets += delta

                if expected_packets > 0:
                    print("Received packets:", received_packets, "Expected packets:", expected_packets)
                    reliability = received_packets / expected_packets
                    SENSOR_STATE["connection_reliability"] = max(0.0, min(1.0, reliability))
                else:
                    SENSOR_STATE["connection_reliability"] = 0.0
            else:
                SENSOR_STATE["connection_reliability"] = 0.0
        time.sleep(POLL_INTERVAL)

t = threading.Thread(target=update_thread, daemon=True)
t.start()

" == SERVER ROUTING == "

@app.get("/data")
def get_data():
    global SENSOR_STATE
    return SENSOR_STATE

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
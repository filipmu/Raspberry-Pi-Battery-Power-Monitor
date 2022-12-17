#!/usr/bin/env python3
# coding: utf-8

# Monitors the voltage and current and initiates shutdown if necessary
# Uses mmap file (a file mapped to memory) to allow other processes to see the latest metrics


# For the INA226 component

# has an emergency shutdown if the battery voltage is too low.




print("Starting up ...")
import systemd.daemon
from systemd import journal

from smbus import SMBus
import subprocess as sp
from time import sleep
from datetime import datetime
from datetime import timedelta

import mmap

import json
import os, sys

from multiprocessing import shared_memory


shared_memory_name = "monitor_memory"
shared_memory_size = 128

from multiprocessing import resource_tracker


def remove_shm_from_resource_tracker():
    """Monkey-patch multiprocessing.resource_tracker so SharedMemory won't be tracked

    More details at: https://bugs.python.org/issue38119
    Example of use at: https://bugs.python.org/file49859/mprt_monkeypatch.py
    
    """

    def fix_register(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.register(self, name, rtype)
    resource_tracker.register = fix_register

    def fix_unregister(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.unregister(self, name, rtype)
    resource_tracker.unregister = fix_unregister

    if "shared_memory" in resource_tracker._CLEANUP_FUNCS:
        del resource_tracker._CLEANUP_FUNCS["shared_memory"]
        

def write_mem(d, shm):
    s = (json.dumps(outdict) ).encode('utf-8')
    l = len(s)
    if l + 1 <= shm.size:
        shm.buf[0:l+1] = s + b'\x00' # use a null terminated string
        return(0)
    else:
        return(1)


def shutdown():
    command = 'echo "Battery low! shutting down in 5 minutes" && /usr/bin/sudo /usr/sbin/shutdown -h +5 "Battery Voltage Low" '
    process = sp.Popen(command,shell=True)
    #output = process.communicate()[0]
    #print(output)
    #return output
    
def cputemp():
    with open("/sys/class/thermal/thermal_zone0/temp", 'r') as f:
        return float(f.read().strip()) / 1000
    
 
def swap_bytes(w):
    byte_val = w.to_bytes(2, 'little')
    return int.from_bytes(byte_val, byteorder='big')
 
def init_INA226(i2c,addr, average_setting, bus_v_conversion_time_setting,
                shunt_v_conversion_time_setting):
    INA226_REG_CONFIG = 0x00
    
    i2c.write_word_data(addr, INA226_REG_CONFIG, swap_bytes(0x8000)) # Reset IC
    
    #             (voltage_range << BRNG |gain << PG0 | bus_adc << BADC1 | shunt_adc << SADC1 | CONT_SH_BUS)
    config_val = (average_setting << 9 | bus_v_conversion_time_setting << 6 |
                  shunt_v_conversion_time_setting << 3 |  7)
    
    
    
    i2c.write_word_data(addr, INA226_REG_CONFIG, swap_bytes(config_val))

# setup


#define the shared memory
remove_shm_from_resource_tracker()

#close any memory that might still be open
try:
    shm = shared_memory.SharedMemory(create=False, size=shared_memory_size, name=shared_memory_name)
    shm.close()
    shm.unlink()
    print(f"Existing shared memory found and unlinked")
except FileNotFoundError:
    print(f"No existing shared memory found")

    
shared_mem = shared_memory.SharedMemory(create=True, size=shared_memory_size, name=shared_memory_name)
print(f"New shared memory created")
print(f'Startup complete')
systemd.daemon.notify('READY=1')

start_time = datetime.now()

sleep_time = 10
volt_threshold = 3.5 * 3  # for a 3 cell li-ion battery
#volt_threshold = 11.670
shutdown_flag = False

i2c = SMBus(1)
addr = 0x40

INA226_REG_SHUNTVOLTAGE = 0x01  # Voltage across shunt
INA226_REG_BUSVOLTAGE = 0x02 # Voltage at input (battery)
INA226_REG_POWER = 0x03
INA226_REG_CURRENT = 0x04
INA219_REG_CALIBRATION = 0x05

shunt_resistance_ohms = 0.1
supply_mAh = 0.0




init_INA226(i2c,addr, average_setting=0, bus_v_conversion_time_setting=3,
                shunt_v_conversion_time_setting=3)

sleep(1) #make sure there is data there

current_time = start_time
while True:
    last_time = current_time
    current_time = datetime.now();

    shunt_voltage_mV = 0.0025 * float(swap_bytes(i2c.read_word_data(addr, INA226_REG_SHUNTVOLTAGE)))
    
    shunt_current_mA = shunt_voltage_mV/shunt_resistance_ohms
            
    supply_mAh = supply_mAh + shunt_current_mA * ((current_time-last_time).total_seconds()/60.0/60.0)
            
    supply_voltage_V = swap_bytes(i2c.read_word_data(addr,INA226_REG_BUSVOLTAGE)) * 0.00125     

    elapsed_time_sec = (datetime.now() - start_time).total_seconds()
    
    cpu_temp_C = cputemp()
    #print()
    #print(f"Elapsed time sec={elapsed_time_sec:0.3f}")
    
    #print(f"Voltage by supply={supply_voltage_V:0.3f}")
            
    #print(f"Current by supply={shunt_current_mA:0.3f}")
    #print(f"mAh by supply={supply_mAh:0.3f}")
    
    under_voltage_state = supply_voltage_V < volt_threshold
    outdict = {"ET":f"{elapsed_time_sec:0.3f}",
               "V":f"{supply_voltage_V:0.3f}",
               "mA":f"{shunt_current_mA:0.3f}",
               "mAh":f"{supply_mAh:0.3f}",
               "UV":f"{under_voltage_state}",
               "TempC":f"{cpu_temp_C:0.2f}"}
    
 
    
    write_mem(outdict,shared_mem)

    if under_voltage_state and not shutdown_flag:
        journal.send(f"Elapsed Time={elapsed_time_sec:0.3f} supplied mAh is {supply_mAh:0.3f}")
        journal.send(f"Battery monitor detected low voltage={supply_voltage_V:0.3f} and will trigger system shutdown")
        shutdown()
        shutdown_flag = True
    sleep(sleep_time)


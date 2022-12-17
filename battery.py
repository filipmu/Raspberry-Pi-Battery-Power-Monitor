#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  battery.py
#  
#  Copyright 2022 Filip Mulier <filip@filip-desktop>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

from time import sleep
import json
import os, sys
from multiprocessing import shared_memory


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
        
        
        



remove_shm_from_resource_tracker()
shared_memory_name = "monitor_memory"
shm = shared_memory.SharedMemory(create=False, size=128, name=shared_memory_name)


def read_mem(shm):
    q = bytes(shm.buf)
    q = q[:q.index(b'\x00')]
    d = json.loads(q)
    return d


d = read_mem(shm)

print( f'battery voltage = {d["V"]} volts.  Run time = {float(d["ET"])/3600.0} hours')
print( f'battery current = {d["mA"]} mA.  Capacity used = {d["mAh"]} mAh')
print( f'CPU temp = {d["TempC"]} deg C.')


shm.close()

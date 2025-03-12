# -*- coding: utf-8 -*-
import sys
import math
import time
import numpy as np
import pygame
import socket


from Physics import Physics
from Graphics_submarine import Graphics

class Submarine:
    def __init__(self):
        self.physics = Physics(hardware_version=3) #setup physics class. Returns a boolean indicating if a device is connected
        self.graphics = Graphics(False) #setup class for drawing and graphics.
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(("127.0.0.1", 40002))
        self.recv_sock.setblocking(False)
        
        # Wait for user input
        run = True
        while run:
            keyups, _ = self.graphics.get_events()
            for key in keyups:
                if key== ord('e'):
                    run = False

        # Wait for at least one message from the master. Only continue once something is received.
        while True:
            try: 
                self.send_sock.sendto(np.array([0,0], dtype=np.float32).tobytes(), ("127.0.0.1", 40001))
                _ = self.recv_sock.recvfrom(1024)
                # Set a timeout to allow closing the window automatically when the communication is broken
                self.recv_sock.settimeout(5)
                print("Got UDP message")
                break
            except BlockingIOError:
                print("Waiting for UDP communication")
                pass
    
    def run(self):
        p = self.physics #assign these to shorthand variables for easier use in this function
        g = self.graphics
        #get input events for both keyboard and mouse
        keyups, xm = g.get_events()
        #  - keyups: list of unicode numbers for keys on the keyboard that were released this cycle
        #  - pm: coordinates of the mouse on the graphics screen this cycle (x,y)      
        #get the state of the device, or otherwise simulate it if no device is connected (using the mouse position)
        g.erase_screen()

        for key in keyups:
            if key==ord("q"): #q for quit, ord() gets the unicode of the given character
                sys.exit(0) #raises a system exit exception so the "PA.close()" function will still execute
            if key == ord('m'): #Change the visibility of the mouse
                pygame.mouse.set_visible(not pygame.mouse.get_visible())
            if key == ord('r'): #Change the visibility of the linkages
                g.show_linkages = not g.show_linkages
            if key == ord('d'): #Change the visibility of the debug text
                g.show_debug = not g.show_debug
            # TODO: Add more keys
        
        try:
            # Receive position
            recv_data, _ = self.recv_sock.recvfrom(1024)
            xh = np.array(np.frombuffer(recv_data, dtype=np.float64))
            # Scale received values
            xh *= np.array([1.142, 1.4])
            xh[1] -= 62
            # Make sure they are pixels and the type is np array 
            xh = np.array(xh, dtype=int)
        except socket.timeout:
            pygame.quit() # stop pygame
            raise RuntimeError("Connection lost")

        # Send force
        fe = np.array([0.0,0.0], dtype=np.float32)
        self.send_sock.sendto(fe.tobytes(), ("127.0.0.1", 40001))

        xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=0.8) #simulate forces with mouse haptics
        pos_phys = g.inv_convert_pos(xh)
        pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
        pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        g.render(pA0,pB0,pA,pB,xh,fe,xm)
        
    def close(self):
        self.graphics.close()
        self.physics.close()

if __name__=="__main__":
    submarine = Submarine()
    try:
        while True:
            submarine.run()
    finally:
        submarine.close()
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
        self.physics = Physics(hardware_version=0, connect_device=False) #setup physics class. Returns a boolean indicating if a device is connected
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
                if key== pygame.K_SPACE:
                    run = False

        # Wait for at least one message from the master. Only continue once something is received.
        while True:
            try: 
                self.send_sock.sendto(np.array([0,0], dtype=np.float32).tobytes(), ("127.0.0.1", 40001))
                _ = self.recv_sock.recvfrom(1024)
                # Set a timeout to allow closing the window automatically when the communication is broken
                self.recv_sock.settimeout(1)
                print("Got UDP message")
                break
            except BlockingIOError:
                print("Waiting for UDP communication")
                pass
    
    def run(self):
        p = self.physics #assign these to shorthand variables for easier use in this function
        g = self.graphics
        #get input events for both keyboard and mouse
        keyups, keypressed = g.get_events()
        #  - keyups: list of unicode numbers for keys on the keyboard that were released this cycle
        #  - pm: coordinates of the mouse on the graphics screen this cycle (x,y)      
        #get the state of the device, or otherwise simulate it if no device is connected (using the mouse position)
        xh = g.haptic.center
        xs = np.array(g.submarine_pos)
        xh = np.array(xh, dtype=np.float64) #make sure fe is a numpy array
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
            
        if keypressed[pygame.K_LEFT]:
            xs[0] = np.clip(xs[0] - 1, 0, g.window_size[0] - 150)
        if keypressed[pygame.K_RIGHT]:
            xs[0] = np.clip(xs[0] + 1, 0, g.window_size[0] - 150)

        
        try:
            # Receive position
            recv_data, _ = self.recv_sock.recvfrom(1024)
            xm = np.array(np.frombuffer(recv_data, dtype=np.float64))
            # TODO: Scale received values
            xm[0] = np.clip((xm[0] + ((g.submarine_pos[0] + 150) - (g.window_size[0]/2))), -100, g.window_size[0] + 100)
            xm[1] = np.clip(((xm[1] + 20) * 1.2), 0, g.window_size[1] + 75)
            # Make sure they are pixels and the type is np array 
            xm = np.array(xm, dtype=int)
        except socket.timeout:
            pygame.quit() # stop pygame
            raise RuntimeError("Connection lost")

        # Send force
        # fe = -50 * (((350,250) - xm) / g.window_scale) 
        fe = np.array([0,0], dtype=np.float32)
        self.send_sock.sendto(fe.tobytes(), ("127.0.0.1", 40001))

        xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=0.8) #simulate forces with mouse haptics
        pos_phys = g.inv_convert_pos(xh)
        pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
        pB0 = pA0
        pA = (pA[0] / 3, pA[1] / 3)
        pB = (pB[0] / 4, pB[1] / 4)
        pE = (pE[0] / 2, pE[1])
        pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        g.render(pA0,pB0,pA,pB,xh,fe,xm, xs)
        
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
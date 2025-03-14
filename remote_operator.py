# -*- coding: utf-8 -*-
import sys
import numpy as np
import pygame
import socket

from Physics import Physics
from Graphics_operator import Graphics

class PA:
    def __init__(self):
        self.physics = Physics(hardware_version=3) #setup physics class. Returns a boolean indicating if a device is connected
        self.device_connected = self.physics.is_device_connected() #returns True if a connected haply device was found
        self.graphics = Graphics(self.device_connected) #setup class for drawing and graphics.
        
        # Set up socket for UDP communication 
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(("127.0.0.1", 40001))
        self.recv_sock.setblocking(False)

        # Submarine initial position
        self.xs = np.array([320, 10], dtype=np.float64) 

        # Wait for user to press the space bar
        self.graphics.show_loading_screen()
        run = True
        while run:
            keyups, _, _= self.graphics.get_events()
            for key in keyups:
                if key== pygame.K_SPACE:
                    run = False 

        # Wait for at least one message from the master. Only continue once something is received.
        print("Waiting for submarine communication")
        i = 0
        while True:
            try: 
                _= self.recv_sock.recvfrom(1024)
                print("Connected")
                # Set a timeout to allow closing the window automatically when the communication is broken
                self.recv_sock.settimeout(1)
                break
            except BlockingIOError:
                self.graphics.show_loading_screen(True, i)
                i += 1
            
        ##############################################
    
    def run(self):
        p = self.physics #assign these to shorthand variables for easier use in this function
        g = self.graphics
        #get input events for both keyboard and mouse
        keyups, xm, keypressed = g.get_events()
        #  - keyups: list of unicode numbers for keys on the keyboard that were released this cycle
        #  - pm: coordinates of the mouse on the graphics screen this cycle (x,y)      
        #get the state of the device, or otherwise simulate it if no device is connected (using the mouse position)
        if self.device_connected:
            pA0,pB0,pA,pB,pE = p.get_device_pos() #positions of the various points of the pantograph
            pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        else:
            xh = g.haptic.center
            #set xh to the current haptic position, which is from the last frame.
            #This previous position will be compared to the mouse position to pull the endpoint towards the mouse
        fe = np.array([0.0,0.0]) #fx,fy
        xh = np.array(xh, dtype=np.float64) #make sure fe is a numpy array

        # xc,yc = g.screenVR.get_rect().center
        g.erase_screen()
        ##############################################
        #ADD things here that run every frame at ~100fps!
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
            self.xs[0] = np.clip(self.xs[0] - 1, 0, 800 - 150)
        if keypressed[pygame.K_RIGHT]:
            self.xs[0] = np.clip(self.xs[0] + 1, 0, 800 - 150)

        # Send Position from the haptic device or mouse and the submarine position
        message = np.array([xh, self.xs])
        self.send_sock.sendto(message.tobytes(), ("127.0.0.1", 40002))

        # Receive Force feedback
        try:
            recv_data, _ = self.recv_sock.recvfrom(1024)
            fe = np.frombuffer(recv_data, dtype=np.float32)
            # TODO: Scale the feedback to make it stable
            fe = np.array(fe, dtype=np.float32)
        except socket.timeout:
            raise RuntimeError("Connection lost")

        ##############################################
        if self.device_connected: #set forces only if the device is connected
            p.update_force(fe)
        else:
            xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=0.8) #simulate forces with mouse haptics
            pos_phys = g.inv_convert_pos(xh)
            pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
            pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        g.render(pA0,pB0,pA,pB,xh,fe,xm)
        
    def close(self):
        ##############################################
        #ADD things here that you want to run right before the program ends!
        
        ##############################################
        self.graphics.close()
        self.physics.close()

if __name__=="__main__":
    pa = PA()
    try:
        while True:
            pa.run()
    finally:
        pa.close()
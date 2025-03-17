# -*- coding: utf-8 -*-
import sys
import numpy as np
import pygame
import socket

from Physics import Physics
from Graphics_submarine import Graphics

        

class Submarine:
    def __init__(self):
        self.physics = Physics(hardware_version=0, connect_device=False) #setup physics class. Returns a boolean indicating if a device is connected
        self.graphics = Graphics(False,3) #setup class for drawing and graphics.
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(("127.0.0.1", 40002))
        self.recv_sock.setblocking(False)
        
        self.fish_left = pygame.transform.scale(pygame.image.load('imgs/fish_left.png'), (40, 20))
        self.fish_right = pygame.transform.scale(pygame.image.load('imgs/fish_right.png'), (40, 20))
        self.fish_dir = self.fish_right
        #self.fish_pos = np.array([200,400])
        self.fish_pos = np.array([400,400])
        
        self.fish_mode = 1
        
        self.wall = pygame.Rect(0, 300, 185, 600)
        self.platform = pygame.Rect(600, 400, 800, 600)
        self.table = pygame.Rect(630, 400, 800, 25)
        self.ground = pygame.Rect(185, 575, 415, 50)
        self.dGray = (50,50,50)
        self.bGray = (230,230,230)
        self.dBrown = (92, 64, 51)
        self.Sand = (198, 166, 100)
        #self.wall = pygame.Rect(xc, yc, 300, 300)

        # Wait for at least one message from the master. Only continue once something is received.
        print("Waiting for operator communication")
        i = 0
        while True:
            for event in pygame.event.get():  # Handle events to keep the window responsive
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
            try: 
                self.send_sock.sendto(np.array([0,0], dtype=np.float32).tobytes(), ("127.0.0.1", 40001))
                _ = self.recv_sock.recvfrom(1024)
                # Set a timeout to allow closing the window automatically when the communication is broken
                self.recv_sock.settimeout(1)
                print("Connected")
                break
            except BlockingIOError:
                self.graphics.show_loading_screen(i)
                i += 1
                pass
    
    def run(self):
        p = self.physics #assign these to shorthand variables for easier use in this function
        g = self.graphics
        #get input events for both keyboard and mouse
        g.get_events()
        xs = np.array(g.submarine_pos)
        xh = np.array(g.haptic.center, dtype=np.float64) #make sure fe is a numpy array
        g.erase_screen()
        #g.screenHaptics.blit(self.fish_dir, self.fish_pos)
        pygame.draw.rect(g.screenHaptics,self.dBrown,self.wall)
        pygame.draw.rect(g.screenHaptics,self.dGray,self.platform)
        pygame.draw.rect(g.screenHaptics,self.bGray,self.table)
        pygame.draw.rect(g.screenHaptics,self.Sand,self.ground)
        
        try:
            # Receive position
            recv_data, _ = self.recv_sock.recvfrom(1024)
            data = np.array(np.frombuffer(recv_data, dtype=np.float64))
            xm = data[:2]
            # Scale end effector position
            xm[0] = np.clip((xm[0] + ((g.submarine_pos[0] + 177) - (g.window_size[0]/2))), -100, g.window_size[0] + 100)
            xm[1] = np.clip((xm[1] * 1.3), 0, g.window_size[1] + 75)
            # Make sure they are pixels and the type is np array 
            xm = np.array(xm, dtype=int)
            xs = np.array(data[2:], dtype=int)
        except socket.timeout:
            pygame.quit() # stop pygame
            raise RuntimeError("Connection lost")

        # TODO: Calculate forces for feedback
        # Send force
        fe = np.array([0,0], dtype=np.float32)
        self.send_sock.sendto(fe.tobytes(), ("127.0.0.1", 40001))

        xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=0.8) #simulate forces with mouse haptics
        
        if(xh[1] >=550):
            xh[1] = 550
        pos_phys = g.inv_convert_pos(xh)
        pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
        pB0 = pA0
        pA = (pA[0] / 3, pA[1] / 3)
        pB = (pB[0] / 4, pB[1] / 4)
        pE = (pE[0] / 2, pE[1])
        pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        g.render(pA0,pB0,pA,pB,xh,fe,xm,xs)
        

        
    def close(self):
        self.graphics.close()
        self.physics.close()
        self.send_sock.close()
        self.recv_sock.close()

if __name__=="__main__":
    submarine = Submarine()
    try:
        while True:
            submarine.run()
    finally:
        submarine.close()
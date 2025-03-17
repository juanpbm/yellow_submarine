# -*- coding: utf-8 -*-
import sys
import numpy as np
import pygame
import socket
import time

from Physics import Physics
from Graphics_submarine import Graphics

class Submarine:
    def __init__(self):
        self.physics = Physics(hardware_version=0, connect_device=False) #setup physics class. Returns a boolean indicating if a device is connected
        self.graphics = Graphics(False) #setup class for drawing and graphics.
        # Set up UDP sockets
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(("127.0.0.1", 40002))
        self.recv_sock.setblocking(False)

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

        # Init Metrics variables
        self.passed = False
        self.damage = 0 # percentage
        self.path_length = 0 # pixels
        self.init_time = time.time() # seconds
        self.max_time = 0.1 * 60 # "T_minutes" * 60s = T_seconds 
    
    def run(self):
        p = self.physics #assign these to shorthand variables for easier use in this function
        g = self.graphics
        #get input events for both keyboard and mouse
        g.get_events()
        xs = np.array(g.submarine_pos)
        xh = np.array(g.haptic.center, dtype=np.float64) #make sure fe is a numpy array
        g.erase_screen()
        
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
        pos_phys = g.inv_convert_pos(xh)
        pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
        pB0 = pA0
        pA = (pA[0] / 3, pA[1] / 3)
        pB = (pB[0] / 4, pB[1] / 4)
        pE = (pE[0] / 2, pE[1])
        pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        g.render(pA0,pB0,pA,pB,xh,fe,xm,xs)

        # Check if game is over
        print(time.time() - self.init_time)
        if (time.time() - self.init_time >= self.max_time):
            self.passed = False
            raise RuntimeError("Game Finished")
        
    def close(self):
        # Metrics 
        final_time = time.time() - self.init_time
        play_again = self.graphics.show_exit_screen(self.passed, final_time, self.path_length, self.damage)
        print(f"Passed: {self.passed}, Time: {final_time:.3f}, Path_length: {self.path_length}")

        # Close used resources
        self.graphics.close()
        self.physics.close()
        self.send_sock.close()
        self.recv_sock.close()
        return play_again



if __name__=="__main__":
    play_again = True
    while play_again:
        submarine = Submarine()
        try:
            while True:
                submarine.run()
        except:
            play_again = submarine.close()
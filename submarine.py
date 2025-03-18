# -*- coding: utf-8 -*-
import sys
import numpy as np
import pygame
import socket
import random
import time
import math

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

                self.mass=0.5

            
        self.mass=0.5

        self.haptic_width = 48
        self.haptic_height = 48
        self.haptic_length = 48

        # Constants for gravity, buoyancy, and damping
        self.mass = 10  
        self.water_density = 1025  
        self.gravity = 9.81  
        self.drag_coefficient = 1

    
        self.cross_sectional_area = (self.haptic_width / self.graphics.window_scale) * (
            self.haptic_height / self.graphics.window_scale
        )  
        self.b_water = 0.5 * self.water_density * self.drag_coefficient * self.cross_sectional_area


        
        self.displaced_volume = (
            (self.haptic_width / self.graphics.window_scale)
            * (self.haptic_height / self.graphics.window_scale)
            * (self.haptic_length / self.graphics.window_scale)
        ) 

        # Perturbation parameters
        self.window_height = 400  
        self.num_sections = 5  
        self.section_height = self.window_height // self.num_sections  
        self.perturbations = []  # List to store active perturbations

    def generate_perturbation(self):
     
        section = random.randint(0, self.num_sections - 1)  
        amplitude = random.uniform(0.9, 1.0)  
        frequency = random.uniform(0.5, 2.0)  
        start_time = time.time()  
        duration = random.uniform(0.5, 1)  
        direction = random.choice([-1, 1])  
        return {
            "section": section,
            "amplitude": amplitude,
            "frequency": frequency,
            "start_time": start_time,
            "duration": duration,
            "direction": direction,  
        }

    def get_perturbation_force(self, xh):
  
        perturbation_force = np.array([0.0, 0.0]) 

        current_time = time.time()
        new_perturbations = []

        for pert in self.perturbations:
            elapsed_time = current_time - pert["start_time"]

            if elapsed_time < pert["duration"]:
                
                y_min = pert["section"] * self.section_height
                y_max = (pert["section"] + 1) * self.section_height

                
                if y_min <= xh[1] <= y_max:
                    
                    force_x = (
                        pert["amplitude"]
                        * math.sin(2 * math.pi * pert["frequency"] * elapsed_time)
                        * pert["direction"]  
                    )
                    perturbation_force[0] += force_x

                new_perturbations.append(pert) 

        self.perturbations = new_perturbations  

        return perturbation_force



    def run(self):
        p = self.physics #assign these to shorthand variables for easier use in this function
        g = self.graphics
        cursor=g.effort_cursor
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
            xs = np.array(data[2:4], dtype=int)
            
            grab_object=data[4]
        except socket.timeout:
            pygame.quit() # stop pygame
            raise RuntimeError("Connection lost")

        dt = 0.01  # Time step (s)

    
        if not hasattr(self, "prev_xh"):
            self.prev_xh = xh.copy()


         # k_wall = 1000  
        # f_wall = -k_wall * (self.proxy - xh)/g.window_scale

        # k_table = 1000  
        # f_table = -k_table * (self.proxy - xh)/g.window_scale

        # k_ground = 1000  
        # f_ground = -k_ground * (self.proxy - xh)/g.window_scale

    
        v_h = ((xh - self.prev_xh) / g.window_scale) / dt
        self.b_water = 0.5 
        f_hydro = np.array(-self.b_water * v_h)
        
        #+ self.water_density*self.gravity*xh[1]/400*self.cross_sectional_area
        if random.random() < 0.1:  
            self.perturbations.append(self.generate_perturbation())

        f_wave = self.get_perturbation_force(xh)
        print(type(f_wave))
        

        f_perturbation = -(self.mass* self.gravity- self.water_density * self.displaced_volume* self.gravity) 
        f_perturbation = np.array([0, f_perturbation]) +f_wave

        fe = np.array([0,0], dtype=np.float32)
        fe+=f_perturbation*0.1

        self.send_sock.sendto(fe.tobytes(), ("127.0.0.1", 40001))

        k_spring = 1000 
        b_damping = 0.1  
        dt = 0.01 


        f_vspring = k_spring * (xh - 300) / g.window_scale
        v_h = ((xh - self.prev_xh) / g.window_scale) / dt
        f_damping = b_damping * v_h
        force = f_vspring + f_damping+fe
        xh = g.sim_forces(xh,force,xm,mouse_k=0.5,mouse_b=0.8) #simulate forces with mouse haptics

        
        if(xh[1] >=550):
            xh[1] = 550

        f_perturbation = -(self.mass* self.gravity+ self.water_density*self.gravity*xh[1]/400*self.cross_sectional_area - self.water_density * self.displaced_volume* self.gravity) 
        f_perturbation = np.array([0, f_perturbation])+f_hydro 
        fe = np.array([0,0], dtype=np.float32)
        fe+=f_perturbation
        if (cursor.colliderect(g.object)) and (grab_object):
            g.object.topleft=(cursor.bottomleft[0]-6,cursor.bottomleft[1]-6)
            fe+=np.array([0,-9.8*(self.mass)])
        self.send_sock.sendto(fe.tobytes(), ("127.0.0.1", 40001))

        xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=0.8) #simulate forces with mouse haptics
        pos_phys = g.inv_convert_pos(xh)
        pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
        pB0 = pA0
        pA = (pA[0] / 3, pA[1] / 3)
        pB = (pB[0] / 4, pB[1] / 4)
        pE = (pE[0] / 2, pE[1])
        pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        g.render(pA0,pB0,pA,pB,xh,force,xm,xs)
        
        # if(self.fish_pos[0] >= 550 and self.fish_dir == self.fish_right):
        #     self.fish_mode = -1
        #     self.fish_dir = self.fish_left
        # if(self.fish_pos[0] <=200 and self.fish_dir == self.fish_left):
        #     self.fish_mode = 1
        #     self.fish_dir = self.fish_right
            
        # self.fish_pos[0] += self.fish_mode
        
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
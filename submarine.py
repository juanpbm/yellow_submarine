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
        
        self.fish_left = pygame.transform.scale(pygame.image.load('imgs/fish_left.png'), (40, 20))
        self.fish_right = pygame.transform.scale(pygame.image.load('imgs/fish_right.png'), (40, 20))
        self.fish_dir = self.fish_right
        self.fish_pos = np.array([200,400])
        
        self.fish_mode = 1
        
        self.wall = pygame.Rect(0, 300, 185, 600)
        self.platform = pygame.Rect(600, 400, 800, 600)
        self.table = pygame.Rect(630, 400, 800, 25)
        self.ground = pygame.Rect(185, 575, 415, 50)
        self.dGray = (50,50,50)
        self.bGray = (230,230,230)
        self.dBrown = (92, 64, 51)
        self.Sand = (198, 166, 100)
        self.xc = [300,200]
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
                self.mass=0.5
        self.haptic_width = 48
        self.haptic_height = 48
        self.haptic_length = 48

        # Constants for gravity, buoyancy, and damping
        self.mass = 0.5  
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
        self.window_height = 600  
        self.num_sections = 10  
        self.section_height = self.window_height // self.num_sections  
        self.perturbations = []  # List to store active perturbations

        self.k_fish = 50  

    def generate_perturbation(self):
     
        section = random.randint(0, self.num_sections - 1)  
        amplitude = random.uniform(0.1, 0.6)  
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
        p = self.physics
        g = self.graphics
        g.get_events()
        xs = np.array(g.submarine_pos)
        xh = np.array(g.haptic.center, dtype=np.float64)
        g.erase_screen()
        g.screenHaptics.blit(self.fish_dir, self.fish_pos)
        cursor=g.effort_cursor
        pygame.draw.rect(g.screenHaptics, self.dBrown, self.wall)
        pygame.draw.rect(g.screenHaptics, self.dGray, self.platform)
        pygame.draw.rect(g.screenHaptics, self.bGray, self.table)
        pygame.draw.rect(g.screenHaptics, self.Sand, self.ground)

        try:
            recv_data, _ = self.recv_sock.recvfrom(1024)
            data = np.array(np.frombuffer(recv_data, dtype=np.float64))
            xm = data[:2]
            xm[0] = np.clip(xm[0] + ((g.submarine_pos[0] + 177) - (g.window_size[0] / 2)), -100, g.window_size[0] + 100)
            xm[1] = np.clip((xm[1] * 1.3), 0, g.window_size[1] + 75)
            xm = np.array(xm, dtype=int)
            xs = np.array(data[2:], dtype=int)
            grab_object=data[4]
        except socket.timeout:
            pygame.quit()
            raise RuntimeError("Connection lost")

        dt = 0.01

        if not hasattr(self, "prev_xh"):
            self.prev_xh = xh.copy()



        if random.random() < 0.1:
            self.perturbations.append(self.generate_perturbation())

        f_wave = self.get_perturbation_force(xh)

        f_perturbation = -(self.mass * self.gravity - self.water_density * self.displaced_volume * self.gravity)
        f_perturbation = np.array([0, f_perturbation]) + f_wave

        fe = np.array([0, 0], dtype=np.float32)
        fe += f_perturbation 
        
        haptic_rect = pygame.Rect(xh[0], xh[1], self.haptic_width, self.haptic_height)

        if haptic_rect.colliderect(self.wall):
            if xh[0] < self.wall.right: 
                xh[0] = self.wall.right


        if haptic_rect.colliderect(self.platform):
            if xh[1] < self.platform.left: 
                xh[1] = self.platform.left - self.haptic_width
            elif xh[1] > self.platform.right - self.haptic_width: 
                xh[1] = self.platform.right
            if xh[0] < self.platform.top: 
                xh[0] = self.platform.top - self.haptic_height
            elif xh[0] > self.platform.bottom - self.haptic_height: 
                xh[0] = self.platform.bottom

        # Table collision (all sides)
        if haptic_rect.colliderect(self.table):
            if xh[1] < self.table.left:  
                xh[1] = self.table.left - self.haptic_width
            elif xh[1] > self.table.right - self.haptic_width:  
                xh[1] = self.table.right
            if xh[0] < self.table.top:  
                xh[0] = self.table.top - self.haptic_height
            elif xh[0] > self.table.bottom - self.haptic_height:  
                xh[0] = self.table.bottom
        
        if haptic_rect.colliderect(self.ground):
            if xh[1] > self.ground.top - self.haptic_height:  
                xh[1] = self.ground.top - self.haptic_height

        if haptic_rect.colliderect(pygame.Rect(self.fish_pos[0], self.fish_pos[1], 40, 20)):
            penetration_depth = max(0, self.fish_pos[0] + 40 - haptic_rect.left)
            fe[0] += (self.k_fish * penetration_depth/600)

        v_h = ((xh - self.prev_xh) / g.window_scale) / dt
        self.b_water = 0.5
        f_hydro = np.array(-self.b_water * v_h)
        fe+=fe+f_hydro
        

        k_spring = 20
        b_damping = 2
        dt = 0.01

        f_vspring = k_spring * (xh-self.xc) / g.window_scale
        if not hasattr(self, "prev_vh"):
            self.prev_vh = v_h.copy()
        v_h = ((xh - self.prev_xh) / g.window_scale) / dt

        a_h = ((v_h - self.prev_vh) / g.window_scale) / dt
        f_damping = b_damping * v_h
        
        f_inertia = self.mass* a_h
        if (cursor.colliderect(g.object)) and (grab_object):
            g.object.topleft=(cursor.bottomleft[0]-6,cursor.bottomleft[1]-6)
            fe+=np.array([0,-9.8*(self.mass)])
            fe+=f_inertia
        force = f_vspring + f_damping + fe+f_inertia
        self.send_sock.sendto(fe.tobytes(), ("127.0.0.1", 40001))
        self.prev_xh = xh.copy()
        self.prev_vh = v_h.copy()
        xh = g.sim_forces(xh, force, xm, mouse_k=0.5, mouse_b=0.8)
        print(f_inertia,f_wave)
        # Ensure haptic device stays within the window bounds
        xh[0] = np.clip(xh[0], 0, g.window_size[0] - self.haptic_width)
        xh[1] = np.clip(xh[1], 0, g.window_size[1] - self.haptic_height)

        pos_phys = g.inv_convert_pos(xh)
        pA0, pB0, pA, pB, pE = p.derive_device_pos(pos_phys)
        pB0 = pA0
        pA = (pA[0] / 3, pA[1] / 3)
        pB = (pB[0] / 4, pB[1] / 4)
        pE = (pE[0] / 2, pE[1])
        pA0, pB0, pA, pB, xh = g.convert_pos(pA0, pB0, pA, pB, pE)
        g.render(pA0, pB0, pA, pB, xh, force, xm, xs)

        if self.fish_pos[0] >= 550 and self.fish_dir == self.fish_right:
            self.fish_mode = -1
            self.fish_dir = self.fish_left
        if self.fish_pos[0] <= 200 and self.fish_dir == self.fish_left:
            self.fish_mode = 1
            self.fish_dir = self.fish_right

        self.fish_pos[0] += self.fish_mode
        
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
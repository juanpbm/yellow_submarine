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
    def __init__(self, render_haptics = True):
        self.max_time = 2 * 60 # "T_minutes" * 60s = T_seconds 
        self.physics = Physics(hardware_version=0, connect_device=False) #setup physics class. Returns a boolean indicating if a device is connected
        self.graphics = Graphics(False, max_time=self.max_time) #setup class for drawing and graphics.
        self.render_haptics = render_haptics
        # Set up UDP sockets
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(("127.0.0.1", 40002))
        self.recv_sock.setblocking(False)
        
        self.fish_left = pygame.transform.scale(pygame.image.load('imgs/fish_left.png'), (40, 20))
        self.fish_right = pygame.transform.scale(pygame.image.load('imgs/fish_right.png'), (40, 20))
        self.fish_dir = self.fish_right
        self.fish_pos = np.array([200,400])
        
        self.fish_mode = 1
        
        self.xc = [300,200]
        #self.wall = pygame.Rect(xc, yc, 300, 300)

        # Objects
        self.object_grabbed = False
        self.objects_in_target = []
        self.object_mass = 0
        self.grabbed_object = ""

        # Wait for at least one message from the master. Only continue once something is received.
        print("Waiting for operator communication")
        i = 0
        while True:
            for event in pygame.event.get():  # Handle events to keep the window responsive
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
            try: 
                self.send_sock.sendto(np.array([0,0,0], dtype=np.float32).tobytes(), ("127.0.0.1", 40001))
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

        # Init Metrics variables
        self.passed = False
        self.first = False
        self.damage = 0 # percentage
        self.path_length = 0 # pixels
        self.init_time = time.time() # seconds

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
    
    def Grab_object(self, grab_object):
        g = self.graphics
        cursor=g.effort_cursor

        if grab_object:
            if not self.object_grabbed:
                if (cursor.colliderect(g.anchor))  and (not cursor.colliderect(g.chest)) and ( not cursor.colliderect(g.bottle)) and "anchor" not in self.objects_in_target:
                        g.anchor.topleft=(cursor.bottomleft[0],cursor.bottomleft[1]-12)
                        self.object_grabbed = True
                        self.grabbed_object = "anchor"
                        self.object_mass = 10.0
                elif (cursor.colliderect(g.chest))  and  (not cursor.colliderect(g.anchor)) and ( not cursor.colliderect(g.bottle)) and "chest" not in self.objects_in_target:
                        g.chest.topleft=(cursor.bottomleft[0],cursor.bottomleft[1]-12)
                        self.object_grabbed = True
                        self.grabbed_object = "chest"
                        self.object_mass = 5.0
                elif (cursor.colliderect(g.bottle))  and  (not cursor.colliderect(g.chest)) and ( not cursor.colliderect(g.anchor)) and "bottle" not in self.objects_in_target:
                        g.bottle.topleft=(cursor.bottomleft[0],cursor.bottomleft[1]-10)
                        self.object_grabbed = True
                        self.grabbed_object = "bottle"
                        self.object_mass = 1.0
                elif not ((cursor.colliderect(g.chest)) or (cursor.colliderect(g.anchor)) or (cursor.colliderect(g.anchor))):
                    self.object_grabbed = False
                    self.grabbed_object = ""
                    self.object_mass = 0.0
                    msg = np.array([2], dtype=np.float32)
                    self.send_sock.sendto(msg.tobytes(), ("127.0.0.1", 40001))
                    time.sleep(0.02)
            else:
                if self.grabbed_object == "anchor":
                    g.anchor.topleft = (cursor.bottomleft[0], cursor.bottomleft[1]-12)
                    if g.anchor.colliderect(g.table):
                        self.objects_in_target.append("anchor")
                        self.object_grabbed = False
                        self.grabbed_object = ""
                        self.object_mass = 0.0
                        msg = np.array([2], dtype=np.float32)
                        self.send_sock.sendto(msg.tobytes(), ("127.0.0.1", 40001))
                        time.sleep(0.02)

                elif self.grabbed_object == "chest":
                    g.chest.topleft = (cursor.bottomleft[0], cursor.bottomleft[1]-12)
                    if g.chest.colliderect(g.table):
                        self.objects_in_target.append("chest")
                        self.object_grabbed = False
                        self.grabbed_object = ""
                        self.object_mass = 0.0
                        msg = np.array([2], dtype=np.float32)
                        self.send_sock.sendto(msg.tobytes(), ("127.0.0.1", 40001))
                        time.sleep(0.02)


                elif self.grabbed_object == "bottle":
                    g.bottle.topleft = (cursor.bottomleft[0], cursor.bottomleft[1]-10)
                    if g.bottle.colliderect(g.table):
                        self.objects_in_target.append("bottle")
                        self.object_grabbed = False
                        self.grabbed_object = ""
                        self.object_mass = 0.0
                        msg = np.array([2], dtype=np.float32)
                        self.send_sock.sendto(msg.tobytes(), ("127.0.0.1", 40001))
                        time.sleep(0.02)
        else:
            self.object_grabbed = False
            self.grabbed_object = ""
            self.object_mass = 0.0
        
    def run(self):
        p = self.physics
        g = self.graphics
        g.get_events()
        xs = np.array(g.submarine_pos)
        xh = np.array(g.haptic.center, dtype=np.float64) #make sure fe is a numpy array
        g.erase_screen()
        
        # Receive and process messages
        try:
            # Receive position
            recv_data, _ = self.recv_sock.recvfrom(64)
            data = np.array(np.frombuffer(recv_data, dtype=np.float64))
            xm = data[:2]
            xm[0] = np.clip(xm[0] + ((g.submarine_pos[0] + 177) - (g.window_size[0] / 2)), -100, g.window_size[0] + 100)
            xm[1] = np.clip((xm[1] * 1.3), 0, g.window_size[1] + 75)
            xm = np.array(xm, dtype=int)
            xs = np.array(data[2:4], dtype=int)
            grab_object=data[4]
        # If there is a timeout the connection with the operator has been lost
        except socket.timeout:
            pygame.quit()
            raise RuntimeError("Connection lost")
        
        # Grabbing Objects
        self.Grab_object(grab_object)

        if self.render_haptics:
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

            if haptic_rect.colliderect(pygame.Rect(self.fish_pos[0], self.fish_pos[1], 40, 20)):
                penetration_depth = max(0, self.fish_pos[0] + 40 - haptic_rect.left)
                fe[0] += (self.k_fish * penetration_depth/600)

            v_h = ((xh - self.prev_xh) / g.window_scale) / dt
            self.b_water = 0.5
            f_hydro = np.array(-self.b_water * v_h)
            fe += f_hydro
            
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
            if (self.object_grabbed):
                fe += np.array([0,-9.8*(0)])
                fe += self.object_mass * a_h
            fe = f_vspring + f_damping + fe + f_inertia

        # if the haptics are disabled send 0 force
        else: 
            fe = np.array([0,0], dtype=np.float32)
        
        # Send force the first 0 is the type of the message informing the operator that it is a force
        msg = np.array([0, *fe], dtype=np.float32)
        self.send_sock.sendto(msg.tobytes(), ("127.0.0.1", 40001))

        self.prev_xh = xh.copy()
        self.prev_vh = v_h.copy()
        # Process the forces and position to render the environment
        xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=0.8) #simulate forces with mouse haptics
        # Ensure haptic device stays within the window bounds
        xh[0] = np.clip(xh[0], 0, g.window_size[0] - self.haptic_width)
        xh[1] = np.clip(xh[1], 0, g.window_size[1] - self.haptic_height)
        pos_phys = g.inv_convert_pos(xh)
        pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
        # Scale the physics results for submarine size
        pB0 = pA0
        pA = (pA[0] / 3, pA[1] / 3)
        pB = (pB[0] / 4, pB[1] / 4)
        pE = (pE[0] / 2, pE[1])
        pA0, pB0, pA, pB, xh = g.convert_pos(pA0, pB0, pA, pB, pE)
        g.render(pA0, pB0, pA, pB, xh, fe, xm, xs, self.init_time, self.damage)  # Render environment

        if self.fish_pos[0] >= 550 and self.fish_dir == self.fish_right:
            self.fish_mode = -1
            self.fish_dir = self.fish_left
        if self.fish_pos[0] <= 200 and self.fish_dir == self.fish_left:
            self.fish_mode = 1
            self.fish_dir = self.fish_right

        self.fish_pos[0] += self.fish_mode
        
        # Skip First iteration as the distance should be 0
        if not self.first:
            self.first = True
        # Get distance traveled from the previous frame to update the path length
        else:
            self.path_length += np.linalg.norm(self.prev_xh - np.ceil(xh))

        # Check if game is over
        if (time.time() - self.init_time >= self.max_time or self.damage >= 100):
            self.passed = False
            raise RuntimeError("Game Finished")
        elif len(self.objects_in_target) == 1:
            self.passed = True
            raise RuntimeError("Game Finished")

        
    def close(self, show_exit_screen):
        # Get Metrics
        play_again = False
        if show_exit_screen: 
            final_time = time.time() - self.init_time
            results = np.array([1, self.passed, final_time, self.path_length, self.damage], dtype=np.float32)
            # Send metrics the first element is 1, the type of the message informing the operator that it is a metrics message
            self.send_sock.sendto(results.tobytes(), ("127.0.0.1", 40001))
            # print metrics to make sure they were recieved correctly
            print(f"Passed: {self.passed}, Time: {final_time:.2f}, Path_length: {self.path_length:.2f}, damage: {self.damage:.0f}")
            # save results to file 
            with open("results.txt", "a") as file:
                file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}, Passed: {self.passed}, Time: {final_time:.2f}, Path_length: {self.path_length:.2f}, Damage: {self.damage:.0f} \n")
            
            # Wait for message from the operator to play again or not
            start_time = time.time()
            while True:
                try:
                    recv_data, _ = self.recv_sock.recvfrom(1024)
                    data = np.array(np.frombuffer(recv_data, dtype=bool))
                    if(data[0] == 1):
                        play_again = data[1]
                        break
                except :
                    # add a 2min time-out to prevent an infinite loop.
                    if (time.time() - start_time > 60):
                        break
                    continue
        # Close used resources
        self.graphics.close()
        self.physics.close()
        self.send_sock.close()
        self.recv_sock.close()
        return play_again



if __name__=="__main__":

    try:
        render_haptics = sys.argv[1].lower() == "true"
    except:
        render_haptics = True
    try:
        name = sys.argv[2]
    except:
        name = "unknown"
        
    play_again = True
    with open("results.txt", "a") as file:
            file.write(f"Participant Name: {name}, Haptic: {render_haptics}\n")
        
    while play_again:
        submarine = Submarine(render_haptics)
        try:
            while True:
                submarine.run()
        except RuntimeError as e:
            if str(e) == "Game Finished":
                play_again = submarine.close(True)
                submarine = None
                continue

        play_again = submarine.close(False)
        submarine = None


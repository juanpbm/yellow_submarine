# -*- coding: utf-8 -*-
import sys
import numpy as np
import pygame
import socket
import random
import time
import math
import traceback

from Physics import Physics
from Graphics_submarine import Graphics


class EndGame(Exception):
    """Exception raised for custom error in the application."""

    def __init__(self, message, error_code=0):
        self.message = message
        super().__init__(self.message)
        self.error_code = error_code

    def __str__(self):
        return f"{self.message} (Code: {self.error_code})"


class Submarine:
    def __init__(self, render_haptics = True):
        self.max_time = 2 * 60 # "T_minutes" * 60s = T_seconds 
        self.physics = Physics(hardware_version=0, connect_device=False) #setup physics class. Returns a boolean indicating if a device is connected
        self.graphics = Graphics(False, num_fish=2, max_time=self.max_time) #setup class for drawing and graphics.
        self.render_haptics = render_haptics

        # Set up UDP sockets
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(("127.0.0.1", 40002))
        self.recv_sock.setblocking(False)
        
        # Current
        self.current_on = False
        
        # Fish
        self.fish_left = pygame.transform.scale(pygame.image.load('imgs/fish_left.png'), (40, 20))
        self.fish_right = pygame.transform.scale(pygame.image.load('imgs/fish_right.png'), (40, 20))
        self.fish_dir = self.fish_right
        self.fish_pos = np.array([200,400])
        
        self.fish_mode = 1
        
        self.xc = self.graphics.haptic.center
        self.collision_act = 0

        # Objects interaction
        self.object_grabbed = False
        self.objects_in_target = []
        self.object_mass = 0
        self.grabbed_object = ""

        self.collision_platform = 0
        self.collision_wall = 0
        self.collision_anchor = 0
        self.collision_chest = 0
        self.collision_bottle = 0

        # Haptic dim anf mass 
        self.mass=0.5
        self.prev_vh = 0

        # TODO: use the ones from fro graphics 
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
        self.num_sections = 5
        self.section_height = self.window_height // self.num_sections  
        self.perturbations = []  # List to store active perturbations

        self.k_fish = 50 

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
        
        # Init Metrics variables
        self.passed = False
        self.first = False
        self.damage = 0 # percentage
        self.path_length = 0 # pixels
        self.init_time = time.time() # seconds

    def generate_perturbation(self):
     
        section = random.randint(2, self.num_sections - 1)  
        amplitude = random.uniform(3, 4)  
        frequency = random.uniform(0.5, 2.0)  
        start_time = time.time()  
        duration = random.uniform(2.0, 3.0) 
        direction = random.choice([-1, 1])  
        return {
            "section": section,
            "amplitude": amplitude,
            "frequency": frequency,
            "start_time": start_time,
            "duration": duration,
            "direction": direction,  
        }

    def get_perturbation_force(self, xh, g):
        perturbation_force = np.array([0.0, 0.0]) 
        current_time = time.time()
        new_perturbations = []

        for pert in self.perturbations:
            elapsed_time = current_time - pert["start_time"]
            duration = pert["duration"]

            if elapsed_time < duration:
                self.current_on = True
                
                y_min = pert["section"] * self.section_height
                y_max = (pert["section"] + 1) * self.section_height

                g.current_pos[1] = y_min
                
                if y_min <= xh[1] <= y_max:
                    # Calculate force magnitude
                    force_x = (
                        pert["amplitude"]
                        * math.sin(2 * math.pi * pert["frequency"] * elapsed_time)
                        * pert["direction"]
                    )

                    # Smoothly reduce force to zero in the last 0.1 seconds
                    if elapsed_time > (duration - 0.2):
                        remaining_time = duration - elapsed_time
                        scale_factor = max(0.0, remaining_time / 0.1)  # Linear ramp down
                        force_x = 0

                    perturbation_force[0] += force_x

                new_perturbations.append(pert)
            else:
                self.current_on = False
                g.current_pos[1] = 1200  # Reset position outside the screen

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
                        self.object_mass = 1.0
                elif (cursor.colliderect(g.chest))  and  (not cursor.colliderect(g.anchor)) and ( not cursor.colliderect(g.bottle)) and "chest" not in self.objects_in_target:
                        g.chest.topleft=(cursor.bottomleft[0],cursor.bottomleft[1]-12)
                        self.object_grabbed = True
                        self.grabbed_object = "chest"
                        self.object_mass = 0.5
                elif (cursor.colliderect(g.bottle))  and  (not cursor.colliderect(g.chest)) and ( not cursor.colliderect(g.anchor)) and "bottle" not in self.objects_in_target:
                        g.bottle.topleft=(cursor.bottomleft[0],cursor.bottomleft[1]-10)
                        self.object_grabbed = True
                        self.grabbed_object = "bottle"
                        self.object_mass = 0.1
                elif not ((cursor.colliderect(g.chest)) or (cursor.colliderect(g.anchor)) or (cursor.colliderect(g.anchor))):
                    self.drop_object()
            else:
                if self.grabbed_object == "anchor":
                    g.anchor.topleft = (cursor.bottomleft[0], cursor.bottomleft[1]-12)
                    if g.anchor.colliderect(g.table):
                        self.objects_in_target.append("anchor")
                        self.drop_object()

                elif self.grabbed_object == "chest":
                    g.chest.topleft = (cursor.bottomleft[0], cursor.bottomleft[1]-12)
                    if g.chest.colliderect(g.table):
                        self.objects_in_target.append("chest")
                        self.drop_object()

                elif self.grabbed_object == "bottle":
                    g.bottle.topleft = (cursor.bottomleft[0], cursor.bottomleft[1]-10)
                    if g.bottle.colliderect(g.table):
                        self.objects_in_target.append("bottle")
                        self.drop_object()
        else:
            self.object_grabbed = False
            self.grabbed_object = ""
            self.object_mass = 0.0

    def drop_object(self):  
        self.object_grabbed = False
        self.grabbed_object = ""
        self.object_mass = 0.0
        msg = np.array([2], dtype=np.float32)
        self.send_sock.sendto(msg.tobytes(), ("127.0.0.1", 40001))
        time.sleep(0.02) 

    def calc_forces(self, xh):
        g = self.graphics


        dt = 0.01

        if not hasattr(self, "prev_xh"):
            self.prev_xh = xh.copy()
        f_wave = np.array([0, 0], dtype=np.float32)
        f_fish = np.array([0, 0], dtype=np.float32)
        if random.random() < 0.1 and self.current_on == False:
            self.perturbations.append(self.generate_perturbation())
        f_wave = self.get_perturbation_force(xh,g)
        depth = xh[1] / g.window_scale  # Depth in meters (y-axis increases downward)
        f_hydrostatic = self.water_density * self.gravity * depth * self.cross_sectional_area
        f_hydrostatic = np.array([0, f_hydrostatic])  # Apply only in the y-axis


        f_perturbation = -(self.mass * self.gravity - self.water_density * self.displaced_volume * self.gravity)
        f_perturbation = np.array([0, f_perturbation]) + f_hydrostatic + f_wave


        fe = np.array([0, 0], dtype=np.float32)
        fe += f_perturbation 
        
        haptic_rect = pygame.Rect(xh[0], xh[1], self.haptic_width, self.haptic_height)
        # TODO: FIX FORCE FISH
        # TODO: FIX FORCE FISH
        if self.collision_act > 0:
            penetration_depth = max(0, self.collision_act + 40 - haptic_rect.left)
            f_fish[0] = (self.k_fish * penetration_depth/600)
            fe += f_fish
            # Reset collision state after applying force
            self.collision_act = 0  # <-- Add this line

        # print(fe,"2")
        v_h = ((xh - self.prev_xh) / g.window_scale) / dt
        self.b_water = 0.5
        f_hydro = np.array(-self.b_water * v_h)
    
        fe += f_hydro

        a_h = ((v_h - self.prev_vh) / g.window_scale) / dt

        f_inertia = self.mass* a_h
        object_inertia = np.array([0.0,0.0], dtype=np.float32)
        if (self.object_grabbed):
            object_inertia += np.array([0.0, -9.8*(self.object_mass)])
            object_inertia += self.object_mass * a_h
        fe = fe + f_inertia + object_inertia
        
        self.prev_vh = v_h.copy()
        return fe

    def run(self):
        p = self.physics
        g = self.graphics
        g.get_events()
        xs = np.array(g.submarine_pos)
        xh = np.array(g.haptic.center, dtype=np.float64) # Make sure fe is a numpy array
        g.erase_screen()
        
        # Receive and process messages
        try:
            # Receive position
            recv_data, _ = self.recv_sock.recvfrom(64)
            data = np.array(np.frombuffer(recv_data, dtype=np.float64))
            #print("message_recieved",data)
            # Rescale xm[0] from -1 to 1 to 0 to 800
            xm = data[:2]
            xm[0] = np.clip((xm[0] + ((g.submarine_pos[0] + 177) - (g.window_size[0]/2))), -100, g.window_size[0] + 100)
            xm[1] = np.clip((xm[1] * 1.3), 0, g.window_size[1] + 75)
            xm = np.array(xm, dtype=int)
 
            xm = np.array(xm, dtype=int)
            xs = np.array(data[2:4], dtype=int)
            grab_object=data[4]
            
        # If there is a timeout the connection with the operator has been lost
        except socket.timeout:
            pygame.quit()
            raise EndGame("Connection lost", 1)
        
        # Grabbing Objects
        self.Grab_object(grab_object)

        fe = self.calc_forces(xh)
        self.prev_xh = xh.copy()

        # Process the forces and position to render the environment
        xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=0.8) # Simulate forces with mouse haptics
        
        g.render_fish()

        # Check collision with fish
        self.collision_act = 0  # Reset collision state every frame
        for n, f in enumerate(g.fish):
            if f == 1:              
                # Check distance from fish to each line
                if (g.effort_cursor.colliderect(g.fish_rect[n]) or 
                    (xh[1] >= g.fish_pos[n][1] and (np.abs(g.fish_pos[n][0] - xh[0])<50))):
                    self.collision_act = g.fish_pos[n][0]  # Set collision state
                    self.damage += 0.1
                
        # Ensure haptic device stays within the window bounds
        xh[0] = np.clip(xh[0], 0, g.window_size[0] - self.haptic_width)
        xh[1] = np.clip(xh[1], 0, g.window_size[1] - self.haptic_height)
        
        pos_phys = g.inv_convert_pos(xh)
        pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) # Derive the pantograph joint positions given some endpoint position

        # Scale the physics results for submarine size
        pB0 = pA0
        pA = (pA[0] / 3, pA[1] / 3)
        pB = (pB[0] / 4, pB[1] / 4)
        pE = (pE[0] / 2, pE[1])

        pA0, pB0, pA, pB, xh = g.convert_pos(pA0, pB0, pA, pB, pE)

        # Check collision with platform on the right and limit the handle position accordingly
        if ((xh[0]+ 20)>g.platform.topleft[0]) and ((xh[1]+25)>g.platform.topleft[1]) and (self.collision_platform==0):
            if ((xh[0]+ 20)-g.platform.topleft[0]) > ((xh[1]+25)-g.platform.topleft[1]):
                self.collision_platform=1
            else:
                self.collision_platform=2    
        elif (((xh[1]+25)<(g.platform.topleft[1])) or (xh[0] + 20)<(g.platform.topleft[0])) and (self.collision_platform!=0):
            self.collision_platform=0
        elif(self.collision_platform==1):
            xh[1]=g.platform.topleft[1]-25
            self.damage += 0.3
            difference=xm[1] - xh[1]  
            wall_force = self.force_wall(difference,0.1) 
            fe+=np.array([0,wall_force])
        elif(self.collision_platform==2):
            xh[0]=g.platform.topleft[0]-20
            self.damage += 0.3 
            difference=xm[0]-xh[0]
            wall_force = self.force_wall(difference) 
            fe+=np.array([wall_force,0])
            

        #Check collision with wall on the left and limit the handle position accordingly
        if ((xh[0] - 20)<g.wall.topright[0]) and ((xh[1]+25)>g.wall.topright[1]) and self.collision_wall==0:
            if ( - ((xh[0] - 20)-g.wall.topright[0]) > ((xh[1]+25)-g.wall.topright[1])):
                self.collision_wall=1
            else:
                self.collision_wall=2        
        elif (((xh[1]+25)<(g.wall.topright[1])) or (xh[0] - 20)>(g.wall.topright[0])) and (self.collision_wall!=0):
            self.collision_wall=0
        elif(self.collision_wall==1):
            xh[1]=g.wall.topright[1]-25
            self.damage += 0.3 
            difference=xm[1] - xh[1]  
            wall_force = self.force_wall(difference,0.1) 
            fe+=np.array([0,wall_force])
        elif(self.collision_wall==2):
            xh[0]=g.wall.topright[0] + 20
            self.damage += 0.3 
            difference=xh[0] - xm[0]
            wall_force = self.force_wall(difference) 
            fe+=np.array([-wall_force,0])

        # Check collision with the different objects only while an object has not been grabbed and limit the handle position accordingly
        if (self.object_grabbed==False):
            xh, self.collision_anchor= self.collision_object(xh,g.anchor, self.collision_anchor)
            xh, self.collision_chest= self.collision_object(xh,g.chest, self.collision_chest)
            xh, self.collision_bottle= self.collision_object(xh,g.bottle, self.collision_bottle,5)
           
        # Send force the first 0 is the type of the message informing the operator that it is a force
        if self.render_haptics:
            msg = np.array([0, *fe], dtype=np.float32)
        else: 
            msg = np.array([0, 0, 0], dtype=np.float32)


        self.send_sock.sendto(msg.tobytes(), ("127.0.0.1", 40001))

        g.render(pA0, pB0, pA, pB, xh, fe, xm, xs, self.init_time, self.damage)  # Render environment
        # fe = 0
        # Skip First iteration as the distance should be 0
        if not self.first:
            self.first = True
        # Get distance traveled from the previous frame to update the path length
        else:
            self.path_length += np.linalg.norm(self.prev_xh - np.ceil(xh))

        # Check if game is over
        if (time.time() - self.init_time >= self.max_time or self.damage >= 100):
            self.passed = False
            raise EndGame("Game Finished", 0)
        elif len(self.objects_in_target) == 3:
            self.passed = True
            raise EndGame("Game Finished", 0)

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
                    self.send_sock.settimeout(0.5)
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
        self.physics.close()
        self.graphics.close()
        self.send_sock.close()
        self.recv_sock.close()
        return play_again
    
    def collision_object(self,xh, object, collision_specific_object, offset=0 ):
        #TODO: add damage for colliding with walls, drop object.
        # Check if the limits of the handle respect to xh collision with the object
        if (((xh[0]+ 20)>object.topleft[0]) and ((xh[0]- 20)<object.topright[0]) ) and ((xh[1]+12 + offset)>object.topleft[1]) and (collision_specific_object==0):
                # Check if the collision is from top, left or right
                if (((xh[0]+ 20)-object.topleft[0]) > ((xh[1]+12 - offset)-object.topleft[1])):
                    # This condition only happens when xh is further away from left side than the top, meaning that when there was a collision was from the top or right side
                    if ( -((xh[0]- 20)-object.topright[0]))  > ((xh[1]+12 + offset)-object.topleft[1]):
                         # Collision from top
                        collision_specific_object=1
                    else:
                        # Collision from right side
                        collision_specific_object=3
                else:
                    # This condition only happens when xh is further away from top than the left side, meaning that when there was a collision was from the left side
                    collision_specific_object=2  
        # Check if the handle no longer collides with the object
        elif ( ((xh[1]+12 + offset)<(object.topleft[1])) or ((xh[0] + 20)<(object.topleft[0])) or ((xh[0] - 20)>(object.topright[0]))) and (collision_specific_object!=0) :
            # No collision (default)
            collision_specific_object=0
        # Adjust the handle accordingly
        elif(collision_specific_object==1):
            xh[1]=object.topleft[1]-12 - offset
        elif(collision_specific_object==2):
            xh[0]=object.topleft[0]-20
        elif(collision_specific_object==3):
            xh[0]=object.topright[0] + 20

        return xh, collision_specific_object

    def force_wall(self,difference, k=0.2):
        if (difference<50):
            difference=50
        elif (difference<60):
            difference=100
            k=0.3
        elif (difference<70):
            difference=150
            k=0.4

        elif(difference<90):
            difference=500
            k=0.8
        elif(difference>=90):
            difference=1000
            k=1

        return difference*k

if __name__=="__main__":

    try:
        name = sys.argv[1]
    except:
        name = "unknown"
    try:
        render_haptics = sys.argv[2].lower() == "true"
    except:
        render_haptics = True
        
    play_again = True
    with open("results.txt", "a") as file:
            file.write(f"Participant Name: {name}, Haptic: {render_haptics}\n")
        
    while play_again:
        submarine = Submarine(render_haptics)
        try:
            while True:
                submarine.run()
        except EndGame as e:
            print(f"Game stopped with exception: {e}")
            play_again = submarine.close(True)
            submarine = None
            if(play_again == False):
                pygame.quit()
                sys.exit(1)
        except Exception as e:
            print("Unhandled exception occurred:")
            traceback.print_exc()
            break
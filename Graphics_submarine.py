# -*- coding: utf-8 -*-
import pygame
import numpy as np
import sys 
import os
import time 

class Graphics:
    def __init__(self,device_connected,num_fish=0,window_size=(800,600), max_time=1.0):
        self.device_connected = device_connected
        self.max_time = max_time
        #initialize pygame window
        self.window_size = window_size #default (800, 600)
        os.environ['SDL_VIDEO_WINDOW_POS'] = "20,100" # Where in the screen the window pops up
        pygame.init()
        self.window = pygame.display.set_mode((window_size[0], window_size[1]))
        pygame.display.set_caption('Yellow Submarine')

        self.screenHaptics = pygame.Surface(self.window_size)
        self.xc = self.screenHaptics.get_rect().centerx
        self.yc =self.screenHaptics.get_rect().centery

        ##add nice icon from https://www.cleanpng.com/png-yellow-submarine-clip-art-submarine-biomass-vector-1902493/
        self.icon = pygame.image.load('imgs/yellow_submarine_left.png')
        pygame.display.set_icon(self.icon)

        ##add text on top to debugToggle the timing and forces
        self.font = pygame.font.Font('freesansbold.ttf', 18)

        pygame.mouse.set_visible(True)     ##Hide cursor by default. 'm' toggles it
         
        ##set up the on-screen debugToggle
        self.text = self.font.render('Submarine', True, (0, 0, 0),(255, 255, 255))
        self.textRect = self.text.get_rect()
        self.textRect.topleft = (10, 10) 

        ##initialize "real-time" clock
        self.clock = pygame.time.Clock()
        self.FPS = 100   #in Hertz

        # Define some colors
        self.cWhite = (255,255,255)
        self.cDarkblue = (36,90,190)
        self.cLightblue = (0,176,240)
        self.cRed = (255,0,0)
        self.cBlack = (0,0,0)
        self.cGreen = (0,255,0)
        self.cOrange = (255,100,0)
        self.cYellow = (255,255,0)
        self.dGray = (50,50,50)
        self.bGray = (230,230,230)
        self.dBrown = (92, 64, 51)
        self.Sand = (198, 166, 100)
        self.dGray = (50,50,50)
        self.bGray = (230,230,230)
        self.dBrown = (92, 64, 51)
        self.Sand = (198, 166, 100)
        
        # Image taken from https://www.cleanpng.com/png-industrial-robotic-arm-in-action-8194578/
        self.hhandle = pygame.image.load('imgs/hand.png') 
        
        self.haptic_width = 48
        self.haptic_height = 48
        self.haptic  = pygame.Rect(*self.screenHaptics.get_rect().center, 0, 0).inflate(self.haptic_width, self.haptic_height)
        self.effort_cursor  = pygame.Rect(*self.haptic.center, 0, 0).inflate(self.haptic_width, self.haptic_height) 
        self.colorHaptic = self.cOrange ##color of the wall

        # Make submarine
        # image taken from https://www.cleanpng.com/png-yellow-submarine-clip-art-submarine-biomass-vector-1902493/
        self.submarine_left = pygame.transform.scale(pygame.image.load('imgs/yellow_submarine_left.png'), (150, 100))
        self.submarine_right = pygame.transform.scale(pygame.image.load('imgs/yellow_submarine_right.png'), (150, 100))
        self.submarine_dir = self.submarine_left

        ####Pseudo-haptics dynamic parameters, k/b needs to be <1
        self.sim_k = 0.5 #0.1#0.5       ##Stiffness between cursor and haptic display
        self.sim_b = 0.8 #1.5#0.8       ##Viscous of the pseudohaptic display
        
        # initial position
        self.window_scale = 3000 #2500 #pixels per meter
        self.submarine_pos = (int(self.window_size[0]/2.0 - 80), 10)
        self.device_origin = (int(self.window_size[0]/2.0), 110)
        
        # Targets (Images taken from the links next to each image)
        self.anchor_img = pygame.image.load('imgs/anchor.png') # https://www.cleanpng.com/png-anchor-anchor-rope-boat-water-7781743/
        self.chest_img = pygame.image.load('imgs/chest.png') # https://www.cleanpng.com/png-icon-wooden-chest-hasp-keyhole-lid-brown-wooden-ch-7956299/
        self.bottle_img = pygame.image.load('imgs/bottle.png') # https://www.cleanpng.com/png-red-ribbon-clean-minimalist-image-of-a-bottle-with-7945288/
        self.anchor = self.anchor_img.get_rect(topleft=(500, 510))
        self.chest = self.chest_img.get_rect(topleft=(50, 263))
        self.bottle = self.bottle_img.get_rect(topleft=(200, 555))

        # Background elements
        self.wall = pygame.Rect(0, 300, 185, 600)
        self.platform = pygame.Rect(600, 400, 800, 600)
        self.table = pygame.Rect(630, 400, 800, 25)
        self.ground = pygame.Rect(185, 575, 415, 50)

        self.show_linkages = True
        
        # Currents
        self.current_pos = np.array([0,1200])
        self.current = pygame.transform.scale(pygame.image.load('imgs/current_line.png'), (800, 120))
        self.current_rect = self.current.get_rect(topleft=self.current_pos)
        
        # Fish
        self.fish_left = pygame.transform.scale(pygame.image.load('imgs/fish_left.png'), (40, 20))
        self.fish_right = pygame.transform.scale(pygame.image.load('imgs/fish_right.png'), (40, 20))

        self.fish = [0,0,0]

        self.fish_dir = np.array([self.fish_right, self.fish_left, self.fish_right])
        self.fish_pos = [[200,500],[500,400],[400,550]]
        self.fish_mode = np.array([1,-1, 1])
        
        fish1 =self.fish_dir[0].get_rect(topleft=self.fish_pos[0])
        fish2 =self.fish_dir[1].get_rect(topleft=self.fish_pos[1]) 
        fish3 =self.fish_dir[2].get_rect(topleft=self.fish_pos[2]) 
        
        self.fish_rect = np.array([fish1, fish2, fish3])
        
        if(num_fish >= 1):
            self.fish[0] = 1
        if(num_fish >= 2):
            self.fish[1] = 1
        if(num_fish >= 3):
            self.fish[2] = 1

    def convert_pos(self,*positions):
        #invert x because of screen axes
        # 0---> +X
        # |
        # |
        # v +Y
        # Scale Device

        converted_positions = []
        for physics_pos in positions:
            x = self.device_origin[0]-physics_pos[0]*self.window_scale
            y = self.device_origin[1]+physics_pos[1]*self.window_scale
            converted_positions.append([x,y])
        if len(converted_positions)<=0:
            return None
        elif len(converted_positions)==1:
            return converted_positions[0]
        else:
            return converted_positions
        return [x,y]
    
    def inv_convert_pos(self,*positions):
        #convert screen positions back into physical positions
        converted_positions = []
        for screen_pos in positions:
            x = (self.device_origin[0]-screen_pos[0])/self.window_scale
            y = (screen_pos[1]-self.device_origin[1])/self.window_scale
            converted_positions.append([x,y])
        if len(converted_positions)<=0:
            return None
        elif len(converted_positions)==1:
            return converted_positions[0]
        else:
            return converted_positions
        return [x,y]
        
    def get_events(self):
        #########Process events  (Mouse, Keyboard etc...)#########
        events = pygame.event.get()
        keyups = []
        for event in events:
            if event.type == pygame.QUIT: #close window button was pressed
                sys.exit(0) #raises a system exit exception so any Finally will actually execute
            elif event.type == pygame.KEYUP:
                keyups.append(event.key)
        
        return keyups

    def sim_forces(self,pE,f,pM,mouse_k=None,mouse_b=None):
        #simulated device calculations
        if mouse_k is not None:
            self.sim_k = mouse_k
        if mouse_b is not None:
            self.sim_b = mouse_b
        if not self.device_connected:
            pP = self.haptic.center
            #pM is where the mouse is
            #pE is where the position is pulled towards with the spring and damping factors
            #pP is where the actual haptic position ends up as
            diff = np.array(( pM[0]-pE[0],pM[1]-pE[1]) )
            #diff = np.array(( pM[0]-pP[0],pM[1]-pP[1]) )
            
            scale = self.window_scale/1e3
            scaled_vel_from_force = np.array(f)*scale/self.sim_b
            vel_from_mouse_spring = (self.sim_k/self.sim_b)*diff
            dpE = vel_from_mouse_spring - scaled_vel_from_force
            #dpE = -dpE
            #if diff[0]!=0:
            #    if (diff[0]+dpE[0])/diff[0]<0:
            #        #adding dpE has changed the sign (meaning the distance that will be moved is greater than the original displacement
            #        #prevent the instantaneous velocity from exceeding the original displacement (doesn't make physical sense)
            #        #basically if the force given is so high that in a single "tick" it would cause the endpoint to move back past it's original position...
            #        #whatever thing is exerting the force should basically be considered a rigid object
            #        dpE[0] = -diff[0]
            #if diff[1]!=1:
            #    if (diff[1]+dpE[1])/diff[1]<0:
            #        dpE[1] = -diff[1]
            if abs(dpE[0])<1:
                dpE[0] = 0
            if abs(dpE[1])<1:
                dpE[1] = 0
            pE = np.round(pE+dpE) #update new positon of the end effector
            
            #Change color based on effort
            cg = 255-np.clip(np.linalg.norm(self.sim_k*diff/self.window_scale)*255*20,0,255)
            cb = 255-np.clip(np.linalg.norm(self.sim_k*diff/self.window_scale)*255*20,0,255)
            self.effort_color = (255,cg,cb)
        return pE

    def erase_screen(self):
        # plot hight map
        self.screenHaptics.fill(self.cWhite) #erase the haptics surface
        pixels = np.zeros((self.window_size[1], self.window_size[0], 3), dtype=np.uint8)  # Create empty image
        Y_color = np.linspace(255, 100, self.window_size[1])[:, None]  # Gradient from 255 (top) to 0 (bottom)

        # Apply the gradient to the blue channel
        pixels[:, :, 0] = 0  
        pixels[:, :, 1] = 0
        pixels[:, :, 2] = Y_color

        # Convert array to surface
        surface = pygame.surfarray.make_surface(pixels.swapaxes(0, 1))
        self.screenHaptics.blit(surface, (0, 0))
    
    def render(self,pA0,pB0,pA,pB,pE,f,pM, pS, st, dam):
        ###################Render the Haptic Surface###################
        #set new position of items indicating the endpoint location
        self.screenHaptics.blit(self.current, self.current_pos)
        
        self.haptic.center = pE #the hhandle image and effort square will also use this position for drawing
        self.effort_cursor.center = self.haptic.center

        # Draw Object
        self.screenHaptics.blit(self.anchor_img, self.anchor)
        self.screenHaptics.blit(self.chest_img, self.chest)
        self.screenHaptics.blit(self.bottle_img, self.bottle)

        # Draw Background elements
        pygame.draw.rect(self.screenHaptics,self.dBrown,self.wall)
        pygame.draw.rect(self.screenHaptics,self.dGray,self.platform)
        pygame.draw.rect(self.screenHaptics,self.bGray,self.table)
        pygame.draw.rect(self.screenHaptics,self.Sand,self.ground)

        ######### Robot visualization ###################
        if self.show_linkages:
            pygame.draw.lines(self.screenHaptics, self.cYellow, False,[pA0,pA],5)
            pygame.draw.lines(self.screenHaptics, self.cYellow, False,[pB0,pB],5)
            pygame.draw.lines(self.screenHaptics, self.cYellow, False,[pA,pE],5)
            pygame.draw.lines(self.screenHaptics, self.cYellow, False,[pB,pE],5)
            
            for p in ( pA0,pB0,pA,pB,pE):
                pygame.draw.circle(self.screenHaptics, (0, 0, 0),p, 5)
                pygame.draw.circle(self.screenHaptics, (200, 200, 200),p, 2)
        
        ### Hand visualisation
        hand_pos = (self.effort_cursor[0], self.effort_cursor[1] + 10)
        self.screenHaptics.blit(self.hhandle, hand_pos)
        
        # Submarine 
        if self.submarine_pos[0] < pS[0]:
            self.submarine_dir = self.submarine_right
        elif self.submarine_pos[0] > pS[0]:
            self.submarine_dir = self.submarine_left
            
        self.submarine_pos = tuple(pS)
        self.device_origin = (pS[0] + 75, pS[1] + 90)
        self.screenHaptics.blit(self.submarine_dir, self.submarine_pos)

        # Display time
        remaining_time = max(0, self.max_time - (time.time() - st))
        time_text = f"T: {int(remaining_time//60)}:{int(remaining_time%60)}"
        time_font = pygame.font.Font('freesansbold.ttf', 20)
        time_text = time_font.render(time_text, True, (255, 255, 255), (0, 0, 0))
        time_text_rect = time_text.get_rect()
        time_text_rect.bottomleft = (5, 600)
        self.screenHaptics.blit(time_text, time_text_rect)

        #Display damage
        damage_text = "Health: "
        damage_font = pygame.font.Font('freesansbold.ttf', 20)
        damage_text = damage_font.render(damage_text, True, (255, 255, 255), (0, 0, 0))
        damage_text_rect = damage_text.get_rect()
        damage_text_rect.bottomleft = (615, 599)
        self.screenHaptics.blit(damage_text, damage_text_rect)
        pygame.draw.rect(self.screenHaptics, (100, 100, 100), (695, 573, 100, 25), border_radius=5)
        # Draw progress fill (green)
        pygame.draw.rect(self.screenHaptics, (255 * ((min(dam,100)/100)), 255 * (1-(min(dam,100)/100)), 0), (695, 573, 100 * (1-(min(dam,100)/100)), 25), border_radius=5)

        ##Fuse it back together
        self.window.blit(self.screenHaptics, (0,0))

        pygame.display.flip()    
        ##Slow down the loop to match FPS
        self.clock.tick(self.FPS)
    
    def show_loading_screen(self, i=0):
        # Show Intro message
        if (i % 15000 == 0):
            self.window.fill(self.cBlack)
            dots_cycle = ["", ".", "..", "...", "....", ".....", "......", ".......","........", ".........",".........."]
            init_text = "WAITING FOR COMMUNICATION: " + dots_cycle[((i//15000) % 11)]
            init_font = pygame.font.Font('freesansbold.ttf', 35)
            init_text = init_font.render(init_text, True, (0, 255, 0), (0, 0, 0))
            init_text_rect = init_text.get_rect()
            init_text_rect.topleft = (50, 300)
            self.window.blit(init_text, init_text_rect)
            pygame.display.flip()
        return 0

    # FISH
    def render_fish(self):
        
        for n, f in enumerate(self.fish):
            if(f == 1):
                self.screenHaptics.blit(self.fish_dir[n], self.fish_pos[n])
                
                if self.fish_pos[n][0] >= 550 and self.fish_mode[n] == 1:
                    self.fish_mode[n] = -1
                    self.fish_dir[n] = self.fish_left
                elif self.fish_pos[n][0] <= 200 and self.fish_mode[n] == -1:
                    self.fish_mode[n] = 1
                    self.fish_dir[n] = self.fish_right
                    
                self.fish_pos[n][0] += self.fish_mode[n]
                pos_new = [0,0]
                pos_new[0] = self.fish_pos[n][0] 
                pos_new[1] = self.fish_pos[n][1]

                fish_new =self.fish_dir[n].get_rect(topleft=pos_new) 
                
                self.fish_rect[n] = fish_new

    def close(self):
        pygame.display.quit()
        pygame.quit()

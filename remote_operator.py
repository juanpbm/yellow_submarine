# -*- coding: utf-8 -*-
import sys
import numpy as np
import pygame
import socket

from Physics import Physics
from Graphics_operator import Graphics
from submarine import EndGame

class RemoteOperator:
    def __init__(self):
        self.physics = Physics(hardware_version=3) #setup physics class. Returns a boolean indicating if a device is connected
        self.device_connected = self.physics.is_device_connected() #returns True if a connected haply device was found
        self.graphics = Graphics(self.device_connected) #setup class for drawing and graphics.
        
        # Set up socket for UDP communication 
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind(("127.0.0.1", 40001))
        self.recv_sock.setblocking(False)
        self.grab_object= 0

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
            if key == 32: # Space bar pressed
                if (self.grab_object== 0):
                    self.grab_object= 1
                else:
                    self.grab_object= 0
        if keypressed[pygame.K_LEFT]:
            self.xs[0] = np.clip(self.xs[0] - 1, 0, 800 - 150)
        if keypressed[pygame.K_RIGHT]:
            self.xs[0] = np.clip(self.xs[0] + 1, 0, 800 - 150)

        # Send Position from the haptic device or mouse and the submarine position
        # Send Position from the haptic device or mouse and the submarine position
        message = np.array([xh, self.xs,(self.grab_object,0)])
        self.send_sock.sendto(message.tobytes(), ("127.0.0.1", 40002))

        # Receive Force feedback
        last_message = np.array([0,0,0])
        try:
            while True:
                try:
                    # Empty buffer TODO: check that forces are still ok
                    while True:  # Keep reading until the buffer is empty
                        self.recv_sock.settimeout(0.01)
                        recv_data, _ = self.recv_sock.recvfrom(1024)
                        last_message = recv_data  # Store the latest message
                except socket.timeout:
                    self.recv_sock.settimeout(1)
                    break  # Exit loop when no more data is available
            # process the last message
            rcv_msg = np.frombuffer(last_message, dtype=np.float32)
            # is the first element is 0 it is a force message
            if (int(rcv_msg[0]) == 0 ):
                # TODO: Scale the feedback to make it stable
                fe = np.array(rcv_msg[1:], dtype=np.float32)
            # if the first element is a 1 is a metrics and game over message
            else:
                passed, final_time, path_length, damage = rcv_msg[1:]
                # Show game over screen with received metrics
                play_again = self.graphics.show_exit_screen(passed, final_time, path_length, damage)
                # send play again message to submarine
                snd_msg = np.array([play_again], dtype=bool)
                self.send_sock.sendto(snd_msg.tobytes(), ("127.0.0.1", 40002))

                # if not play again end the operator
                if not play_again:
                    raise EndGame("Game Over", 2)
                # if play again show the loading screen and wait for user input to start and reset submarine position
                g.erase_screen()
                g.show_loading_screen()
                self.xs = np.array([320, 10], dtype=np.float64) 

                run = True
                while run:
                    keyups, _, _= self.graphics.get_events()
                    for key in keyups:
                        if key== pygame.K_SPACE:
                            run = False 
        except socket.timeout:
            pygame.quit()
            raise EndGame("Connection lost", 1)

        
        # Update previous position
        self.prev_xh = xh.copy()
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
        self.graphics.close()
        self.physics.close()
        self.send_sock.close()
        self.recv_sock.close()

if __name__=="__main__":
    operator = RemoteOperator()
    try:
        while True:
            operator.run()
    except EndGame as e:
        print(f"Game stopped with exception: {e}")
        if(e.error_code == 1):
            pygame.quit()
            sys.exit(1)
    finally:
        operator.close()
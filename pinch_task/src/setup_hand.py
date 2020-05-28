import sys
import argparse

import numpy as np
import pandas as pd
import datetime
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import (AntialiasAttrib, PointLight, Spotlight, TextNode,
                          TransparencyAttrib)
from panda3d.core import loadPrcFileData, WindowProperties
from panda3d.core import MeshDrawer2D, Vec4
from panda3d.core import WindowProperties
from src.machine import HandSetupMachine
from toon.input import MpDevice
from src.hand import RightHand
from toon.input.clock import mono_clock
from src.timers import CountdownTimer

from direct.gui.DirectGui import DirectEntry, DirectButton
from threading import Timer
import os.path



class HandS(ShowBase, HandSetupMachine):
    def __init__(self,id,session,hand, wrist,trial,exp):
        self.sub_id = id
        self.trialid= trial
        self.session = session
        self.hand = hand
        self.wrist= wrist
        self.exp = exp
        
        self.DATA_DIR = 'data'
        
        ShowBase.__init__(self)
        HandSetupMachine.__init__(self)
        props = WindowProperties()
        props.setTitle('Hand Setup')
        
        self.session_dir = os.path.join(self.DATA_DIR,'exp_'+self.exp,self.sub_id,self.session,self.wrist,self.hand,'Setup_'+self.trialid)
        if not os.path.exists(self.session_dir):
          print('Making new folders: ' + self.session_dir)
          os.makedirs(self.session_dir)
        
        self.win.requestProperties(props)
        self.render.setAntialias(AntialiasAttrib.MMultisample)
        self.render.setShaderAuto()  # allows shadows
        self.setFrameRateMeter(True)
        self.space = False
        self.dev = MpDevice(RightHand(calibration_files=['calibs/cal_mat_15.mat',  # thumb
                                        'calibs/cal_mat_31.mat',
                                        'calibs/cal_mat_13.mat',
                                        'calibs/cal_mat_21.mat',
                                        'calibs/cal_mat_8.mat'], clock=mono_clock.get_time))
        #self.finger = int(finger) * 3  # offset
        #self.f2 = int(finger)
        self.disableMouse()
        self.countdown_timer = CountdownTimer()

       # self.table = pd.read_table(trial_table)  # trial table
        self.setup_lights()
        self.setup_camera()
        self.load_models()
        

        # add tasks (run every frame)
        taskMgr.add(self.get_user_input, 'move' )
        taskMgr.add(self.update_feedback_bar, 'update_feedback_bar',sort=1)    
        self.accept('space', self.space_on)  # toggle a boolean somewhere 
        self.accept('escape', self.clean_up)

        self.med_data = None
        self.noise1 = 0.0
        self.noise2 = 0.0
        self.noise3 = 0.0
        self.noise4 = 0.0
        self.noise5 = 0.0
        
        self.trial_counter=0
        self.logging = False
        self.text = OnscreenText(text='Not recording.', pos=(-0.8, 0.7),
                                scale=0.08, fg=(1, 1, 1, 1),
                                bg=(0, 0, 0, 1), frame=(0.2, 0.2, 0.8, 1),
                                align=TextNode.ACenter)      
        self.button = DirectButton(
        text='Log data', scale=0.05, command=self.log_and_print, pos=(-0.9, 0, 0.9))
        self.button = DirectButton(
        text='Stop logging', scale=0.05, command=self.stop_logging, pos=(-0.9, 0, 0.8))


    def stop_logging(self):
        self.logging = False
        self.stoplog_text()
        
    def log_and_print(self):
        self.logging = True
        self.trial_counter+=1
        self.log_text()
        self.t = Timer(30,self.incrementfile)
        self.t.start()              

    def incrementfile(self):
        if self.logging:
            self.t.cancel()
            self.log_and_print()

    def load_models(self):
        self.cam2dp.node().getDisplayRegion(0).setSort(-20)
        OnscreenImage(parent=self.cam2dp, image='models/background.jpg')

        self.bgtext = OnscreenText(pos=(-0.8, 0.8),
                                 scale=0.08, fg=(1, 1, 1, 1),
                                 bg=(0, 0, 0, 1), frame=(0.2, 0.2, 0.8, 1),
                                 align=TextNode.ACenter)
        self.bgtext.reparentTo(self.aspect2d)

        self.errorlevel = OnscreenText(text='10%', pos=(-0.99, -0.80),
                                 scale=0.08, fg=(1, 1, 1, 1),
                                 bg=(0, 0, 0, 1), frame=(0.2, 0.2, 0.8, 1),
                                 align=TextNode.ACenter)
        self.halfscale = OnscreenText(text='50%', pos=(-0.99, -0.4),
                                 scale=0.08, fg=(1, 1, 1, 1),
                                 bg=(0, 0, 0, 1), frame=(0.2, 0.2, 0.8, 1),
                                 align=TextNode.ACenter)
        self.fullscale = OnscreenText(text='100%', pos=(-0.99, 0.10),
                                 scale=0.08, fg=(1, 1, 1, 1),
                                 bg=(0, 0, 0, 1), frame=(0.2, 0.2, 0.8, 1),
                                 align=TextNode.ACenter)                                                  
        self.text = OnscreenText(text='Neutral position error', pos=(-0.08, 0.8),
                                 scale=0.08, fg=(1, 1, 1, 1),
                                 bg=(0, 0, 0, 1), frame=(0.2, 0.2, 0.8, 1),
                                 align=TextNode.ACenter)
        self.text.reparentTo(self.aspect2d)

        self.move_feedback = MeshDrawer2D()
        self.move_feedback.setBudget(100)  # this is the number of triangles needed (two per rect)
        feed_node = self.move_feedback.getRoot()
        feed_node.setTwoSided(True)
        feed_node.setDepthWrite(False)
        feed_node.setTransparency(True)
        feed_node.setBin('fixed', 0)
        feed_node.setLightOff(True)
        self.node = feed_node
        self.node.reparentTo(self.render2d)

    def setup_lights(self):
        pl = PointLight('pl')
        pl.setColor((1, 1, 1, 1))
        plNP = self.render.attachNewNode(pl)
        plNP.setPos(-0.5, -0.5, 0.5)
        self.render.setLight(plNP)

        pos = [[[0, 0, 3], [0, 0, -1]],
               [[0, -3, 0], [0, 1, 0]],
               [[-3, 0, 0], [1, 0, 0]]]
        for i in pos:
            dl = Spotlight('dl')
            dl.setColor((1, 1, 1, 1))
            dlNP = self.render.attachNewNode(dl)
            dlNP.setPos(*i[0])
            dlNP.lookAt(*i[1])
            dlNP.node().setShadowCaster(True)
            self.render.setLight(dlNP)

    def setup_camera(self):
        self.cam.setPos(-2, -4, 2)
        self.cam.lookAt(0, 0, 0)

    def get_user_input(self, task):
        error,data = self.dev.read()
        
        if data is not None:
            data *= 0.001
            if self.med_data is None:
                self.med_data = np.median(data, axis=0)
                
            self.data = data
            
            noise1 = np.sqrt(np.square(data[-1, 0] - self.med_data[0]) +
                                 np.square(data[-1, 1] - self.med_data[1]) +
                                 np.square(data[-1, 2] - self.med_data[2]))
            noise2 = np.sqrt(np.square(data[-1, 3] - self.med_data[3]) +
                                 np.square(data[-1, 4] - self.med_data[4]) +
                                 np.square(data[-1, 5] - self.med_data[5]))
            noise3 = np.sqrt(np.square(data[-1, 6] - self.med_data[6]) +
                                 np.square(data[-1, 7] - self.med_data[7]) +
                                 np.square(data[-1, 8] - self.med_data[8]))
            noise4 = np.sqrt(np.square(data[-1, 9] - self.med_data[9]) +
                                 np.square(data[-1, 10] - self.med_data[10]) +
                                 np.square(data[-1, 11] - self.med_data[11]))
            noise5 = np.sqrt(np.square(data[-1, 12] - self.med_data[12]) +
                                 np.square(data[-1, 13] - self.med_data[13]) +
                                 np.square(data[-1, 14] - self.med_data[14]))
            
                                 
            self.noise1=noise1   
            self.noise2=noise2 
            self.noise3=noise3   
            self.noise4=noise4 
            self.noise5=noise5

            if self.logging:
                self.log_file_name = os.path.join(self.session_dir, "Setup_"+self.sub_id+"_"+self.session+"_"+self.hand+"_"+str(self.trial_counter)+".txt")   
                with open(self.log_file_name, 'ab') as f:
                 np.savetxt(f, self.data, fmt='%10.5f', delimiter=',')
            else:
                pass
        
                 
        return task.cont

    def update_feedback_bar(self, task):
        self.move_feedback.begin()
        self.move_feedback.rectangle_raw(-0.5, -0.9, 0.1, self.noise1, 0, 0, 0, 0, Vec4(0.9, .2, .1, 1))
        self.move_feedback.rectangle_raw(-0.525, -0.9, 0.15, 0.015, 0, 0, 0, 0, Vec4(1, 1, 1, 1))
        self.move_feedback.rectangle_raw(-0.625, 0.1, 1.2, 0.015, 0, 0, 0, 0, Vec4(1, 1, 1, 1))
        self.move_feedback.rectangle_raw(-0.625, -0.4, 0.07, 0.015, 0, 0, 0, 0, Vec4(1, 1, 1, 1))
        self.move_feedback.rectangle_raw(-0.3, -0.9, 0.1, self.noise2, 0, 0, 0, 0, Vec4(0.9, .2, .1, 1))
        self.move_feedback.rectangle_raw(-0.325, -0.9, 0.15, 0.015, 0, 0, 0, 0, Vec4(1, 1, 1, 1))
        self.move_feedback.rectangle_raw(-0.1, -0.9, 0.1, self.noise3, 0, 0, 0, 0, Vec4(0.9, .2, .1, 1))
        self.move_feedback.rectangle_raw(-0.125, -0.9, 0.15, 0.015, 0, 0, 0, 0, Vec4(1, 1, 1, 1))
        self.move_feedback.rectangle_raw(0.1, -0.9, 0.1, self.noise4, 0, 0, 0, 0, Vec4(0.9, .2, .1, 1))
        self.move_feedback.rectangle_raw(0.075, -0.9, 0.15, 0.015, 0, 0, 0, 0, Vec4(1, 1, 1, 1))
        self.move_feedback.rectangle_raw(0.3, -0.9, 0.1, self.noise5, 0, 0, 0, 0, Vec4(0.9, .2, .1, 1))
        self.move_feedback.rectangle_raw(0.275, -0.9, 0.15, 0.015, 0, 0, 0, 0, Vec4(1, 1, 1, 1))
        self.move_feedback.rectangle_raw(-0.625, -0.80, 1.2, 0.015, 0, 0, 0, 0, Vec4(1, 1, 1, 1))
        self.move_feedback.end()
        return task.cont

    def space_on(self):
     self.space = True
     
        

    def update_state(self, task):
        self.step()
        return task.cont

    # state machine functions
    def wait_for_space(self):
        return self.space

    def log_text(self):
        self.text.setText('Now logging...')

    def stoplog_text(self):
        self.text.setText('Paused logging!')

    
    def time_elapsed(self):
        return self.countdown_timer.elapsed() < 0

    def post_text(self):
        self.text.setText('Relax.')

    def reset_baseline(self):
       self.med_data = None
      
        
    def clean_up(self):
        sys.exit()

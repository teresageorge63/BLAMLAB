import sys
import numpy as np
import os.path
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.core import (AntialiasAttrib, PointLight, Spotlight,
                          TextNode, TransparencyAttrib)
from panda3d.core import CollisionTraverser
from panda3d.core import CollisionNode, CollisionHandlerPusher, CollisionHandlerEvent
from panda3d.core import CollisionSphere, CollisionBox, CollisionTube, Point3
from panda3d.core import WindowProperties

from collections import Counter

from src.machine import GripStateMachine
from toon.input import MpDevice
from toon.input.clock import mono_clock
from src.hand import RightHand
from src.handpos import *
from src.timers import CountdownTimer
import yaml
import math
import time

import serial
from serial.tools import list_ports
import struct

class PinchTask(ShowBase, GripStateMachine):
    DATA_DIR = 'data'
    
    def __init__(self, id, session, hand, block, mode, wrist):
        ShowBase.__init__(self)
        GripStateMachine.__init__(self)
        base.disableMouse()
        wp = WindowProperties()
        wp.setSize(1920,1080)
        wp.setFullscreen(True)
        base.win.requestProperties(wp)

        self.sub_id = str(id)
        self.sess_id = str(session)
        self.hand = str(hand)
        self.block = str(block)
        self.mode = str(mode)
        self.wrist = str(wrist)
        
        self.prev_blk = os.path.join(self.DATA_DIR,'exp_1',self.sub_id,self.sess_id,self.wrist,self.hand,"B0")
        if self.wrist == 'pron':
            self.table = np.loadtxt('src/pinch_task/trialtable_pron.csv',dtype='str',delimiter=',',skiprows=1)
        elif self.wrist == 'flex':
            self.table = np.loadtxt('src/pinch_task/trialtable_flex.csv',dtype='str',delimiter=',',skiprows=1)
        else:
            raise NameError('Wrist position not found')

        try:
            self.prev_table = np.loadtxt(os.path.join(self.prev_blk, 'final_targets.csv'),dtype='str',delimiter=',',skiprows=1)
            indices = {}
            for i in range(self.prev_table.shape[0]):
                indices[self.prev_table[i,1]] = int(self.prev_table[i,0])-1
            for i in range(self.table.shape[0]):
                self.table[i,11] = self.prev_table[indices[self.table[i,1].strip()],11]
                self.table[i,12] = self.prev_table[indices[self.table[i,1].strip()],12]
                self.table[i,13] = self.prev_table[indices[self.table[i,1].strip()],13]
        except:
            print('Previous target file not found')
        
        self.table = np.array([[item.strip() for item in s] for s in self.table])

        ##################################################
        #only use rows relevant to this block
        #HARDCODED! NOTE IN LOG SHEET
        spec_table = []
        for i in range(self.table.shape[0]):
            if int(self.block)%4 == 0:
                if "(p)" in self.table[i,2]:
                    spec_table.append(self.table[i])
            elif int(self.block)%4 == 1:
                if "(t)" in self.table[i,2]:
                    spec_table.append(self.table[i])
            elif int(self.block)%4 == 2:
                if "(s)" in self.table[i,2]:
                    spec_table.append(self.table[i])
            elif int(self.block)%4 == 3:
                if "(t+s)" in self.table[i,2]:
                    spec_table.append(self.table[i])
        ###################################################
        self.table = np.array(spec_table)

        self.session_dir = os.path.join(self.DATA_DIR,'exp_1',self.sub_id,self.sess_id,self.wrist,self.hand)
        self.subjinfo = self.sub_id + '_' + self.sess_id + '_' + self.hand + '_log.yml'
        self.p_x,self.p_y,self.p_a = GET_POS(self.session_dir,self.subjinfo,self.hand,self.wrist)

        self.rotmat = ROT_MAT(self.p_a,self.hand)

        self.setup_text()
        self.setup_lights()
        self.setup_camera()
        
        self.trial_counter = 0
        self.load_models()
        self.load_audio()
        self.update_trial_command()
        self.countdown_timer = CountdownTimer()
        self.hold_timer = CountdownTimer()

        self.cTrav = CollisionTraverser()
        self.chandler = CollisionHandlerEvent()
        self.chandler.addInPattern('%fn-into-%in')
        self.chandler.addAgainPattern('%fn-again-%in')
        self.chandler.addOutPattern('%fn-outof-%in')
        self.attachcollnodes()

        taskMgr.add(self.read_data, 'read')
        for i in range(5):
            taskMgr.add(self.move_player, 'move%d' % i, extraArgs = [i], appendTask=True)
        taskMgr.add(self.log_data, 'log data')
        taskMgr.add(self.update_state, 'update_state', sort=1)

        self.accept('space', self.space_on)
        self.accept('escape', self.clean_up)
        self.space = False
        self.statenum = list()

        self.max_time = 20
        self.med_data = None

        self.grip_dir = os.path.join(self.DATA_DIR,'exp_1',self.sub_id,self.sess_id,self.wrist,self.hand,"B"+self.block)
        if not os.path.exists(self.grip_dir):
           print('Making new folders: ' + self.grip_dir)
           os.makedirs(self.grip_dir)

        self.dev = MpDevice(RightHand(calibration_files=['calibs/cal_mat_15.mat',  # thumb
                                               'calibs/cal_mat_31.mat',
                                               'calibs/cal_mat_8.mat',
                                               'calibs/cal_mat_21.mat',
                                               'calibs/cal_mat_13.mat'], clock=mono_clock.get_time))

        self.init_ser()

    ############
    #SET UP HUD#
    ############
    def setup_text(self):
        #OnscreenImage(parent=self.cam2dp, image='models/background.jpg')
        self.bgtext = OnscreenText(text='Not recording.', pos=(-0.8, 0.8),
                                 scale=0.08, fg=(0, 0, 0, 1),
                                 bg=(1, 1, 1, 1), frame=(0.2, 0.2, 0.8, 1),
                                 align=TextNode.ACenter)
        self.bgtext.reparentTo(self.aspect2d)

        self.dirtext = OnscreenText( pos=(-0.6, 0.65),
                                 scale=0.08, fg=(0, 0, 0, 1),
                                 bg=(1, 1, 1, 1), frame=(0.2, 0.2, 0.8, 1),
                                 align=TextNode.ACenter)
        self.dirtext.reparentTo(self.aspect2d)

    ##########################
    #SET UP SCENE AND PLAYERS#
    ##########################
    def setup_lights(self):
        pl = PointLight('pl')
        pl.setColor((1, 1, 1, 1))
        plNP = self.render.attachNewNode(pl)
        plNP.setPos(-10, -10, 10)
        self.render.setLight(plNP)
        pos = [[[0, 0, 50], [0, 0, -10]],
               [[0, -50, 0], [0, 10, 0]],
               [[-50, 0, 0], [10, 0, 0]]]
        for i in pos:
            dl = Spotlight('dl')
            dl.setColor((1, 1, 1, 1))
            dlNP = self.render.attachNewNode(dl)
            dlNP.setPos(*i[0])
            dlNP.lookAt(*i[1])
            dlNP.node().setShadowCaster(False)
            self.render.setLight(dlNP)

    def setup_camera(self):
        self.cam.setPos(0, -4, 12)
        self.cam.lookAt(0, 2, 0)
        self.camLens.setFov(90)

    def load_models(self):
        self.back_model = self.loader.loadModel('models/back')
        self.back_model.setScale(10, 10, 10)
        if self.hand == "Left":
            self.back_model.setH(90)
        self.back_model.reparentTo(self.render)

        self.player_offsets = [[self.p_x[0]-5, self.p_y[0]+3, 0], [self.p_x[1]-2.5, self.p_y[1]+4.5, 0], [self.p_x[2], self.p_y[2]+5, 0],
                                [self.p_x[3]+2.5, self.p_y[3]+4.5, 0], [self.p_x[4]+5, self.p_y[4]+3, 0]]
        self.p_col =[[0,0,250],[50,0,200],[125,0,125],[200,0,50],[250,0,0]]
        if self.hand == 'Left':
            self.p_col = self.p_col[::-1]

        self.players = list()
        self.contacts = list()        
        for counter, value in enumerate(self.player_offsets):
            self.players.append(self.loader.loadModel('models/target'))
            self.contacts.append(False)

            self.players[counter].setPos(*value)
            self.players[counter].setScale(0.2, 0.2, 0.2)
            self.players[counter].setColorScale(
                self.p_col[counter][0]/255, self.p_col[counter][1]/255, self.p_col[counter][2]/255, 1)
            self.players[counter].reparentTo(self.render)
            self.players[counter].show()

        self.target_select()

    def load_audio(self):
        self.pop = self.loader.loadSfx('audio/Blop.wav')
        self.buzz = self.loader.loadSfx('audio/Buzzer.wav')


    ############################
    #SET UP COLLISION MECHANICS#
    ############################
    def attachcollnodes(self):
        for i in range(5):
            self.fromObject = self.players[i].attachNewNode(CollisionNode('colfromNode'+str(i)))
            self.fromObject.node().addSolid(CollisionSphere(0,0,0,1))
            self.cTrav.addCollider(self.fromObject, self.chandler)

        for i in range(5):
            self.accept('colfromNode%d-into-colintoNode' % i, self.collide1,[i])
            self.accept('colfromNode%d-again-colintoNode' % i, self.collide2,[i])
            self.accept('colfromNode%d-outof-colintoNode' % i, self.collide3,[i])

    def collide1(self,f,collEntry):
        if f in self.highlighted_indices:
            self.players[f].setColorScale(0,1,0,0)
            self.tar.setColorScale(0.2,0.2,0.2,1)
            self.tar.setAlphaScale(0.7)
            self.contacts[f] = True
            taskMgr.doMethodLater(self.delay,self.too_long,'too_long%d' % f,extraArgs = [f])
            self.sendsig(1,f,100)
                
    def collide2(self,f,collEntry):
        if f in self.highlighted_indices:
            dist = np.sqrt(self.distances[f][1]^2+self.distances[f][2]^2+self.distances[f][3]^2)
            self.sendsig(2,f,int(10/dist)+100)
        for i in self.highlighted_indices:
            if self.contacts[i] == False:
                return
        taskMgr.remove('too_long%d' % f)

    def collide3(self,f,collEntry):
        taskMgr.remove('too_long%d' % f)
        self.reset_fing(f)
        self.tar.setColorScale(0.1,0.1,0.1,1)
        self.tar.setAlphaScale(0.7)

    def too_long(self,f):
        self.reset_fing(f)
        self.tar.setColorScale(0.5,0.2,0.2,1)
        self.tar.setAlphaScale(0.7)

    def reset_fing(self,f):
        self.players[f].setColorScale(
                self.p_col[f][0]/255, self.p_col[f][1]/255, self.p_col[f][2]/255, 1)
        self.contacts[f] = False
        self.sendsig(3,f,0)

    ###############
    #TARGET THINGS#
    ###############
    def show_target(self):
        self.target_select()
        self.intoObject = self.tar.attachNewNode(CollisionNode('colintoNode'))

        if self.table[self.trial_counter,7] == "sphere":
            self.intoObject.node().addSolid(CollisionSphere(0,0,0,1))
        elif self.table[self.trial_counter,7] == "cylinder":
            self.intoObject.node().addSolid(CollisionTube(0,0,-2,0,0,2,1))
        else:
            raise NameError("No such collision type")

        self.tar.show()

        #hide players not related to target
        for i in range(5):
            if i not in self.highlighted_indices:
                self.players[i].hide()
        
    def target_select(self):
        self.tgtscx=float(self.table[self.trial_counter,14])
        self.tgtscy=float(self.table[self.trial_counter,15])
        self.tgtscz=float(self.table[self.trial_counter,16])
        tgttsx=float(self.table[self.trial_counter,11])
        tgttsy=float(self.table[self.trial_counter,12])
        tgttsz=float(self.table[self.trial_counter,13])
        tgtrx=float(self.table[self.trial_counter,17])
        tgtry=float(self.table[self.trial_counter,18])
        tgtrz=float(self.table[self.trial_counter,19])
        if self.hand == 'Left':
            tgttsx *= -1
            tgtrx *= -1

        self.static_task = (str(self.table[self.trial_counter,5]) == "True")
        self.target_model = str(self.table[self.trial_counter,6])
        self.highlighted_indices=[int(s)-1 for s in self.table[self.trial_counter,4].split(' ')]
        if self.hand == 'Left':
            self.highlighted_indices=[4-i for i in self.highlighted_indices]

        #NOTE:this position finding is present in all three tasks
        #     it is somewhat hacky and can be improved upon
        self.tgtposx = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][[-2,-1],0]) + tgttsx
        self.tgtposy = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][[0,1],1]) + tgttsy
        if len(self.highlighted_indices) > 3: #for sphere, return to just average of all fingers
            self.tgtposx = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][:,0]) + tgttsx
            #self.tgtposy = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][:,1])
        self.tgtposz = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][:,2]) + tgttsz

        self.tar = self.loader.loadModel(self.target_model)
        self.tar.setScale(self.tgtscx,self.tgtscy,self.tgtscz)
        self.tar.setPos(self.tgtposx,self.tgtposy,self.tgtposz)
        self.tar.setHpr(tgtrx,tgtry,tgtrz)
        self.tar.setColorScale(0.1, 0.1, 0.1, 1)
        self.tar.setAlphaScale(0.7)
        self.tar.setTransparency(TransparencyAttrib.MAlpha) 
        self.tar.reparentTo(self.render)
        self.tar.hide()

        self.delay=float(self.table[self.trial_counter,8])
        self.loc_angle=math.radians(float(self.table[self.trial_counter,9]))
        self.invf=float(self.table[self.trial_counter,10])
        
        self.distances = [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]

    ##############
    #MOVE FINGERS#
    ##############
    def read_data(self,task):
        error, data = self.dev.read()
        if data is not None:
            data *= 0.001
            self.ts = data.time
            data = np.dot(data,self.rotmat)
            self.data = data
            if self.med_data is None:
                self.med_data = np.median(data, axis=0)

            if self.space:
                self.statenum.extend(([self.checkstate()])*len(data.time))
                
        return task.cont
        
    def move_player(self,p,task):
        if self.data is not None :
            k = p*3
            new_x = 10*np.mean(self.data[-1,k]) + self.player_offsets[p][0] - 10*self.med_data[k]
            new_y = 10*np.mean(self.data[-1,k + 1]) + self.player_offsets[p][1] - 10*self.med_data[k + 1]
            new_z = 10*np.mean(self.data[-1,k + 2]) + self.player_offsets[p][2] - 10*self.med_data[k + 2]

            #make sure digits do not cross each other
            if ((p in range(1,3) and p+1 in self.highlighted_indices and new_x > self.players[p+1].getX())
                or (p in range(2,4) and p-1 in self.highlighted_indices and new_x < self.players[p-1].getX())):
                    new_x = self.players[p].getX()
            
            #make sure digits do not cross into target
            if self.space == True and p in self.highlighted_indices:
                self.distances[p][0] = new_x - self.tar.getX()
                self.distances[p][1] = new_y - self.tar.getY()
                self.distances[p][2] = new_z - self.tar.getZ()
                self.check_pos(p)
                
            self.players[p].setPos(new_x, new_y, new_z)
            
        return task.cont
    
    def check_pos(self,p):
        if (abs(self.distances[p][0]) < self.invf*self.tgtscx
            and abs(self.distances[p][1]) < self.invf*self.tgtscy
            and abs(self.distances[p][2]) < self.invf*self.tgtscz):
                self.too_long(p)

    ##################
    #CHECK COMPLETION#
    ##################
    def close_to_target(self):
        for i in self.highlighted_indices:
            if self.contacts[i] == False:
                return False

        if not self.check_angle():
            self.tar.setColorScale(0.1,0.1,0.1,1)
            self.tar.setAlphaScale(0.7)
            return False

        self.tar.setColorScale(0,1,1,1)
        return True

    def check_hold(self):
        if not self.close_to_target():
            self.hold_timer.reset(0.5)
            return False
        return self.hold_timer.elapsed() < 0

    def check_angle(self):
        #hardcoded condition may be able to be assimilated into old angle method somehow
        if self.table[self.trial_counter,1] == 'pts':
            vec = np.subtract(self.players[self.highlighted_indices[1]].getPos(), self.players[self.highlighted_indices[0]].getPos())
            xvec = [1,0,0]
            if self.hand == 'Left':
                xvec = [-1,0,0]
            print(math.degrees(math.acos(np.dot(vec,xvec)/(np.linalg.norm(vec)*np.linalg.norm(xvec)))))
            if math.acos(np.dot(vec,xvec)/(np.linalg.norm(vec)*np.linalg.norm(xvec))) < self.loc_angle:
                return True
            else: return False
        thumbindx = 0
        if self.hand == "Left": thumbindx = 4
        for i in self.highlighted_indices:
            if i == thumbindx:
                continue
            th = self.distances[thumbindx]
            fg = self.distances[i]
            if math.acos(np.dot(th,fg)/(np.linalg.norm(th)*np.linalg.norm(fg))) > self.loc_angle:
                return True
        return False

    def adjust_targets(self):
        #no adjustment if more than 2 fingers or position is prone
        if len(self.highlighted_indices) > 2 or self.wrist == 'pron':
            return

        xadj,yadj,zadj = np.mean(np.asarray(self.distances)[self.highlighted_indices],0)
        #yadj = np.mean(np.asarray(self.distances)[self.highlighted_indices][1])
        #zadj = np.mean(np.asarray(self.distances)[self.highlighted_indices][2])

        #do adjustment on all tasks with same name
        if self.hand == 'Left':
            xadj = -xadj
        for i in range(self.trial_counter+1,self.table.shape[0]):
            if self.table[i,1] == self.table[self.trial_counter,1]:
                self.table[i,11] = float(self.table[i,11]) + xadj
                self.table[i,12] = float(self.table[i,12]) + yadj
                self.table[i,13] = float(self.table[i,13]) + zadj


    #########
    #LOGGING#
    #########
    def play_success(self):
        if int(self.block) == 0:
            self.adjust_targets()
        self.pop.play()
        self.tar.hide()
        self.highlighted_indices = [0,1,2,3,4]

    def log_text(self):
        self.bgtext.setText('Now logging...')

    def log_data(self, task):
        if (self.trial_counter + 1) <= self.table.shape[0]:
            if self.space:
                self.log_file_name = os.path.join(self.grip_dir,
                                          self.sub_id+"_"+self.sess_id+"_"+self.hand+"_"+
                                              str(self.table[self.trial_counter,1])+"_"+str(self.table[self.trial_counter,0])+".csv" )
                self.movvars = np.column_stack((self.ts, self.statenum, self.data))
                self.statenum = []
                if self.mode=='task':
                    with open(self.log_file_name, 'ab') as f:
                        np.savetxt(f, self.movvars, fmt='%10.5f', delimiter=',')
            return task.cont
        else:
            pass

    def stoplog_text(self):
        self.dirtext.clearText()
        self.bgtext.setText('Done logging!')
        for i in range(5):
            self.players[i].show()

    #######
    #RESET#
    #######
    def delete_file(self):
        if (self.trial_counter + 1) <= self.table.shape[0]:
            self.log_file_name = os.path.join(self.grip_dir,
                                      self.sub_id+"_"+self.sess_id+"_"+self.hand+"_"+
                                          str(self.table[self.trial_counter,1])+"_"+str(self.table[self.trial_counter,0])+".csv" )
            try:
                os.remove(self.log_file_name)
            except OSError:
                pass
        else:
            pass

    def reset_baseline(self):
       self.med_data = None
                   
    def reset_keyboard_bool(self):
        self.space = False

    def hide_target(self):
        self.tar.hide()
        self.intoObject.removeNode()
        self.imageObject.destroy()

    def update_trial_command(self):
        self.dirtext.setText(str(self.table[self.trial_counter,2]))
        if self.hand == 'Left':
            xfac = -0.25
        else:
            xfac = 0.25
        self.imageObject = OnscreenImage(image = str(self.table[self.trial_counter,3]),scale=(xfac,0.25,0.25),pos=(-1.2, 0, 0.3))

    def increment_trial_counter(self):
        self.trial_counter += 1
        self.update_trial_command()

    ########
    #TIMERS#
    ########
    def start_trial_countdown(self):
        self.countdown_timer.reset(self.max_time)

    def start_hold_countdown(self):
        self.hold_timer.reset(0.5)

    def start_post_countdown(self):
        self.countdown_timer.reset(2)

    def time_elapsed(self):
        return self.countdown_timer.elapsed() < 0

    #########
    #MACHINE#
    #########
    def update_state(self, task):
        self.step()
        return task.cont

    def wait_for_space(self):
        return self.space

    def space_on(self):
        self.space = True

    #####
    #END#
    #####
    def trial_counter_exceeded(self):
        return (self.trial_counter+1) > self.table.shape[0]-1

    def clean_up(self):
        #write last known positions to 'final_targets' file
        f = open('src/pinch_task/trialtable_flex.csv')
        header = f.readline().rstrip()
        np.savetxt(self.grip_dir + '/final_targets.csv',self.table,fmt='%s',header = header, delimiter=',')
        f.close()
        sys.exit()

    ########
    #SERIAL#
    ########
    def init_ser(self):
        #CONNECT TO HAPTIC DEVICE
        ports = list_ports.comports()
        mydev = next((p.device for p in ports if p.pid == 1155))
        self.ser = serial.Serial(mydev,9600,timeout=.1)

    def sendsig(self,signal,finger,intensity):
        #would read from table, but table not available yet
        if intensity > 255:
            intensity = 255
        dur_int = [signal,finger,intensity]
        data = struct.pack('3B',*dur_int)
        self.ser.write(data)
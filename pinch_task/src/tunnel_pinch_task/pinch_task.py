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
from panda3d.core import OrthographicLens
from panda3d.core import WindowProperties

from collections import Counter

from src.machine import GripStateMachine
from toon.input import MpDevice
from toon.input.clock import mono_clock
from src.hand import RightHand
from src.timers import CountdownTimer
import yaml
import math
import time

from src.handpos import *
from src.tunnel_pinch_task.draw_shape import *


class TunnelPinchTask(ShowBase, GripStateMachine):
    DATA_DIR = 'data'
    
    def __init__(self, id, session, hand, block, mode, wrist):
        ShowBase.__init__(self)
        GripStateMachine.__init__(self)
        base.disableMouse()
        wp = WindowProperties()
        wp.setSize(1920,1080)
        wp.setFullscreen(True)
        wp.setUndecorated(True)
        base.win.requestProperties(wp)

        self.sub_id = str(id)
        self.sess_id = str(session)
        self.hand = str(hand)
        self.block = str(block)
        self.mode = str(mode)
        self.wrist = str(wrist)
        
        self.prev_blk = os.path.join(self.DATA_DIR,'exp_2',self.sub_id,self.sess_id,self.wrist,self.hand,"B0")
        self.exp_blk0 = os.path.join(self.DATA_DIR,'exp_1',self.sub_id,self.sess_id,self.wrist,self.hand,"B0")
        self.table = np.loadtxt('src/tunnel_pinch_task/trialtable_flex.csv',dtype='str',delimiter=',',skiprows=1)

        indices = {}
        try:
            self.prev_table = np.loadtxt(os.path.join(self.prev_blk, 'final_targets.csv'),dtype='str',delimiter=',',skiprows=1)
        except:
            try:
                self.prev_table = np.loadtxt(os.path.join(self.exp_blk0, 'final_targets.csv'),dtype='str',delimiter=',',skiprows=1)
            except:
                print('Previous target file not found, results may be suboptimal')
        try:
            for i in range(self.prev_table.shape[0]):
                indices[self.prev_table[i,1]] = int(self.prev_table[i,0])-1
            for i in range(self.table.shape[0]):
                self.table[i,11] = self.prev_table[indices[self.table[i,1].strip()],11]
                self.table[i,12] = self.prev_table[indices[self.table[i,1].strip()],12]
                self.table[i,13] = self.prev_table[indices[self.table[i,1].strip()],13]
        except:
            print('Invalid target file')
        
        self.table = np.array([[item.strip() for item in s] for s in self.table])

        ###################################################
        #only use rows relevant to this block
        #HARDCODED! NOTE IN LOG SHEET
        spec_table = []
        for i in range(self.table.shape[0]):
            if int(self.block)%5 == 0: #block 0 to adjust positions
                if "(p)" in self.table[i,2]:
                    spec_table.append(self.table[i])
            elif int(self.block)%5 == 1:
                if "(L)" in self.table[i,2]:
                    spec_table.append(self.table[i])
            elif int(self.block)%5 == 2:
                if "(L+t)" in self.table[i,2]:
                    spec_table.append(self.table[i])
            elif int(self.block)%5 == 3:
                if "(S)" in self.table[i,2]:
                    spec_table.append(self.table[i])
            elif int(self.block)%5 == 4:
                if "(S+t)" in self.table[i,2]:
                    spec_table.append(self.table[i])
        ###################################################
        self.table = np.array(spec_table)

        self.session_dir = os.path.join(self.DATA_DIR,'exp_2',self.sub_id,self.sess_id,self.wrist,self.hand)
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
        self.chandler.addOutPattern('%fn-outof-%in')
        self.chandler.addAgainPattern('%fn-again-%in')
        self.attachcollnodes()

        taskMgr.add(self.read_data, 'read')
        for i in range(5):
            taskMgr.add(self.move_player, 'move%d' % i, extraArgs = [i], appendTask=True)
        taskMgr.add(self.log_data, 'log_data')
        taskMgr.add(self.update_state, 'update_state', sort=1)

        self.accept('space', self.space_on)
        self.accept('escape', self.clean_up)
        self.space = False
        self.statenum = list()

        self.max_time = 20
        self.med_data = None

        self.grip_dir = os.path.join(self.DATA_DIR,'exp_2',self.sub_id,self.sess_id,self.wrist,self.hand,"B"+self.block)
        if not os.path.exists(self.grip_dir):
           print('Making new folders: ' + self.grip_dir)
           os.makedirs(self.grip_dir)

        self.dev = MpDevice(RightHand(calibration_files=['calibs/cal_mat_70_v2.mat',
                                                'calibs/cal_mat_73_v2.mat',
                                                'calibs/cal_mat_56.mat',
                                                'calibs/cal_mat_58_v2.mat',
                                                'calibs/cal_mat_50.mat'], clock=mono_clock.get_time))

    ############
    #SET UP HUD#
    ############
    def setup_text(self):
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
        self.cam.setPos(0, 0, 12)
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
        self.inside = [False]*5
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
            self.players[f].setColorScale(0,1,0,1)
            self.tar.setColorScale(0.2,0.2,0.2,1)
            self.tar.setAlphaScale(0.7)
            self.contacts[f] = True
            taskMgr.doMethodLater(self.delay,self.too_long,'too_long%d' % f,extraArgs = [f])
                
    def collide2(self,f,collEntry):
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
        self.occSolid.show()
        self.occLines.show()

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

        self.tgtposx = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][[-2,-1],0]) + tgttsx
        self.tgtposy = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][[0,1],1]) + tgttsy
        if self.hand == 'Left':
            self.tgtposx = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][[0,1],0]) + tgttsx
            self.tgtposy = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][[-2,-1],1]) + tgttsy
        #self.tgtposx = np.mean(np.asarray(self.player_offsets)[self.highlighted_indices][:,0])
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

        if len(self.highlighted_indices) == 2:
            dx = self.players[self.highlighted_indices[0]].getX() - self.players[self.highlighted_indices[1]].getX()
            dy = self.players[self.highlighted_indices[0]].getY() - self.players[self.highlighted_indices[1]].getY()
            angle = math.degrees(math.atan(dy/dx))
            self.table[self.trial_counter,9] =  str(angle) + ' ' + str(angle-180)
        
        self.angs=self.table[self.trial_counter,9].split(' ')
        self.angs = [float(a) for a in self.angs]
        self.tunn_width=float(self.table[self.trial_counter,10])
        self.r = 1.5
        if int(self.block) == 0:
            self.r = 0
        self.x = [self.r*math.cos(math.radians(a)) for a in self.angs]
        self.y = [self.r*math.sin(math.radians(a)) for a in self.angs]
        self.occ = draw_shape(self.angs,self.tunn_width,self.r)
        self.occSolid = render.attachNewNode(self.occ[0])
        self.occSolid.setPos(self.tgtposx,self.tgtposy,self.tgtposz)
        self.occSolid.setColorScale(0,1,1,0)
        self.occSolid.setTransparency(TransparencyAttrib.MAlpha)
        self.occSolid.setAlphaScale(0.6)
        self.occLines = render.attachNewNode(self.occ[1])
        self.occLines.setPos(self.tgtposx,self.tgtposy,self.tgtposz)
        self.occSolid.hide()
        self.occLines.hide()
        self.delay=float(self.table[self.trial_counter,8])

        self.distances = [[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0]]

        #change camera to be on top of target
        self.cam.setPos(self.tgtposx, self.tgtposy - 2, 12)
        self.back_model.setPos(self.tgtposx,self.tgtposy - 2,0)
        self.cam.lookAt(self.tgtposx, self.tgtposy, 0)

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
    
    def check_pos(self, p):
        x = self.distances[p][0]
        y = self.distances[p][1]
        z = self.distances[p][2]
        hit = True
        for i in range(len(self.angs)):
            p_ang = math.acos((x*self.x[i]+y*self.y[i])/(self.r*(x**2+y**2)**0.5))
            if math.sin(p_ang)*(x**2+y**2)**0.5 < self.tunn_width and p_ang < math.pi/2:
                hit = False
                break
        if (abs(z) <= 1.2 #check z location
            and x**2 + y**2 <= self.r**2 #within radius of circle
            and hit == True):
                if self.inside[p] is False:
                    self.ignore('colfromNode%d-into-colintoNode' % p)
                    self.ignore('colfromNode%d-again-colintoNode' % p)
                    self.players[p].setColorScale(1,1,0,1)
                    self.inside[p] = True
        else:
            if self.inside[p] is True and x**2 + y**2 > self.r**2:
                self.accept('colfromNode%d-into-colintoNode' % p, self.collide1,[p])
                self.accept('colfromNode%d-again-colintoNode' % p, self.collide2,[p])
                self.players[p].setColorScale(
                    self.p_col[p][0]/255, self.p_col[p][1]/255, self.p_col[p][2]/255, 1)
                self.inside[p] = False

    ##################
    #CHECK COMPLETION#
    ##################
    def close_to_target(self):
        for i in self.highlighted_indices:
            if self.contacts[i] == False:
                return False

        self.tar.setColorScale(0,1,1,1)
        return True

    def check_hold(self):
        if not self.close_to_target():
            self.hold_timer.reset(0.5)
            return False
        return self.hold_timer.elapsed() < 0

    def adjust_targets(self):
        #no adjustment if more than 2 fingers or position is prone
        if len(self.highlighted_indices) > 2 or self.wrist == 'pron':
            return

        xadj,yadj,zadj = np.mean(np.asarray(self.distances)[self.highlighted_indices],0)
        #xadj = np.mean(np.asarray(self.distances)[self.highlighted_indices][0])
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
        self.occSolid.hide()
        self.occLines.hide()
        self.intoObject.removeNode()
        self.imageObject.destroy()

    def update_trial_command(self):
        self.dirtext.setText(str(self.table[self.trial_counter,2]))
        if self.hand == 'Left':
            xfac = -0.25
        else:
            xfac = 0.25
        self.imageObject = OnscreenImage(image = str(self.table[self.trial_counter,3]),scale=(xfac,0.25,0.25),pos=(-0.8, 0, 0.3))

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

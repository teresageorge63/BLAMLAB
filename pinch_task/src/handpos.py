import yaml
import math
import numpy as np
import os.path

###################################################
##########            METHODS            ##########
#shared methods between tasks can be defined here##
###################################################

#get finger positions from yaml
def GET_POS(session_dir,subjinfo,hand,wrist):
    with open(os.path.join(session_dir,subjinfo), 'r') as f:
            doc = yaml.load(f)
            r1 = (5-float(doc["Thumb"]["DEVICE Mount length"]))
            r2 = (5-float(doc["Index"]["DEVICE Mount length"]))
            r3 = (5-float(doc["Middle"]["DEVICE Mount length"]))
            r4 = (5-float(doc["Ring"]["DEVICE Mount length"]))
            r5 = (5-float(doc["Pinky"]["DEVICE Mount length"]))
            ang1 = math.radians(180+float(doc["Thumb"]["DEVICE Mount angle"]))
            ang2 = math.radians(float(doc["Index"]["DEVICE Mount angle"]))
            ang3 = math.radians(float(doc["Middle"]["DEVICE Mount angle"]))
            ang4 = math.radians(float(doc["Ring"]["DEVICE Mount angle"]))
            ang5 = math.radians(float(doc["Pinky"]["DEVICE Mount angle"]))

            if wrist == 'pron':
                ang1 = math.radians(180+float(doc["Thumb"]["DEVICE Mount angle"]))
                ang2 = math.radians(180+float(doc["Index"]["DEVICE Mount angle"]))
                ang3 = math.radians(180+float(doc["Middle"]["DEVICE Mount angle"]))
                ang4 = math.radians(180+float(doc["Ring"]["DEVICE Mount angle"]))



            x1 = r1* math.cos(ang1)
            y1 = r1* math.sin(ang1)
            x2 = r2* math.cos(ang2)
            y2 = r2* math.sin(ang2)
            x3 = r3* math.cos(ang3)
            y3 = r3* math.sin(ang3)
            x4 = r4* math.cos(ang4)
            y4 = r4* math.sin(ang4)
            x5 = r5* math.cos(ang5)
            y5 = r5* math.sin(ang5)

            p_x=[x1,x2,x3,x4,x5]
            p_y=[y1,y2,y3,y4,y5]
            if hand == 'Left':
                p_x = p_x[::-1]
                p_y = p_y[::-1]

            p_a = [ang1-3*math.pi/2,ang2-3*math.pi/2,ang3-3*math.pi/2,ang4-3*math.pi/2,ang5-3*math.pi/2]
    return p_x,p_y,p_a

#create rotation matrix from angles
def ROT_MAT(angles,hand):
        if hand == 'Left':
            angles = np.flip(angles)
        rotmat = [[math.cos(angles[0]),math.sin(angles[0])]+np.zeros(13).tolist(),
                    [-math.sin(angles[0]),math.cos(angles[0])]+np.zeros(13).tolist(),
                    [0,0,1]+np.zeros(12).tolist(),
                    np.zeros(3).tolist()+[math.cos(angles[1]),math.sin(angles[1])]+np.zeros(10).tolist(),
                    np.zeros(3).tolist()+[-math.sin(angles[1]),math.cos(angles[1])]+np.zeros(10).tolist(),
                    np.zeros(3).tolist()+[0,0,1]+np.zeros(9).tolist(),
                    np.zeros(6).tolist()+[math.cos(angles[2]),math.sin(angles[2])]+np.zeros(7).tolist(),
                    np.zeros(6).tolist()+[-math.sin(angles[2]),math.cos(angles[2])]+np.zeros(7).tolist(),
                    np.zeros(6).tolist()+[0,0,1]+np.zeros(6).tolist(),
                    np.zeros(9).tolist()+[math.cos(angles[3]),math.sin(angles[3])]+np.zeros(4).tolist(),
                    np.zeros(9).tolist()+[-math.sin(angles[3]),math.cos(angles[3])]+np.zeros(4).tolist(),
                    np.zeros(9).tolist()+[0,0,1]+np.zeros(3).tolist(),
                    np.zeros(12).tolist()+[math.cos(angles[4]),math.sin(angles[4]),0],
                    np.zeros(12).tolist()+[-math.sin(angles[4]),math.cos(angles[4]),0],
                    np.zeros(12).tolist()+[0,0,1]]

        return rotmat

def LEARNING_ROT_MAT(hand):
    #angles rotate clockwise
    
    angles = [math.radians(50), math.radians(320), math.radians(320), math.radians(320), math.radians(320)]
    if hand == 'Left':
        angles = np.flip(angles)
    new_rotmat = [[math.cos(angles[0]),math.sin(angles[0])]+np.zeros(13).tolist(),
                [-math.sin(angles[0]),math.cos(angles[0])]+np.zeros(13).tolist(), 
                    [0,0,1]+np.zeros(12).tolist(),
                    np.zeros(3).tolist()+[math.cos(angles[1]), math.sin(angles[1])]+np.zeros(10).tolist(),
                    np.zeros(3).tolist()+[-math.sin(angles[1]), math.cos(angles[1])]+np.zeros(10).tolist(),
                    np.zeros(5).tolist()+[1]+np.zeros(9).tolist(),
                    np.zeros(6).tolist()+[math.cos(angles[2]), math.sin(angles[2])]+np.zeros(7).tolist(),
                    np.zeros(6).tolist()+[-math.sin(angles[2]), math.cos(angles[2])]+np.zeros(7).tolist(),
                    np.zeros(8).tolist()+[1]+np.zeros(6).tolist(),
                    np.zeros(9).tolist()+[math.cos(angles[3]), math.sin(angles[3])]+np.zeros(4).tolist(),
                    np.zeros(9).tolist()+[-math.sin(angles[3]), math.cos(angles[3])]+np.zeros(4).tolist(),
                    np.zeros(11).tolist()+[1]+np.zeros(3).tolist(),
                    np.zeros(12).tolist()+[math.cos(angles[4]), math.sin(angles[4])]+np.zeros(1).tolist(),
                    np.zeros(12).tolist()+[-math.sin(angles[4]), math.cos(angles[4]),0],
                    np.zeros(14).tolist()+[1]]

    return new_rotmat
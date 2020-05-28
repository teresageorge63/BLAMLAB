import numpy as np
from panda3d.core import Geom, GeomVertexData, GeomVertexFormat, GeomVertexWriter, GeomVertexReader, GeomNode, GeomTriangles, GeomLines
from panda3d.core import TransparencyAttrib
from panda3d.core import GeomPoints

import math

#any number of angles, single width and radius
#all numbers should be floats
def draw_shape(angles, width, radius):
    res = 10
    if radius == 0:
        point = GeomNode('gnode')
        vdata = GeomVertexData('occ', GeomVertexFormat.getV3(), Geom.UHStatic)
        vdata.setNumRows(1)
        vertex = GeomVertexWriter(vdata, 'vertex')
        vertex.addData3f(0,0,0)
        
        geom = Geom(vdata)
        g = GeomPoints(Geom.UHStatic)
        g.addVertex(0)
        geom.addPrimitive(g)
        point.addGeom(geom)
        return point,point
    #first, sort angles in ascending order
    #if negative is given, translate to range of 2pi
    for i in range(len(angles)):
        if angles[i] < 0: angles[i] = 360 + angles[i]
    angles.sort()
    angles = [math.radians(a) for a in angles]
    angles.append(angles[0]) #read first angle to account for wrapping around

    #function = 'w/sin(theta)'
    
    vdata = GeomVertexData('occ', GeomVertexFormat.getV3(), Geom.UHStatic)
    vdata.setNumRows(1)
    vertex = GeomVertexWriter(vdata, 'vertex')
    
    numverts = [3]*(len(angles)-1) #center, and two points on function lines
    
    for i in range(len(angles)-1):
        #find center point
        #L = [None,None]
        #sign = [-1,1]
        #for p in range(2):
        #    theta1 = angles[i+p] - sign[p]*math.pi/2
        #    theta2 = angles[i+p] + sign[p]*math.pi/4
        #    x1 = width*math.cos(theta1)
        #    y1 = width*math.sin(theta1)
        #    r = math.sqrt(2*width**2)
        #    x2 = r*math.cos(theta2)
        #    y2 = r*math.sin(theta2)
        #    L[p] = line([x1,y1], [x2,y2])
        #R = intersection(L[0],L[1])

        #if R is False:
        #    R = [x1,y1] #if parallel, shift both lines down by y_width
        #vertex.addData3f(R[0],R[1],1)
        difang = (angles[i+1] - angles[i]) /2
        l = width/math.sin(difang)
        avgang = (angles[i] + angles[i+1]) /2
        x0 = l*math.cos(avgang)
        y0 = l*math.sin(avgang)
        vertex.addData3f(x0,y0,1)

        newang1 = angles[i] + (math.pi/2 - math.acos(width/radius))
        x = radius*math.cos(newang1)
        y = radius*math.sin(newang1)
        vertex.addData3f(x,y,1)
        newang2 = angles[i+1] - (math.pi/2 - math.acos(width/radius))
        for angle in arc(newang1,newang2,res):
            vertex.addData3f(radius*math.cos(math.radians(angle)),radius*math.sin(math.radians(angle)),1)
            numverts[i] = numverts[i] + 1
        x = radius*math.cos(newang2)
        y = radius*math.sin(newang2)
        vertex.addData3f(x,y,1)

    #copy all data to the bottom, moving it down to z = -1
    vertread = GeomVertexReader(vdata, 'vertex')
    while not vertread.isAtEnd():
        v = vertread.getData3f()
        vertex.addData3f(v[0],v[1],-1)
        
    #draw
    geom = Geom(vdata)
    #draw top
    for i in range(len(angles)-1):
        for j in range(numverts[i]-2):
            ind = sum(numverts[0:i]) + j
            g = GeomTriangles(Geom.UHStatic)
            g.add_vertices(ind-j,ind+1,ind+2)
            geom.addPrimitive(g)
    
    #draw bottom
    for i in range(len(angles)-1):
        for j in range(numverts[i]-2):
            ind = sum(numverts) + sum(numverts[0:i]) + j
            g = GeomTriangles(Geom.UHStatic)
            g.add_vertices(ind-j,ind+2,ind+1)
            geom.addPrimitive(g)
    
    #draw edges
    for i in range(len(angles)-1):
        for j in range(numverts[i]-1):
            ind = sum(numverts[0:i]) + j
            g = GeomTriangles(Geom.UHStatic)
            g.add_vertices(ind,ind+sum(numverts),ind+1)
            g.add_vertices(ind+sum(numverts),ind+1+sum(numverts),ind+1)
            geom.addPrimitive(g)
        g = GeomTriangles(Geom.UHStatic)
        ind = sum(numverts[0:i])
        indx = sum(numverts[0:i+1])
        g.add_vertices(indx-1,indx+sum(numverts)-1,ind)
        g.add_vertices(indx+sum(numverts)-1,sum(numverts)+ind,ind)
        geom.addPrimitive(g)
    
    #outline object
    lines = Geom(vdata)
    l = GeomLines(Geom.UHStatic)
    for i in range(len(angles)-1):
        for j in range(numverts[i]-1):
            ind = sum(numverts[0:i]) + j
            l.add_vertices(ind,ind+1)
            l.add_vertices(sum(numverts)+ind,sum(numverts)+ind+1)
        ind = sum(numverts[0:i])
        indx = sum(numverts[0:i+1])
        l.add_vertices(ind,indx-1)
        l.add_vertices(sum(numverts)+ind,sum(numverts)+indx-1)
        l.add_vertices(ind+1,sum(numverts)+ind+1)
        l.add_vertices(indx-1,sum(numverts)+indx-1)
        lines.addPrimitive(l)

    node = GeomNode('gnode')
    node.addGeom(geom)
    nodeL = GeomNode('gnode')
    nodeL.addGeom(lines)
    return node,nodeL

#the following two functions are used to find the intersection of the lines
#after they have been shifted. Used to draw triangle fan on top of object
"""
def line(p1, p2):
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0]*p2[1] - p2[0]*p1[1])
    return A, B, -C

def intersection(L1, L2):
    D  = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return x,y
    else:
        return False
"""
def arc(ang1, ang2, res):
    arcarray = []
    count = 0
    if math.degrees(ang2) < res:
        ang2 = ang2 - math.radians(res)
    if ang1 < 0: ang1 = 2*math.pi + ang1
    if ang2 < 0: ang2 = 2*math.pi + ang2
    while True:
        nextangle = math.ceil(math.degrees(ang1) + res*count)
        nextangle = nextangle % 360
        if nextangle > math.floor(math.degrees(ang2))-res and nextangle <= math.floor(math.degrees(ang2)):
            arcarray.append(nextangle)
            break
        arcarray.append(nextangle)
        count += 1

    return arcarray
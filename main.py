# -*- coding: utf-8 -*-
import re
from math import sin, cos
from PIL import Image
from face import src
from graphics import Vector, Canvas

scr_x = 800
scr_y = 800
scr_z = 800

"""
 0: без текстуры, яркость пропорциональна z-координате
 1: без текстуры, яркость интерполяцией по нормалям в вершинах, нормали берутся из описания модели
 2: просто текстура
 3: текстура с освещением по нормалям в вершинах
 4: без текстуры, яркость по карте нормалей
 5: текстура, яркость по карте нормалей
"""
Mode = 5


class Face(object):
    light_vector = None

    def __init__(self, texture_file, normals_file):
        self.texture_img = Image.open(texture_file)
        self.texture_pixels = self.texture_img.load()
        self.normals_img = Image.open(normals_file)
        self.normals_pixels = self.normals_img.load()
        self.vectors = vectors = []
        self.normals = normals = []
        self.textures = textures = []
        self.polygons = polygons = []

        u_max = self.texture_img.width
        v_max = self.texture_img.height
        for s in src.split('\n'):
            try:
                cmd, x, y, z = re.split('\s+', s)
            except ValueError:
                continue
            if cmd == 'v':
                vectors.append([float(i) for i in (x, y, z)])
            if cmd == 'vn':
                normals.append([float(i) for i in (x, y, z)])
            if cmd == 'vt':
                textures.append([float(x) * u_max, float(y) * v_max])
            if cmd == 'f':
                f = [[int(j)-1 for j in i.split('/')] for i in (x, y, z)]
                polygons.append({
                    'vectors': [i[0] for i in f],
                    'texture': [i[1] for i in f],
                    'normals': [i[2] for i in f],
                })

    def triangle(self, a, b, c):
        light_vector = self.light_vector
        u_max = self.texture_img.width
        v_max = self.texture_img.height
        a, b, c = sorted((a, b, c), key=lambda vector: vector.y)
        y, x1, x2, z1, z2 = a.y, a.x, a.x, a.z, a.z
        u1, u2, v1, v2 = a.u, a.u, a.v, a.v
        light1, light2 = a.light, a.light
        point = b
        height = float(c.y - y)
        delta_cx = float(c.x - x1) / height if height else 0
        delta_cz = float(c.z - z1) / height if height else 0
        delta_u2 = float(c.u - u1) / height if height else 0
        delta_v2 = float(c.v - v1) / height if height else 0
        delta_c_light = float(c.light - light1) / height if height else 0
        for step in (False, True):
            if step:
                x2 -= delta_cx
                z2 -= delta_cz
                light2 -= delta_c_light
                y, x1, z1, u1, v1, light1 = b.y, b.x, b.z, b.u, b.v, b.light
                point = c
            height = float(point.y - y)
            delta_bx = float(point.x - x1) / height if height else 0
            delta_bz = float(point.z - z1) / height if height else 0
            delta_v1 = float(point.v - v1) / height if height else 0
            delta_u1 = float(point.u - u1) / height if height else 0
            delta_b_light = float(point.light - light1) / height if height else 0
            dz = du = dv = dl = 0
            while y <= point.y:
                if x1 != x2 and not dz:
                    width = float(x2 - x1)
                    dz = float(z2 - z1) / width
                    du = float(u2 - u1) / width
                    dv = float(v2 - v1) / width
                    dl = float(light2 - light1) / width
                if x1 > x2:
                    x, z, u, v, light = x2, z2, u2, v2, light2
                else:
                    x, z, u, v, light = x1, z1, u1, v1, light1
                x_max = max(x1, x2)
                while x <= x_max:
                    if Mode == 0:
                        Vector(x, y, z).draw((int((z+scr_z/4)*255*1.7/scr_z),) * 3)
                    elif Mode == 1:
                        Vector(x, y, z).draw((int(light),) * 3)
                    else:
                        uu = min(int(u), u_max-1)
                        vv = int(v_max-v)
                        color = list(self.texture_pixels[uu, vv])
                        if Mode == 2:
                            pass
                        elif Mode == 3:
                            color = [int(i * light / 256) for i in color]
                        elif Mode == 4:
                            normal = self.normals_pixels[uu, vv]
                            n_light = int(sum([(normal[i]-128) * light_vector[i] for i in(0, 1, 2)]))
                            color = (int(n_light), ) * 3
                        else:
                            normal = self.normals_pixels[uu, vv]
                            n_light = sum([(normal[i]-128) * light_vector[i] for i in(0, 1, 2)])
                            color = [int(i * n_light / 128) for i in color]
                        Vector(x, y, z).draw(tuple(color))
                    x += 1
                    z += dz
                    u += du
                    v += dv
                    light += dl
                y += 1
                x1 += delta_bx
                x2 += delta_cx
                z1 += delta_bz
                z2 += delta_cz
                u1 += delta_u1
                u2 += delta_u2
                v1 += delta_v1
                v2 += delta_v2
                light1 += delta_b_light
                light2 += delta_c_light

    def show(self, light_vector, rotate):
        self.light_vector = light_vector
        Canvas(scr_x, scr_y, scr_z)
        scale = (int(scr_x/2 - 0.5), int(scr_y/2 - 0.5), int(scr_z/2 - 0.5))
        k = 1
        for i in self.polygons:
            vectors = [self.vectors[j] for j in i['vectors']]
            normals = [self.normals[j] for j in i['normals']]
            texture = [self.textures[j] for j in i['texture']]
            new_vectors = []
            for v in vectors:
                xyz = [v[j] * scale[j] * k for j in (0, 1, 2)]
                x = int(xyz[0] * cos(rotate) - xyz[2] * sin(rotate))
                z = int(xyz[0] * sin(rotate) + xyz[2] * cos(rotate))
                y = int(xyz[1])
                new_vectors.append(Vector(x, y, z))
            a, b, c = new_vectors
            a.u, a.v = texture[0]
            b.u, b.v = texture[1]
            c.u, c.v = texture[2]
            light = []
            for normal in normals:
                x, y, z = normal
                light.append(int((x * light_vector[0] + y * light_vector[1] + z * light_vector[2]) * 256))
            a.light, b.light, c.light = light
            self.triangle(a, b, c)
        Canvas.show()

face = Face(texture_file='african_head_diffuse.tga', normals_file='african_head_nm.png')
face.show(light_vector=(1, 0, 0.5), rotate=3.14/8)


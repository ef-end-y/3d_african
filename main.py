# -*- coding: utf-8 -*-
import re
import datetime
from math import sin, cos, copysign
from PIL import Image
from graphics import Vector, Canvas

scr_x = 800
scr_z = 1000
padding = 100

"""
 0: без текстуры, яркость пропорциональна z-координате
 1: без текстуры, яркость интерполяцией по нормалям в вершинах, нормали берутся из описания модели
 2: просто текстура
 3: текстура с освещением по нормалям в вершинах
 4: без текстуры, яркость по рассеянному свету
 5: без текстуры, яркость по отраженному свету
 6: текстура, яркость по рассеянному и отраженному свету
"""
Mode = 6


class Face(object):
    light_vector = None
    eye_vector = None

    def __init__(self, texture_file, normals_file):
        self.texture_img = Image.open(texture_file)
        self.texture_pixels = self.texture_img.load()
        self.normals_img = Image.open(normals_file)
        self.normals_pixels = self.normals_img.load()
        self.vectors = vectors = []
        self.normals = normals = []
        self.textures = textures = []
        self.polygons = polygons = []
        self.normals_map = []
        self.extremes = ([0, 0], [0, 0], [0, 0])

        obj_file = open('face.obj', 'r')
        src = obj_file.read()

        u_max = self.texture_img.width
        v_max = self.texture_img.height
        for s in src.split('\n'):
            try:
                cmd, x, y, z = re.split('\s+', re.sub('(\s|\r)*$', '', s))
            except ValueError:
                continue
            if cmd == 'v':
                coord = [float(i) for i in (x, y, z)]
                for i in (0, 1, 2):
                    self.extremes[i][0] = min(self.extremes[i][0], coord[i])
                    self.extremes[i][1] = max(self.extremes[i][1], coord[i])
                vectors.append(coord)
            if cmd == 'vn':
                normals.append([float(i) for i in (x, y, z)])
            if cmd == 'vt':
                textures.append([float(x) * u_max, float(y) * v_max])
            if cmd == 'f':
                f = [[0 if j == '' else int(j)-1 for j in i.split('/')] for i in (x, y, z)]
                polygons.append({
                    'vectors': [i[0] for i in f],
                    'texture': [i[1] for i in f],
                    'normals': [i[2] for i in f],
                })
        pass

    def triangle(self, a, b, c):
        light_vector = self.light_vector
        eye_vector = self.eye_vector
        texture_pixels = self.texture_pixels
        normals_map = self.normals_map
        u_max = self.texture_img.width - 1
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
                        Canvas.pixel(x, y, z, (int(z * 200 / scr_z + 50),) * 3)
                    elif Mode == 1:
                        Canvas.pixel(x, y, z, (int(light),) * 3)
                    else:
                        uu = int(u)
                        vv = int(v_max-v-1)
                        if uu > u_max:
                            uu = u_max
                        if uu < 0:
                            uu = 0
                        if vv < 0:
                            vv = 0
                        color = list(texture_pixels[uu, vv])
                        if Mode == 2:
                            pass
                        elif Mode == 3:
                            color = [int(i * light / 256) for i in color]
                        else:
                            normals = normals_map[uu][vv]
                            n_light = sum([normals[i] * light_vector[i] for i in(0, 1, 2)])
                            mirror = [light_vector[i] - 2 * normals[i] * n_light for i in(0, 1, 2)]
                            specular = sum([-mirror[i] * eye_vector[i] for i in(0, 1, 2)])
                            specular = copysign(pow(specular, 10), specular)
                            if Mode == 4:
                                n_light = int(n_light*256)
                                color = (n_light,) * 3
                            elif Mode == 5:
                                intensity = int(256*specular)
                                if intensity < 0:
                                    intensity = 0
                                color = (intensity,) * 3
                            else:

                                intensity = float(n_light*0.7 + specular*0.005 + 0.2)
                                if intensity < 0:
                                    intensity = 0
                                color = [int(i * intensity) for i in color]
                        Canvas.pixel(x, y, z, tuple(color))
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

    def show(self, light_vector, eye_vector, rotate):
        self.light_vector = light_vector
        self.eye_vector = eye_vector
        original_box = [i[1] - i[0] for i in self.extremes]
        scr_y = int(scr_x * original_box[1] / original_box[0])
        Canvas(scr_x, scr_y, scr_z)

        self.normals_map = normals_map = []
        height = self.normals_img.height
        normals_pixels = self.normals_pixels
        for j in range(self.normals_img.width):
            line = [[float(a-128)/128 for a in normals_pixels[j, i]] for i in range(height)]
            normals_map.append(line)

        scale = [scr_x-padding, scr_y-padding, scr_z-padding]
        scale = [scale[i] / (self.extremes[i][1]-self.extremes[i][0]) for i in (0, 1, 2)]
        padding2 = padding / 2
        k = 1
        for i in self.polygons:
            vectors = [self.vectors[j] for j in i['vectors']]
            normals = [self.normals[j] for j in i['normals']]
            texture = [0 if j == 0 else self.textures[j] for j in i['texture']]
            new_vectors = []
            for v in vectors:
                xyz = [(v[j] - self.extremes[j][0]) * scale[j] * k + padding2 for j in (0, 1, 2)]
                x = int(xyz[0] * cos(rotate) - xyz[2] * sin(rotate))
                z = int(xyz[0] * sin(rotate) + xyz[2] * cos(rotate))
                y = int(xyz[1])
                new_vectors.append(Vector(x, y, z))
            a, b, c = new_vectors
            a.u, a.v = texture[0] or (0, 0)
            b.u, b.v = texture[1] or (0, 0)
            c.u, c.v = texture[2] or (0, 0)
            light = []
            for normal in normals:
                x, y, z = normal
                light.append(int((x * light_vector[0] + y * light_vector[1] + z * light_vector[2]) * 256))
            a.light, b.light, c.light = light
            self.triangle(a, b, c)
        Canvas.show()
dt = datetime.datetime.now()
face = Face(texture_file='african_head_diffuse.tga', normals_file='african_head_nm.png')
face.show(light_vector=(1, 1, 1), eye_vector=(0, 0, 1), rotate=0*3.14/4)
print datetime.datetime.now() - dt


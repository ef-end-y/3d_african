# -*- coding: utf-8 -*-
import re
import datetime
from math import sin, cos, copysign
from PIL import Image
from graphics import Vector, Canvas

Scr_x = 600
Scr_z = 10000

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
MSAA = True  # multisampling


class Render(object):
    light_vector = None
    eye_vector = None
    pixels = None
    z_buffer = None
    scr_x = 0
    scr_y = 0
    scr_z = 0
    u_max = None
    v_max = None

    def __init__(self, texture_file, normals_file, obj_file=''):
        self.texture_img = Image.open(texture_file)
        self.texture_pixels = self.texture_img.load()
        self.normals_img = Image.open(normals_file)
        self.normals_pixels = self.normals_img.load()
        self.vectors = vectors = []
        self.normals = normals = []
        self.textures = textures = []
        self.polygons = polygons = []
        self.normals_map = []

        obj_file = open(obj_file, 'r')
        src = obj_file.read()

        u_max = self.texture_img.width
        v_max = self.texture_img.height
        for s in src.split('\n'):
            try:
                data = re.split('\s+', re.sub('(\s|\r)*$', '', s))
                cmd = data[0]
                if cmd == 'v':
                    vectors.append(tuple(float(i) for i in data[1:4]))
                if cmd == 'vn':
                    normals.append(tuple(float(i) for i in data[1:4]))
                if cmd == 'vt':
                    textures.append((float(data[1]) * u_max, float(data[2]) * v_max))
                if cmd == 'f':
                    f = (tuple(0 if j == '' else int(j)-1 for j in i.split('/')) for i in data[1:4])
                    polygon = []
                    for i in f:
                        polygon.append({
                            'xyz': vectors[i[0]],
                            'texture': textures[i[1]],
                            'normals': normals[i[2]],
                        })
                    polygons.append(tuple(polygon))
            except (ValueError, IndexError):
                print s
                continue

    def set_pixel(self, x, y, z, u, v, light, pixel_line, multi):
        xx = int(round(x))
        zz = round(z)
        index = int(y * self.scr_x + xx)
        if self.z_buffer[index] >= zz:
            return
        self.z_buffer[index] = zz
        if Mode == 0:
            color = (int(z * 200 / Scr_z + 50),) * 3
        elif Mode == 1:
            color = (int(light),) * 3
        else:
            uu = max(0, min(int(u), self.u_max))
            vv = max(0, min(int(self.v_max - v), self.v_max))
            color = list(self.texture_pixels[uu, vv])
            if Mode == 2:
                pass
            elif Mode == 3:
                color = [int(i * light / 256) for i in color]
            else:
                normals = self.normals_map[uu][vv]
                n_light = sum([normals[i] * self.light_vector[i] for i in(0, 1, 2)])
                mirror = [self.light_vector[i] - 2 * normals[i] * n_light for i in(0, 1, 2)]
                specular = sum([-mirror[i] * self.eye_vector[i] for i in(0, 1, 2)])
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
                color = tuple(color)
        pixel_line[xx] = color
        if multi:
            if self.z_buffer[index+1] >= zz:
                return
            self.z_buffer[index+1] = zz
            pixel_line[xx+1] = color

    def triangle(self, a, b, c):
        self.u_max = self.texture_img.width - 1
        self.v_max = self.texture_img.height - 1
        pixels = self.pixels
        a, b, c = sorted((a, b, c), key=lambda vector: vector.y)
        y, x1, x2, z1, z2 = int(a.y), a.x, a.x, a.z, a.z
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
                y, x1, z1, u1, v1, light1 = int(b.y), b.x, b.z, b.u, b.v, b.light
                point = c
            height = float(point.y - y) or 1.0
            delta_bx = float(point.x - x1) / height
            delta_bz = float(point.z - z1) / height
            delta_v1 = float(point.v - v1) / height
            delta_u1 = float(point.u - u1) / height
            delta_b_light = float(point.light - light1) / height
            dx = float(x2 + delta_cx - x1 - delta_bx) or 1.0
            dz = float(z2 + delta_cz - z1 - delta_bz) / dx
            du = float(u2 + delta_u2 - u1 - delta_u1) / dx
            dv = float(v2 + delta_v2 - v1 - delta_v1) / dx
            dl = float(light2 + delta_c_light - light1 - delta_b_light) / dx
            if step:
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

            while y <= point.y:
                if x1 > x2:
                    x, z, u, v, light, x_right = x2, z2, u2, v2, light2, x1
                    last_point = (x1, y, z1, u1, v1, light1)
                else:
                    x, z, u, v, light, x_right = x1, z1, u1, v1, light1, x2
                    last_point = (x2, y, z2, u2, v2, light2)
                pixel_line = pixels[self.scr_y - y]
                line = []
                while x <= x_right:
                    line.append((x, y, z, u, v, light))
                    x += 1
                    z += dz
                    u += du
                    v += dv
                    light += dl
                line.append(last_point)
                n = len(line)
                k = True
                for i, param in enumerate(line):
                    if not MSAA or i in (0, 1, n-2, n-1):
                        self.set_pixel(*param, pixel_line=pixel_line, multi=False)
                    else:
                        if k:
                            self.set_pixel(*param, pixel_line=pixel_line, multi=True)
                        k = not k
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
        self.normals_map = normals_map = []
        height = self.normals_img.height
        normals_pixels = self.normals_pixels
        for j in range(self.normals_img.width):
            line = [[float(a-128)/128 for a in normals_pixels[j, i]] for i in range(height)]
            # line = [[float(normals_pixels[j, i]-128)/128.0] * 3 for i in range(height)]
            normals_map.append(line)
        rotated = []
        xx, yy, zz = [], [], []
        for polygon in self.polygons:
            new_polygon = []
            for v in polygon:
                x, y, z = v['xyz']
                x = float(x * cos(rotate) - z * sin(rotate))
                z = float(x * sin(rotate) + z * cos(rotate))
                y = y
                new_polygon.append({
                    'xyz': (x, y, z),
                    'texture': v['texture'],
                    'normals': v['normals'],
                })
                xx.append(x)
                yy.append(y)
                zz.append(z)
            rotated.append(new_polygon)
        min_x = min(xx)
        min_y = min(yy)
        min_z = min(zz)
        scr_x = Scr_x * 2 if MSAA else Scr_x
        scale_x = int((scr_x - 1) / (max(xx) - min_x))
        scale_y = int((Scr_x - 1) / (max(xx) - min_x))
        scr_y = int((max(yy) - min_y) * scale_y) + 1
        scale_z = int(Scr_z / (max(zz) - min_z))

        Canvas(Scr_x, scr_y, Scr_z)
        (self.scr_x, self.scr_y, self.scr_z) = (scr_x-1, scr_y-1, Scr_z)

        self.pixels = pixels = []
        for j in range(scr_y):
            pixels.append([(0, 0, 0) for i in range(scr_x)])
        self.z_buffer = [0] * scr_x * scr_y

        for polygon in rotated:
            vectors3 = []
            for v in polygon:
                x, y, z = v['xyz']
                vector = Vector(
                    round((x - min_x) * scale_x),
                    round((y - min_y) * scale_y),
                    round((z - min_z) * scale_z)
                )
                vector.u, vector.v = v['texture'] or (0, 0)
                x, y, z = v['normals']
                vector.light = int((x * light_vector[0] + y * light_vector[1] + z * light_vector[2]) * 128)
                vectors3.append(vector)
            self.triangle(*vectors3)
        Canvas.show(self.pixels, multisampling=MSAA)

dt = datetime.datetime.now()
face = Render(
    obj_file='face.obj',
    texture_file='african_head_diffuse.tga',
    normals_file='african_head_nm.png'
)
#face = Render(
#    obj_file='Porsche_911_GT2.obj',
#    texture_file='0000.BMP',
#    normals_file='0000-a.BMP'
#)
face.show(
    light_vector=(1, 1, 1),
    eye_vector=(0, 0, 1),
    rotate=1*3.14/4
)
print datetime.datetime.now() - dt

"""
    vectors3 = [
        Vector(200, 100, 10, 255),
        Vector(100, 200, 10, 200),
        Vector(650, 500, 10, 100),
    ]
    self.triangle(*vectors3)
    Canvas.show(self.pixels, multisampling=MSAA)
    exit()
"""
# -*- coding: utf-8 -*-
import re
import datetime
from math import sin, cos, copysign
from PIL import Image
from graphics import Vector, Canvas, Matrix

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
Multisampling = False


class Render(object):
    light_vector = None
    eye_vector = None
    pixels = None
    scr_x = 0
    scr_y = 0
    scr_z = 0
    current_scr_x = 0
    tr_num = 0
    layer2 = None
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
        limit = 100000
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
                    limit -= 1
                    if not limit:
                        break
            except (ValueError, IndexError):
                print s
                continue
        if Mode == 0:
            self.set_pixel_now = self.set_pixel0
        elif Mode == 1:
            self.set_pixel_now = self.set_pixel1
        elif Mode == 2:
            self.set_pixel_now = self.set_pixel2
        elif Mode == 3:
            self.set_pixel_now = self.set_pixel3
        elif Mode == 4:
            self.set_pixel_now = self.set_pixel4
        elif Mode == 5:
            self.set_pixel_now = self.set_pixel5
        elif Mode == 6:
            self.set_pixel_now = self.set_pixel6

    def set_pixel0(self, z, u, v, light, pixel):
        pixel.extend([int(z * 200 / Scr_z + 50)] * 3)

    def set_pixel1(self, z, u, v, light, pixel):
        pixel.extend([int(light)] * 3)

    def set_pixel2(self, z, u, v, light, pixel):
        pixel.extend(self.texture_pixels[u, v])

    def set_pixel3(self, z, u, v, light, pixel):
        color = list(self.texture_pixels[u, v])
        pixel.extend([int(i * light / 128) for i in color])

    def set_pixel4(self, x, z, u, v, light, pixel):
        normals = self.normals_map[u][v]
        n_light = sum([normals[i] * self.light_vector[i] for i in(0, 1, 2)])
        n_light = int(n_light*256)
        pixel.extend([n_light] * 3)

    def set_pixel5(self, z, u, v, light, pixel):
        normals = self.normals_map[u][v]
        n_light = sum([normals[i] * self.light_vector[i] for i in(0, 1, 2)])
        mirror = [self.light_vector[i] - 2 * normals[i] * n_light for i in(0, 1, 2)]
        specular = sum([-mirror[i] * self.eye_vector[i] for i in(0, 1, 2)])
        specular = copysign(pow(specular, 10), specular)
        intensity = int(512*specular)
        if intensity < 0:
            intensity = 0
        pixel.extend([intensity] * 3)

    def set_pixel6(self, z, u, v, light, pixel):
        color = list(self.texture_pixels[u, v])
        normals = self.normals_map[u][v]
        n_light = sum([normals[i] * self.light_vector[i] for i in(0, 1, 2)])
        mirror = [self.light_vector[i] - 2 * normals[i] * n_light for i in(0, 1, 2)]
        specular = sum([-mirror[i] * self.eye_vector[i] for i in(0, 1, 2)])
        specular = copysign(pow(specular, 10), specular)
        intensity = float(n_light*0.7 + specular*2 + 0.2)
        if intensity < 0:
            intensity = 0
        color = [int(i * intensity) for i in color]
        pixel.extend(color)

    def set_pixel(self, xx, z, u, v, light, pixel_line, multisampling=False):
        zz = round(z)
        index = pixel_line + xx
        if self.pixels[index][0] > zz:
            return
        pixel = self.pixels[index] = [zz, self.tr_num]
        # if multisampling:
        #    pixel.extend([255, 0, 0])
        #    return
        uu = max(0, min(int(u), self.u_max))
        vv = max(0, min(int(self.v_max - v), self.v_max))
        self.set_pixel_now(zz, uu, vv, light, pixel)

    def triangle(self, tr_num, a, b, c, multisampling=False):
        self.tr_num = tr_num
        self.u_max = self.texture_img.width - 1
        self.v_max = self.texture_img.height - 1
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
                y, x1, z1, u1, v1, light1 = int(b.y), b.x, b.z, b.u, b.v, b.light
                point = c
                height = float(point.y - y)
                if not height:
                    break
                y += 1
            else:
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
            pixel_line = y * self.current_scr_x
            while True:
                if step:
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
                if x1 > x2:
                    x, z, u, v, light, x_right = x2, z2, u2, v2, light2, x1
                    last_point = (int(round(x1)), z1, u1, v1, light1)
                else:
                    x, z, u, v, light, x_right = x1, z1, u1, v1, light1, x2
                    last_point = (int(round(x2)), z2, u2, v2, light2)
                xx = int(round(x))
                if multisampling:
                    force_calc = True
                    while x <= x_right:
                        if force_calc:
                            self.set_pixel(xx, z, u, v, light, pixel_line)
                            force_calc = False
                        else:
                            index = pixel_line + xx
                            p = self.layer2[index]
                            if len(p) == 5 and p[1] == tr_num:
                                self.pixels[index] = p
                            else:
                                self.set_pixel(xx, z, u, v, light, pixel_line)
                        xx += 1
                        x += 1
                        z += dz
                        u += du
                        v += dv
                        light += dl
                else:
                    while x <= x_right:
                        self.set_pixel(xx, z, u, v, light, pixel_line)
                        xx += 1
                        x += 1
                        z += dz
                        u += du
                        v += dv
                        light += dl
                self.set_pixel(*last_point, pixel_line=pixel_line)
                y += 1
                if y > point.y:
                    break
                step = True
                pixel_line += self.current_scr_x

    def show(self, light_vector, eye_vector, x_rotate=0.0, y_rotate=0.0, z_rotate=0.0):
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
                x, y, z = (Matrix([[x, y, z]]) * Matrix([
                    [1, 0, 0],
                    [0, cos(x_rotate), -sin(x_rotate)],
                    [0, sin(x_rotate), cos(x_rotate)]
                ]) * Matrix([
                    [cos(y_rotate), 0, sin(y_rotate)],
                    [0, 1, 0],
                    [-sin(y_rotate), 0, cos(y_rotate)]
                ]) * Matrix([
                    [cos(z_rotate), -sin(z_rotate), 0],
                    [sin(z_rotate), cos(z_rotate), 0],
                    [0, 0, 1]
                ])).data[0]
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
        self.current_scr_x = scr_x = Scr_x
        scale_y = scale_x = (scr_x - 1) // (max(xx) - min_x)
        scr_y = int((max(yy) - min_y) * scale_y) + 1
        scale_z = Scr_z // (max(zz) - min_z)

        Canvas(Scr_x, scr_y, Scr_z)
        (self.scr_x, self.scr_y, self.scr_z) = (scr_x, scr_y, Scr_z)

        self.pixels = pixels = [[0]] * scr_x * (scr_y + 1)
        triangles = []
        tr_num = 0
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
                vector.light = int((x * light_vector.x + y * light_vector.y + z * light_vector.z) * 256)
                vectors3.append(vector)
            self.triangle(tr_num, *vectors3)
            for vector in vectors3:
                vector.x *= 2
                vector.y *= 2
            triangles.append(vectors3)
            tr_num += 1

        if Multisampling:
            visible_triangles = {}
            self.layer2 = layer2 = []
            for y in range(0, self.scr_y * self.scr_x, self.scr_x):
                new_line = []
                for x in range(self.scr_x):
                    p = pixels[y + x]
                    if len(p) > 1 and p[1] not in visible_triangles:
                        visible_triangles[p[1]] = True
                    new_line.append(p)
                    new_line.append(p)
                layer2.extend(new_line)
                layer2.extend(new_line)
            self.pixels = [[0]] * scr_x * (scr_y + 1) * 4
            self.current_scr_x *= 2
            for tr_num, vectors3 in enumerate(triangles):
                if tr_num in visible_triangles:
                    self.triangle(tr_num, *vectors3, multisampling=True)

        Canvas.show(self.pixels, multisampling=Multisampling)

dt = datetime.datetime.now()
face = Render(
    obj_file='face.obj',
    texture_file='african_head_diffuse.tga',
    normals_file='african_head_nm.png'
)
face.show(
    light_vector=Vector(1, 1, 1).normalize(),
    eye_vector=Vector(0, 0, 1).normalize(),
    x_rotate=-0.4*0,
    y_rotate=0.2*0,
    z_rotate=-0.5*0,
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
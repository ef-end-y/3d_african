# -*- coding: utf-8 -*-
import re
import datetime
from math import sin, cos, copysign
from PIL import Image
from graphics import Canvas, Vector, Matrix

Scr_x = 600
Scr_z = 10000

"""
 0: без текстуры, яркость пропорциональна z-координате
 1: без текстуры, яркость интерполяцией по нормалям в вершинах, нормали берутся из описания модели
 2: просто текстура
 3: текстура с освещением по нормалям в вершинах
 4: без текстуры, яркость по рассеянному свету (normal mapping)
 5: без текстуры, яркость по отраженному свету
 6: текстура, яркость по рассеянному и отраженному свету
 7: текстура, гуро, normal mapping, shadow mapping
"""
Mode = 6
Multisampling = False


class View(object):
    set_pixel_now = None
    texture_pixels = None
    texture_width = 0
    texture_height = 0
    normals_map = None
    light_vector = None
    eye_vector = None
    tr_num = 0
    shadow = None
    transform = None
    layer2 = None

    def __init__(self, polygons, pixel_mode, eye_vector, light_vector, transform=None,
                 texture=None, normals_map=None, shadow=None):
        new_polygons = []
        xx, yy, zz = [], [], []
        self.transform = transform
        for polygon in polygons:
            new_polygon = []
            for v in polygon:
                x, y, z = transform(Matrix([v['xyz']])) if transform else v['xyz']
                new_polygon.append({
                    'xyz': (x, y, z),
                    'texture': v['texture'],
                    'normals': v['normals'],
                })
                xx.append(x)
                yy.append(y)
                zz.append(z)
            new_polygons.append(new_polygon)
        self.width = width = Scr_x
        self.min_x = min_x = min(xx)
        self.min_y = min_y = min(yy)
        self.min_z = min_z = min(zz)
        self.scale_x = scale_x = (width - 1) // (max(xx) - min(xx))
        self.scale_y = scale_y = (width - 1) // (max(xx) - min(xx))
        self.scale_z = scale_z = Scr_z // (max(zz) - min(zz))
        self.height = height = int((max(yy) - min(yy)) * scale_y) + 1
        self.pixels = [[0]] * width * (height + 1)
        self.normals_map = normals_map
        self.eye_vector = eye_vector
        self.light_vector = light_vector
        self.shadow = shadow

        if texture:
            self.texture_pixels = texture.load()
            self.texture_width = texture.width - 1
            self.texture_height = texture.height - 1
        if pixel_mode == 0:
            self.set_pixel_now = self.set_pixel0
        elif pixel_mode == 1:
            self.set_pixel_now = self.set_pixel1
        elif pixel_mode == 2:
            self.set_pixel_now = self.set_pixel2
        elif pixel_mode == 3:
            self.set_pixel_now = self.set_pixel3
        elif pixel_mode == 4:
            self.set_pixel_now = self.set_pixel4
        elif pixel_mode == 5:
            self.set_pixel_now = self.set_pixel5
        elif pixel_mode == 6:
            self.set_pixel_now = self.set_pixel6
        elif pixel_mode == 7:
            self.set_pixel_now = self.set_pixel7

        tr_num = 0
        triangles = self.triangles = []
        for polygon in new_polygons:
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

    @staticmethod
    def set_pixel0(x, y, z, u, v, light, pixel):
        pixel.extend([int(z * 256 / Scr_z)] * 3)

    @staticmethod
    def set_pixel1(x, y, z, u, v, light, pixel):
        pixel.extend([int(light)] * 3)

    def set_pixel2(self, x, y, z, u, v, light, pixel):
        pixel.extend(self.texture_pixels[u, v])

    def set_pixel3(self, x, y, z, u, v, light, pixel):
        color = list(self.texture_pixels[u, v])
        pixel.extend([int(i * light / 128) for i in color])

    def set_pixel4(self, x, y, z, u, v, light, pixel):
        normals = self.normals_map[u][v]
        n_light = sum([normals[i] * self.light_vector[i] for i in(0, 1, 2)])
        n_light = int(n_light*256)
        pixel.extend([n_light] * 3)

    def set_pixel5(self, x, y, z, u, v, light, pixel):
        normals = self.normals_map[u][v]
        n_light = sum([normals[i] * self.light_vector[i] for i in(0, 1, 2)])
        mirror = [self.light_vector[i] - 2 * normals[i] * n_light for i in(0, 1, 2)]
        specular = sum([-mirror[i] * self.eye_vector[i] for i in(0, 1, 2)])
        specular = copysign(pow(specular, 10), specular)
        intensity = int(512*specular)
        if intensity < 0:
            intensity = 0
        pixel.extend([intensity] * 3)

    def set_pixel6(self, x, y, z, u, v, light, pixel):
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

    def set_pixel7(self, x, y, z, u, v, light, pixel):
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
        # Shadow
        x0 = x / self.scale_x + self.min_x
        y0 = y / self.scale_y + self.min_y
        z0 = z / self.scale_z + self.min_z
        x0, y0, z0 = self.shadow.transform(Matrix([[x0, y0, z0]]))
        x0 = round((x0 - self.shadow.min_x) * self.shadow.scale_x)
        y0 = round((y0 - self.shadow.min_y) * self.shadow.scale_y)
        z0 = round((z0 - self.shadow.min_z) * self.shadow.scale_z)
        shadow_pixel = self.shadow.pixels[int(x0) + int(y0 * self.shadow.width)]
        if shadow_pixel[0] <= (z0+150):
            pixel.extend(color)
        else:
            pixel.extend([int(i * 0.4) for i in color])

    def set_pixel(self, x, y, z, u, v, light, pixel_line, multisampling=False):
        zz = round(z)
        index = pixel_line + x
        if self.pixels[index][0] > zz:
            return
        pixel = self.pixels[index] = [zz, self.tr_num]
        # if multisampling:
        #    pixel.extend([255, 0, 0])
        #    return
        uu = max(0, min(int(u), self.texture_width))
        vv = max(0, min(int(self.texture_height - v), self.texture_height))
        self.set_pixel_now(x, y, zz, uu, vv, light, pixel)

    def triangle(self, tr_num, a, b, c, multisampling=False):
        self.tr_num = tr_num
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
            pixel_line = y * self.width
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
                    last_point = (int(round(x1)), y, z1, u1, v1, light1)
                else:
                    x, z, u, v, light, x_right = x1, z1, u1, v1, light1, x2
                    last_point = (int(round(x2)), y, z2, u2, v2, light2)
                xx = int(round(x))
                if multisampling:
                    force_calc = True
                    while x <= x_right:
                        if force_calc:
                            self.set_pixel(xx, y, z, u, v, light, pixel_line)
                            force_calc = False
                        else:
                            index = pixel_line + xx
                            p = self.layer2[index]
                            if len(p) == 5 and p[1] == tr_num:
                                self.pixels[index] = p
                            else:
                                self.set_pixel(xx, y, z, u, v, light, pixel_line)
                        xx += 1
                        x += 1
                        z += dz
                        u += du
                        v += dv
                        light += dl
                else:
                    while x <= x_right:
                        self.set_pixel(xx, y, z, u, v, light, pixel_line)
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
                pixel_line += self.width


class Render(object):
    def __init__(self, texture_file, normals_file, obj_file=''):
        self.texture_img = Image.open(texture_file)
        self.normals_img = Image.open(normals_file)
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

    @staticmethod
    def rotate(x_rotate=0.0, y_rotate=0.0, z_rotate=0.0):
        def ret(matrix):
            return (matrix * Matrix([
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
        return ret

    @staticmethod
    def shadow_matrix(eye):
        up = Vector(0, 1, 0).normalize()
        z = Vector(-eye.x, -eye.y, eye.z)
        x = up.cross(z).normalize()
        y = z.cross(x).normalize()
        minv = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        for i in range(3):
            minv[0][i] = x[i]
            minv[1][i] = y[i]
            minv[2][i] = z[i]
        return lambda matrix: (matrix * Matrix(minv)).data[0]

    def show(self, light_vector, eye_vector, x_rotate=0.0, y_rotate=0.0, z_rotate=0.0):
        normals_map = []
        height = self.normals_img.height
        normals_pixels = self.normals_img.load()
        for j in range(self.normals_img.width):
            line = [[float(a-128)/128 for a in normals_pixels[j, i]] for i in range(height)]
            normals_map.append(line)

        shadow = None
        if Mode == 7:
            shadow_matrix = self.shadow_matrix(light_vector)
            shadow = View(
                polygons=self.polygons,
                pixel_mode=2,
                eye_vector=eye_vector,
                light_vector=light_vector,
                transform=shadow_matrix,
                texture=self.texture_img,
                normals_map=normals_map,
            )
            # canvas = Canvas(shadow.width, shadow.height, shadow.pixels)
            # canvas.img.show()
            # exit()

        view = View(
            polygons=self.polygons,
            pixel_mode=Mode,
            eye_vector=eye_vector,
            light_vector=light_vector,
            transform=self.rotate(x_rotate, y_rotate, z_rotate),
            texture=self.texture_img,
            normals_map=normals_map,
            shadow=shadow,
        )

        canvas_width = view.width
        canvas_height = view.height

        if Multisampling:
            visible_triangles = {}
            view.layer2 = layer2 = []
            for y in range(0, view.height * view.width, view.width):
                new_line = []
                for x in range(view.width):
                    p = view.pixels[y + x]
                    if len(p) > 1 and p[1] not in visible_triangles:
                        visible_triangles[p[1]] = True
                    new_line.append(p)
                    new_line.append(p)
                layer2.extend(new_line)
                layer2.extend(new_line)
            view.width *= 2
            view.height *= 2
            view.scale_x *= 2
            view.scale_y *= 2
            view.pixels = [[0]] * view.width * (view.height + 1)
            for tr_num, vectors3 in enumerate(view.triangles):
                if tr_num in visible_triangles:
                    view.triangle(tr_num, *vectors3, multisampling=True)

        canvas = Canvas(canvas_width, canvas_height, view.pixels, multisampling=Multisampling)
        canvas.img.show()

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
    z_rotate=-0.2*0,
)
print datetime.datetime.now() - dt

import re
from PIL import Image
from face import src
from graphics import Vector, Canvas, triangle

scr_x = 800
scr_y = 800
scr_z = 400


class Polygon(object):
    a = None
    b = None
    c = None
    normals = None
    texture = None

    def __init__(self, a, b, c, normals, texture):
        self.a, self.b, self.c = a, b, c
        self.normals = normals
        self.texture = texture


class Face(object):
    def __init__(self, texture_file):
        self.texture_img = Image.open(texture_file)
        self.texture_pixels = self.texture_img.load()
        self.points = points = []
        self.normals = normals = []
        self.textures = textures = []
        self.polygons = polygons = []

        scale = (int(scr_x/2 - 0.5), int(scr_y/2 - 0.5), int(scr_z/2 - 0.5))

        for s in src.split('\n'):
            try:
                cmd, x, y, z = re.split('\s+', s)
            except ValueError:
                continue
            if cmd == 'v':
                points.append(Vector(*[int((float([x, y, z][i])+1)*scale[i]) for i in (0, 1, 2)]))
            if cmd == 'vn':
                normals.append([float(i) for i in (x, y, z)])
            if cmd == 'vt':
                textures.append([float(i) for i in (x, y)])
            if cmd == 'f':
                abc = [points[int(i.split('/')[0])-1] for i in (x, y, z)]
                texture = [textures[int(i.split('/')[1])-1] for i in (x, y, z)]
                normal = [normals[int(i.split('/')[2])-1] for i in (x, y, z)]
                polygons.append(Polygon(*abc, normals=normal, texture=texture))

    def show(self, light_vector):
        Canvas(scr_x, scr_y, scr_z)
        for p in self.polygons:
            a, b, c = p.a, p.b, p.c
            a.u, a.v = p.texture[0]
            b.u, b.v = p.texture[1]
            c.u, c.v = p.texture[2]
            light = []
            for normal in p.normals:
                x, y, z = normal
                light.append(int((x * light_vector[0] + y * light_vector[1] + z * light_vector[2]) * 250))
            a.light, b.light, c.light = light
            triangle(a, b, c, self.texture_pixels, self.texture_img)
        Canvas.show()

Face(texture_file='african_head_diffuse.tga').show((0, 0, 1))


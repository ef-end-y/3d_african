import math
from PIL import Image


class Canvas(object):
    pixels = None
    z_buffer = None
    img = None
    scr_x = None
    scr_y = None
    scr_z = None
    center_x = None
    center_y = None

    def __init__(self, scr_x, scr_y, scr_z):
        Canvas.img = Image.new('RGB', (scr_x, scr_y), 'black')
        Canvas.pixels = self.img.load()
        Canvas.z_buffer = {}
        Canvas.scr_x = scr_x - 1
        Canvas.scr_y = scr_y - 1
        Canvas.scr_z = scr_z - 1
        Canvas.center_x = int(scr_x/2)
        Canvas.center_y = int(scr_y/2)
        Canvas.canvas = self

    @classmethod
    def pixel(cls, x, y, z, color):
        x, y, z = int(round(x)), int(round(y)), round(z)
        index = '%s:%s' % (x, y)
        if cls.z_buffer.get(index, -99999) >= z:
            return
        cls.z_buffer[index] = z
        try:
            cls.pixels[x, cls.scr_y - y] = color
        except:
            # print x, y
            pass

    @classmethod
    def show(cls, pixels, multisampling=False):
        canvas_pixels = cls.pixels
        k = 2 if multisampling else 1
        for y in range(cls.scr_y):
            step = True
            x0 = 0
            for x in range(cls.scr_x * k):
                step = not step
                if multisampling and step:
                    continue
                color = pixels[y][x]
                if multisampling:
                    color2 = pixels[y][x+1]
                    color = (
                        int((color[0] + color2[0])/2),
                        int((color[1] + color2[1])/2),
                        int((color[2] + color2[2])/2),
                    )
                canvas_pixels[x0, y] = color
                x0 += 1
        cls.img.show()


class Vector(object):
    x = 0
    y = 0
    z = 0
    u = 0
    v = 0
    light = None

    def __init__(self, x, y, z, light=None):
        self.x, self.y, self.z, self.light = x, y, z, light

    def draw(self, color):
        Canvas.pixel(self.x, self.y, self.z, color)

    def multiply(self, vec):
        return Vector(
            self.y * vec.z - self.z * vec.y,
            self.x * vec.z - self.z * vec.x,
            self.x * vec.y - self.y * vec.x,
        )

    def normalize(self):
        length = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        if not length:
            return
        self.x /= length
        self.y /= length
        self.z /= length

    @staticmethod
    def plane_normal(a, b, c):
        ab = Vector(b.x - a.x, b.y - a.y, b.z - a.z)
        ac = Vector(c.x - a.x, c.y - a.y, c.z - a.z)
        return ab.multiply(ac)

    def __repr__(self):
        return '%s:%s:%s' % (self.x, self.y, self.z)


def _swap_if(condition, a, b):
    return (b, a) if condition else (a, b)


def line(a, b):
    if a.x == b.x and a.y == b.y:
        return [a]
    if abs(b.y - a.y) > abs(b.x - a.x):
        a, b = _swap_if(a.y > b.y, a, b)
        delta = float(b.x - a.x) / float(b.y - a.y)
        delta_z = float(b.z - a.z) / float(b.y - a.y)
        x, y, z = a.x, a.y, a.z
        while y <= b.y:
            Vector(x, y, z+2).draw((int((z-70)*1.6), 0, 0))
            x += delta
            y += 1
            z += delta_z
    else:
        a, b = _swap_if(a.x > b.x, a, b)
        delta = float(b.y - a.y) / float(b.x - a.x)
        delta_z = float(b.z - a.z) / float(b.x - a.x)
        x, y, z = a.x, a.y, a.z
        while x <= b.x:
            Vector(x, y, z+2).draw((int((z-70)*1.6), 0, 0))
            y += delta
            x += 1
            z += delta_z

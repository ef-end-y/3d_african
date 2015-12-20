import math
from PIL import Image


class Canvas(object):
    img = None

    def __init__(self, width, height, pixels, multisampling=False):
        self.img = Image.new('RGB', (width, height), 'black')
        canvas_pixels = self.img.load()
        k = 2 if multisampling else 1
        source_x = width * k
        source_y = height * k
        y1 = source_x * (source_y - k)
        delta_y = source_x * k
        for y in range(height):
            x1 = y1
            for x in range(width):
                if multisampling:
                    color = (
                        pixels[x1],
                        pixels[x1 + 1],
                        pixels[x1 + source_x],
                        pixels[x1 + source_x + 1],
                    )
                    color = (
                        int(sum(0 if len(i) != 5 else i[2] for i in color)/4),
                        int(sum(0 if len(i) != 5 else i[3] for i in color)/4),
                        int(sum(0 if len(i) != 5 else i[4] for i in color)/4),
                    )
                else:
                    color = pixels[x1]
                    color = (0, 0, 0) if len(color) != 5 else tuple(color[2:5])
                canvas_pixels[x, y] = color
                x1 += k
            y1 -= delta_y


class Vector(object):
    def __init__(self, x, y, z, light=None):
        self.x, self.y, self.z, self.light = x, y, z, light
        self.u = 0
        self.v = 0

    def __getitem__(self, index):
        if index == 0:
            return self.x
        if index == 1:
            return self.y
        if index == 2:
            return self.z
        return None

    def __add__(self, vec):
        return Vector(
            self.x + vec.x,
            self.y + vec.y,
            self.z + vec.z,
        )

    def __sub__(self, vec):
        return Vector(
            self.x - vec.x,
            self.y - vec.y,
            self.z - vec.z,
        )

    def __mul__(self, vec):
        return Vector(
            self.x * vec.x,
            self.y * vec.y,
            self.z * vec.z,
        )

    def cross(self, vec):
        return Vector(
            self.y * vec.z - self.z * vec.y,
            self.z * vec.x - self.x * vec.z,
            self.x * vec.y - self.y * vec.x,
        )

    def normalize(self):
        length = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        if not length:
            return self
        self.x /= length
        self.y /= length
        self.z /= length
        return self

    @staticmethod
    def plane_normal(a, b, c):
        ab = Vector(b.x - a.x, b.y - a.y, b.z - a.z)
        ac = Vector(c.x - a.x, c.y - a.y, c.z - a.z)
        return ab * ac

    def __repr__(self):
        return '%s:%s:%s' % (self.x, self.y, self.z)


class Matrix(object):
    def __init__(self, data):
        self.data = data

    def __mul__(self, matrix):
        x = self.data
        y = matrix.data
        return Matrix([[sum(a*b for a, b in zip(x_row, y_col)) for y_col in zip(*y)] for x_row in x])

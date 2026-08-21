import struct
import json
import math


OUTPUT = "dice.glb"

SIZE = 0.2
H = SIZE / 2.0

# Размер точки
DOT_RADIUS = SIZE * 0.08

# Насколько точки выступают над поверхностью.
# Отрицательное значение = небольшое углубление визуально.
DOT_OFFSET = SIZE * 0.003

# Качество круглых точек
DOT_SEGMENTS = 24


# ============================================================
# Массивы всей геометрии
# ============================================================

vertices = []
normals = []
indices = []
materials = []


def add_vertex(pos, normal):
    index = len(vertices) // 3

    vertices.extend(pos)
    normals.extend(normal)

    return index


def add_triangle(a, b, c, material):
    indices.extend([a, b, c])
    materials.append(material)


# ============================================================
# Куб
# ============================================================

def add_quad(p0, p1, p2, p3, normal, material):
    i0 = add_vertex(p0, normal)
    i1 = add_vertex(p1, normal)
    i2 = add_vertex(p2, normal)
    i3 = add_vertex(p3, normal)

    add_triangle(i0, i1, i2, material)
    add_triangle(i0, i2, i3, material)


# Front (+Z)
add_quad(
    (-H, -H, H),
    (H, -H, H),
    (H, H, H),
    (-H, H, H),
    (0, 0, 1),
    0
)

# Back (-Z)
add_quad(
    (H, -H, -H),
    (-H, -H, -H),
    (-H, H, -H),
    (H, H, -H),
    (0, 0, -1),
    0
)

# Right (+X)
add_quad(
    (H, -H, H),
    (H, -H, -H),
    (H, H, -H),
    (H, H, H),
    (1, 0, 0),
    0
)

# Left (-X)
add_quad(
    (-H, -H, -H),
    (-H, -H, H),
    (-H, H, H),
    (-H, H, -H),
    (-1, 0, 0),
    0
)

# Top (+Y)
add_quad(
    (-H, H, H),
    (H, H, H),
    (H, H, -H),
    (-H, H, -H),
    (0, 1, 0),
    0
)

# Bottom (-Y)
add_quad(
    (-H, -H, -H),
    (H, -H, -H),
    (H, -H, H),
    (-H, -H, H),
    (0, -1, 0),
    0
)


# ============================================================
# Пятно / точка на поверхности
# ============================================================

def add_dot(center, normal, radius=DOT_RADIUS):
    """
    Создаёт чёрный круг на поверхности кубика.

    center = центр точки
    normal = нормаль поверхности
    """

    nx, ny, nz = normal

    # Выбираем вектор, не параллельный normal
    if abs(ny) < 0.9:
        ref = (0, 1, 0)
    else:
        ref = (1, 0, 0)

    # tangent = ref x normal
    tx = ref[1] * nz - ref[2] * ny
    ty = ref[2] * nx - ref[0] * nz
    tz = ref[0] * ny - ref[1] * nx

    length = math.sqrt(tx * tx + ty * ty + tz * tz)

    tx /= length
    ty /= length
    tz /= length

    # bitangent = normal x tangent
    bx = ny * tz - nz * ty
    by = nz * tx - nx * tz
    bz = nx * ty - ny * tx

    # Центр круга немного перед поверхностью
    cx = center[0] + nx * DOT_OFFSET
    cy = center[1] + ny * DOT_OFFSET
    cz = center[2] + nz * DOT_OFFSET

    center_index = add_vertex(
        (cx, cy, cz),
        normal
    )

    ring = []

    for i in range(DOT_SEGMENTS):
        angle = 2.0 * math.pi * i / DOT_SEGMENTS

        x = (
            cx
            + tx * math.cos(angle) * radius
            + bx * math.sin(angle) * radius
        )

        y = (
            cy
            + ty * math.cos(angle) * radius
            + by * math.sin(angle) * radius
        )

        z = (
            cz
            + tz * math.cos(angle) * radius
            + bz * math.sin(angle) * radius
        )

        ring.append(
            add_vertex((x, y, z), normal)
        )

    for i in range(DOT_SEGMENTS):
        a = ring[i]
        b = ring[(i + 1) % DOT_SEGMENTS]

        add_triangle(
            center_index,
            a,
            b,
            1
        )


# ============================================================
# Расстановка точек
# ============================================================

def add_face_dots(face, number):
    """
    Добавляет number точек на указанную грань.

    face:
        front
        back
        right
        left
        top
        bottom
    """

    d = SIZE * 0.24

    positions = {
        1: [
            (0, 0)
        ],

        2: [
            (-d, d),
            (d, -d)
        ],

        3: [
            (-d, d),
            (0, 0),
            (d, -d)
        ],

        4: [
            (-d, -d),
            (-d, d),
            (d, -d),
            (d, d)
        ],

        5: [
            (-d, -d),
            (-d, d),
            (0, 0),
            (d, -d),
            (d, d)
        ],

        6: [
            (-d, -d),
            (-d, 0),
            (-d, d),
            (d, -d),
            (d, 0),
            (d, d)
        ]
    }

    for u, v in positions[number]:

        if face == "front":
            add_dot(
                (u, v, H),
                (0, 0, 1)
            )

        elif face == "back":
            add_dot(
                (-u, v, -H),
                (0, 0, -1)
            )

        elif face == "right":
            add_dot(
                (H, v, -u),
                (1, 0, 0)
            )

        elif face == "left":
            add_dot(
                (-H, v, u),
                (-1, 0, 0)
            )

        elif face == "top":
            add_dot(
                (u, H, -v),
                (0, 1, 0)
            )

        elif face == "bottom":
            add_dot(
                (u, -H, v),
                (0, -1, 0)
            )


# ============================================================
# Грани кубика
# ============================================================

# Противоположные стороны в сумме дают 7.

add_face_dots("front", 1)
add_face_dots("back", 6)

add_face_dots("right", 2)
add_face_dots("left", 5)

add_face_dots("top", 3)
add_face_dots("bottom", 4)


# ============================================================
# Разделяем индексы по материалам
# ============================================================

white_indices = []
black_indices = []

for i in range(0, len(indices), 3):
    tri = indices[i:i + 3]
    material = materials[i // 3]

    if material == 0:
        white_indices.extend(tri)
    else:
        black_indices.extend(tri)


# ============================================================
# Binary buffer
# ============================================================

position_data = struct.pack(
    "<" + "f" * len(vertices),
    *vertices
)

normal_data = struct.pack(
    "<" + "f" * len(normals),
    *normals
)

white_index_data = struct.pack(
    "<" + "H" * len(white_indices),
    *white_indices
)

black_index_data = struct.pack(
    "<" + "H" * len(black_indices),
    *black_indices
)


def align4(data):
    return data + b"\x00" * ((4 - len(data) % 4) % 4)


bin_data = bytearray()


def append(data):
    offset = len(bin_data)

    bin_data.extend(data)

    while len(bin_data) % 4:
        bin_data.append(0)

    return offset


position_offset = append(position_data)
normal_offset = append(normal_data)
white_index_offset = append(white_index_data)
black_index_offset = append(black_index_data)

bin_data = bytes(bin_data)


# ============================================================
# glTF
# ============================================================

gltf = {
    "asset": {
        "version": "2.0",
        "generator": "Pure Python Dice"
    },

    "scene": 0,

    "scenes": [
        {
            "nodes": [0]
        }
    ],

    "nodes": [
        {
            "name": "Dice",
            "mesh": 0
        }
    ],

    "meshes": [
        {
            "name": "Dice",

            "primitives": [
                {
                    "attributes": {
                        "POSITION": 0,
                        "NORMAL": 1
                    },

                    "indices": 2,
                    "material": 0,
                    "mode": 4
                },

                {
                    "attributes": {
                        "POSITION": 0,
                        "NORMAL": 1
                    },

                    "indices": 3,
                    "material": 1,
                    "mode": 4
                }
            ]
        }
    ],

    "materials": [
        {
            "name": "White",

            "pbrMetallicRoughness": {
                "baseColorFactor": [
                    0.95,
                    0.95,
                    0.95,
                    1.0
                ],

                "metallicFactor": 0.0,
                "roughnessFactor": 0.3
            }
        },

        {
            "name": "BlackDots",

            "pbrMetallicRoughness": {
                "baseColorFactor": [
                    0.005,
                    0.005,
                    0.005,
                    1.0
                ],

                "metallicFactor": 0.0,
                "roughnessFactor": 0.4
            }
        }
    ],

    "buffers": [
        {
            "byteLength": len(bin_data)
        }
    ],

    "bufferViews": [
        {
            "buffer": 0,
            "byteOffset": position_offset,
            "byteLength": len(position_data),
            "target": 34962
        },

        {
            "buffer": 0,
            "byteOffset": normal_offset,
            "byteLength": len(normal_data),
            "target": 34962
        },

        {
            "buffer": 0,
            "byteOffset": white_index_offset,
            "byteLength": len(white_index_data),
            "target": 34963
        },

        {
            "buffer": 0,
            "byteOffset": black_index_offset,
            "byteLength": len(black_index_data),
            "target": 34963
        }
    ],

    "accessors": [
        {
            "bufferView": 0,
            "componentType": 5126,
            "count": len(vertices) // 3,
            "type": "VEC3",
            "min": [
                -H,
                -H,
                -H
            ],
            "max": [
                H,
                H,
                H
            ]
        },

        {
            "bufferView": 1,
            "componentType": 5126,
            "count": len(normals) // 3,
            "type": "VEC3"
        },

        {
            "bufferView": 2,
            "componentType": 5123,
            "count": len(white_indices),
            "type": "SCALAR"
        },

        {
            "bufferView": 3,
            "componentType": 5123,
            "count": len(black_indices),
            "type": "SCALAR"
        }
    ]
}


# ============================================================
# JSON
# ============================================================

json_data = json.dumps(
    gltf,
    separators=(",", ":"),
    ensure_ascii=False
).encode("utf-8")

# В GLB JSON padding должен быть ASCII SPACE.
json_data = (
    json_data +
    b" " * ((4 - len(json_data) % 4) % 4)
)


# BIN padding
bin_data = align4(bin_data)


# ============================================================
# Chunks
# ============================================================

json_chunk = (
    struct.pack(
        "<I",
        len(json_data)
    )
    +
    struct.pack(
        "<I",
        0x4E4F534A
    )
    +
    json_data
)


bin_chunk = (
    struct.pack(
        "<I",
        len(bin_data)
    )
    +
    struct.pack(
        "<I",
        0x004E4942
    )
    +
    bin_data
)


# ============================================================
# Header
# ============================================================

total_length = (
    12
    +
    len(json_chunk)
    +
    len(bin_chunk)
)


header = struct.pack(
    "<III",
    0x46546C67,
    2,
    total_length
)


# ============================================================
# Сохранение
# ============================================================

with open(
    OUTPUT,
    "wb"
) as f:

    f.write(header)
    f.write(json_chunk)
    f.write(bin_chunk)


# ============================================================
# Проверки
# ============================================================

file_size = (
    len(header)
    +
    len(json_chunk)
    +
    len(bin_chunk)
)


assert file_size == total_length

assert total_length % 4 == 0

assert len(bin_data) == gltf["buffers"][0]["byteLength"]

assert header[0:4] == b"glTF"

assert struct.unpack_from(
    "<I",
    header,
    4
)[0] == 2

assert json_data.rstrip(
    b" "
).endswith(
    b"}"
)


print()
print("========================================")
print("GLB успешно создан!")
print("========================================")
print("Файл:", OUTPUT)
print("Размер:", total_length, "байт")
print("Размер кубика:", SIZE)
print("Вершин:", len(vertices) // 3)
print("Треугольников:", len(indices) // 3)
print("Белых треугольников:", len(white_indices) // 3)
print("Чёрных треугольников:", len(black_indices) // 3)
print("========================================")
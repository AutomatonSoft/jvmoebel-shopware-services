import math
import struct
import zlib
import zipfile


OUTPUT = "dice.usdz"

SIZE = 0.2
H = SIZE / 2.0

# Размер точки
DOT_RADIUS = SIZE * 0.08

# Небольшое выступание точки над поверхностью
DOT_OFFSET = SIZE * 0.003

# Качество круглых точек
DOT_SEGMENTS = 24


# ============================================================
# Форматирование чисел для USDA
# ============================================================

def f(value):
    return "{:.8f}".format(value)


def v3(x, y, z):
    return "({}, {}, {})".format(
        f(x),
        f(y),
        f(z)
    )


# ============================================================
# USDA
# ============================================================

usda = """#usda 1.0

(
    defaultPrim = "Dice"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "Dice"
{
    def Material "WhiteMaterial"
    {
        token outputs:surface.connect = </Dice/WhiteMaterial/Shader.outputs:surface>

        def Shader "Shader"
        {
            uniform token info:id = "UsdPreviewSurface"

            color3f inputs:diffuseColor = (0.92, 0.92, 0.92)
            float inputs:roughness = 0.32
            float inputs:metallic = 0.0

            token outputs:surface
        }
    }

    def Material "BlackMaterial"
    {
        token outputs:surface.connect = </Dice/BlackMaterial/Shader.outputs:surface>

        def Shader "Shader"
        {
            uniform token info:id = "UsdPreviewSurface"

            color3f inputs:diffuseColor = (0.003, 0.003, 0.003)
            float inputs:roughness = 0.4
            float inputs:metallic = 0.0

            token outputs:surface
        }
    }

"""


# ============================================================
# Куб
# ============================================================

cube_vertices = [
    # Front
    (-H, -H,  H),
    ( H, -H,  H),
    ( H,  H,  H),
    (-H,  H,  H),

    # Back
    ( H, -H, -H),
    (-H, -H, -H),
    (-H,  H, -H),
    ( H,  H, -H),

    # Right
    ( H, -H,  H),
    ( H, -H, -H),
    ( H,  H, -H),
    ( H,  H,  H),

    # Left
    (-H, -H, -H),
    (-H, -H,  H),
    (-H,  H,  H),
    (-H,  H, -H),

    # Top
    (-H,  H,  H),
    ( H,  H,  H),
    ( H,  H, -H),
    (-H,  H, -H),

    # Bottom
    (-H, -H, -H),
    ( H, -H, -H),
    ( H, -H,  H),
    (-H, -H,  H),
]


cube_faces = [
    (0, 1, 2, 3),
    (4, 5, 6, 7),
    (8, 9, 10, 11),
    (12, 13, 14, 15),
    (16, 17, 18, 19),
    (20, 21, 22, 23),
]


usda += """    def Mesh "Cube"
    {
        uniform token subdivisionScheme = "none"

        int[] faceVertexCounts = [
            4, 4, 4, 4, 4, 4
        ]

        int[] faceVertexIndices = [
"""


for face in cube_faces:
    usda += "            "
    usda += ", ".join(
        str(i)
        for i in face
    )
    usda += ",\n"


usda += """        ]

        point3f[] points = [
"""


for x, y, z in cube_vertices:
    usda += "            "
    usda += v3(x, y, z)
    usda += ",\n"


usda += """        ]

        rel material:binding = </Dice/WhiteMaterial>
    }

"""


# ============================================================
# Раскладка точек
# ============================================================

def positions(number):

    d = SIZE * 0.24

    patterns = {
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

    return patterns[number]


# ============================================================
# Создание круглой точки
# ============================================================

dot_number = 0


def make_dot(center, normal):

    global dot_number

    cx, cy, cz = center
    nx, ny, nz = normal

    name = "Dot_{:02d}".format(
        dot_number
    )

    dot_number += 1

    # --------------------------------------------------------
    # Локальная система координат
    # --------------------------------------------------------

    if abs(ny) < 0.9:
        reference = (
            0.0,
            1.0,
            0.0
        )
    else:
        reference = (
            1.0,
            0.0,
            0.0
        )

    # tangent = reference × normal

    tx = (
        reference[1] * nz
        -
        reference[2] * ny
    )

    ty = (
        reference[2] * nx
        -
        reference[0] * nz
    )

    tz = (
        reference[0] * ny
        -
        reference[1] * nx
    )

    length = math.sqrt(
        tx * tx +
        ty * ty +
        tz * tz
    )

    tx /= length
    ty /= length
    tz /= length

    # bitangent = normal × tangent

    bx = (
        ny * tz -
        nz * ty
    )

    by = (
        nz * tx -
        nx * tz
    )

    bz = (
        nx * ty -
        ny * tx
    )

    # --------------------------------------------------------
    # Центр + кольцо
    # --------------------------------------------------------

    points = [
        (
            cx + nx * DOT_OFFSET,
            cy + ny * DOT_OFFSET,
            cz + nz * DOT_OFFSET
        )
    ]

    for i in range(DOT_SEGMENTS):

        angle = (
            2.0 *
            math.pi *
            i /
            DOT_SEGMENTS
        )

        c = math.cos(angle)
        s = math.sin(angle)

        points.append(
            (
                cx
                + nx * DOT_OFFSET
                + tx * c * DOT_RADIUS
                + bx * s * DOT_RADIUS,

                cy
                + ny * DOT_OFFSET
                + ty * c * DOT_RADIUS
                + by * s * DOT_RADIUS,

                cz
                + nz * DOT_OFFSET
                + tz * c * DOT_RADIUS
                + bz * s * DOT_RADIUS
            )
        )

    # --------------------------------------------------------
    # Mesh точки
    # --------------------------------------------------------

    result = '    def Mesh "{}"\n'.format(
        name
    )

    result += """    {
        uniform token subdivisionScheme = "none"

        int[] faceVertexCounts = [
"""

    for _ in range(DOT_SEGMENTS):
        result += "            3,\n"

    result += """        ]

        int[] faceVertexIndices = [
"""

    for i in range(DOT_SEGMENTS):

        a = 0
        b = i + 1
        c = ((i + 1) % DOT_SEGMENTS) + 1

        result += "            {}, {}, {},\n".format(
            a,
            b,
            c
        )

    result += """        ]

        point3f[] points = [
"""

    for x, y, z in points:

        result += "            "
        result += v3(x, y, z)
        result += ",\n"

    result += """        ]

        rel material:binding = </Dice/BlackMaterial>
    }

"""

    return result


# ============================================================
# Точки на гранях
# ============================================================

def add_face(face, number):

    result = ""

    for u, v in positions(number):

        if face == "front":

            center = (
                u,
                v,
                H
            )

            normal = (
                0,
                0,
                1
            )

        elif face == "back":

            center = (
                -u,
                v,
                -H
            )

            normal = (
                0,
                0,
                -1
            )

        elif face == "right":

            center = (
                H,
                v,
                -u
            )

            normal = (
                1,
                0,
                0
            )

        elif face == "left":

            center = (
                -H,
                v,
                u
            )

            normal = (
                -1,
                0,
                0
            )

        elif face == "top":

            center = (
                u,
                H,
                -v
            )

            normal = (
                0,
                1,
                0
            )

        elif face == "bottom":

            center = (
                u,
                -H,
                v
            )

            normal = (
                0,
                -1,
                0
            )

        else:
            raise ValueError(face)

        result += make_dot(
            center,
            normal
        )

    return result


# ============================================================
# Номера граней
# ============================================================

usda += add_face(
    "front",
    1
)

usda += add_face(
    "back",
    6
)

usda += add_face(
    "right",
    2
)

usda += add_face(
    "left",
    5
)

usda += add_face(
    "top",
    3
)

usda += add_face(
    "bottom",
    4
)


# ============================================================
# Закрываем Xform
# ============================================================

usda += "}\n"


# ============================================================
# Создание USDZ
# ============================================================

def create_usdz(usda_data, filename):

    data = usda_data.encode(
        "utf-8"
    )

    filename_bytes = b"dice.usda"

    crc = zlib.crc32(
        data
    ) & 0xffffffff

    size = len(data)

    # --------------------------------------------------------
    # ZIP Local File Header
    # --------------------------------------------------------

    local_header_size = 30

    # Нужно подобрать размер extra field так,
    # чтобы начало USDA было выровнено на 64 байта.

    base = (
        local_header_size
        +
        len(filename_bytes)
    )

    extra_size = (
        64 -
        (base % 64)
    ) % 64

    if extra_size < 4:
        extra_size += 64

    extra_payload_size = (
        extra_size - 4
    )

    extra = struct.pack(
        "<HH",
        0xFFFF,
        extra_payload_size
    )

    extra += b"\x00" * extra_payload_size

    local_header = struct.pack(
        "<IHHHHHIIIHH",
        0x04034B50,
        20,
        0,
        0,
        0,
        0,
        crc,
        size,
        size,
        len(filename_bytes),
        len(extra)
    )

    local_file = (
        local_header
        +
        filename_bytes
        +
        extra
        +
        data
    )

    # --------------------------------------------------------
    # Проверяем выравнивание данных USDA
    # --------------------------------------------------------

    data_offset = (
        len(local_header)
        +
        len(filename_bytes)
        +
        len(extra)
    )

    assert data_offset % 64 == 0

    # --------------------------------------------------------
    # Central Directory
    # --------------------------------------------------------

    central_offset = len(
        local_file
    )

    central_header = struct.pack(
        "<IHHHHHHIIIHHHHHII",
        0x02014B50,
        20,
        20,
        0,
        0,
        0,
        0,
        crc,
        size,
        size,
        len(filename_bytes),
        len(extra),
        0,
        0,
        0,
        0,
        0
    )

    central_directory = (
        central_header
        +
        filename_bytes
        +
        extra
    )

    # --------------------------------------------------------
    # End of Central Directory
    # --------------------------------------------------------

    end_record = struct.pack(
        "<IHHHHIIH",
        0x06054B50,
        0,
        0,
        1,
        1,
        len(central_directory),
        central_offset,
        0
    )

    # --------------------------------------------------------
    # Итоговый USDZ
    # --------------------------------------------------------

    result = (
        local_file
        +
        central_directory
        +
        end_record
    )

    with open(
        filename,
        "wb"
    ) as file:

        file.write(
            result
        )

    return result


# ============================================================
# Генерация
# ============================================================

result = create_usdz(
    usda,
    OUTPUT
)


# ============================================================
# Проверка созданного архива
# ============================================================

with zipfile.ZipFile(
    OUTPUT,
    "r"
) as archive:

    assert archive.testzip() is None

    assert archive.namelist() == [
        "dice.usda"
    ]

    info = archive.getinfo(
        "dice.usda"
    )

    assert info.compress_type == (
        zipfile.ZIP_STORED
    )


# ============================================================
# Информация
# ============================================================

print()
print("========================================")
print("USDZ успешно создан!")
print("========================================")
print("Файл:", OUTPUT)
print("Размер:", len(result), "байт")
print("Размер кубика:", SIZE)
print("Радиус точек:", DOT_RADIUS)
print("Количество точек:", dot_number)
print("========================================")
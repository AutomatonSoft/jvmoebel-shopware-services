# AR API

AR API предназначен для загрузки, хранения, проверки наличия и управления 3D-моделями для Augmented Reality.

Base URL:

```text
/api/v1/ar/models
```

Поддерживаемые форматы моделей:

* `GLB`
* `USDZ`

Максимальный размер одного AR-файла по умолчанию — **15 MB**.

Ограничение HTTP request body по умолчанию — **16 MB**. Оно немного больше ограничения файла, чтобы учитывать `multipart/form-data` overhead.

Настройки:

```env
AR_MAX_FILE_SIZE=15728640
AR_MAX_BODY_SIZE=16777216
```

Если значения не заданы, используются значения по умолчанию из `app/core/config.py`.

---

## AR model response

При запросе информации о модели API возвращает один из двух вариантов ответа.

### Model available

Если AR-модель существует, имеет статус `active` и физический файл существует в storage:

```json
{
  "sku": "BRAUSSET_black",
  "available": true,
  "format": "glb",
  "file_url": "/api/v1/ar/models/BRAUSSET_black/file",
  "width": 2.4,
  "height": 0.8,
  "depth": 0.6,
  "unit": "m"
}
```

Значение:

```json
"available": true
```

означает, что AR-модель существует, активна и доступна для скачивания.

`file_url` содержит endpoint, через который можно получить сам файл модели.

Размеры (`width`, `height`, `depth`) в response всегда указаны в метрах:

```json
"unit": "m"
```

---

### Model unavailable

Если AR-модель недоступна:

```json
{
  "sku": "UNKNOWN_SKU",
  "available": false
}
```

`available: false` возвращается в следующих случаях:

* AR-модель отсутствует в базе данных;
* AR-модель существует, но имеет статус `not_active`;
* AR-модель существует и активна, но физический файл отсутствует в storage.

В этом случае поля `format`, `file_url`, `width`, `height`, `depth` отсутствуют.

Важно: отсутствие доступной AR-модели не считается ошибкой HTTP. Endpoint проверки наличия возвращает `200 OK` с:

```json
"available": false
```

---

# GET /api/v1/ar/models/{sku}

Получить информацию о наличии AR-модели и её метаданные.

### Example

```bash
curl http://localhost:8000/api/v1/ar/models/BRAUSSET_black
```

### Response: model exists

```http
HTTP/1.1 200 OK
```

```json
{
  "sku": "BRAUSSET_black",
  "available": true,
  "format": "glb",
  "file_url": "/api/v1/ar/models/BRAUSSET_black/file",
  "width": 2.4,
  "height": 0.8,
  "depth": 0.6,
  "unit": "m"
}
```

### Response: model does not exist

```http
HTTP/1.1 200 OK
```

```json
{
  "sku": "UNKNOWN_SKU",
  "available": false
}
```

### Errors

| Status | Description        |
| ------ | ------------------ |
| `422`  | Invalid SKU format |

SKU может содержать только:

* латинские буквы;
* цифры;
* `_`;
* `-`.

SKU не должен содержать:

* `/`;
* `\`;
* `..`;
* null bytes.

---

# GET /api/v1/ar/models/{sku}/file

Скачать файл AR-модели.

Endpoint возвращает исходный файл модели.

### Example

```bash
curl -o model.glb \
  http://localhost:8000/api/v1/ar/models/BRAUSSET_black/file
```

Для USDZ:

```bash
curl -o model.usdz \
  http://localhost:8000/api/v1/ar/models/LOW_POLY_CAR/file
```

### Errors

| Status | Description                        |
| ------ | ---------------------------------- |
| `404`  | AR model или файл модели не найден |
| `422`  | Invalid SKU format                 |

---

# POST /api/v1/ar/models/{sku}

Создать новую AR-модель.

Для endpoint требуется Bearer authentication.

### Authentication

Передача API key:

```http
Authorization: Bearer <AR_WRITE_API_KEY>
```

API key хранится в environment variable:

```env
AR_WRITE_API_KEY=your-secret-key
```

### Request

Request должен быть `multipart/form-data`.

Обязательные поля:

| Field    | Type    | Description        |
| -------- | ------- | ------------------ |
| `file`   | file    | GLB или USDZ файл  |
| `width`  | decimal | Ширина             |
| `height` | decimal | Высота             |
| `depth`  | decimal | Глубина            |
| `unit`   | string  | `m`, `cm` или `mm` |

`width`, `height` и `depth` должны быть больше `0`.

Допустимые значения `unit`:

```text
m
cm
mm
```

### Example

```bash
curl -X POST \
  http://localhost:8000/api/v1/ar/models/BRAUSSET_black \
  -H "Authorization: Bearer $AR_WRITE_API_KEY" \
  -F "file=@./BRAUSSET_black.glb" \
  -F "width=240" \
  -F "height=80" \
  -F "depth=60" \
  -F "unit=cm"
```

При сохранении размеры автоматически преобразуются в метры.

Например:

```text
240 cm → 2.4 m
80 cm  → 0.8 m
60 cm  → 0.6 m
```

### Response

```http
HTTP/1.1 201 Created
```

```json
{
  "sku": "BRAUSSET_black",
  "available": true,
  "format": "glb",
  "file_url": "/api/v1/ar/models/BRAUSSET_black/file",
  "width": 2.4,
  "height": 0.8,
  "depth": 0.6,
  "unit": "m"
}
```

### Errors

| Status | Description                                        |
| ------ | -------------------------------------------------- |
| `400`  | Unsupported format, file too large or invalid file |
| `401`  | Authentication required or invalid token           |
| `409`  | AR model with this SKU already exists              |
| `413`  | HTTP request body exceeds `AR_MAX_BODY_SIZE`       |
| `422`  | Invalid SKU format or invalid request parameters   |

Возможные ошибки валидации AR-файла:

```text
Unsupported AR model format. Supported formats: GLB, USDZ
```

```text
AR model file is too large. Maximum file size is 15 MB
```

```text
AR model file content does not match the declared format
```

Ошибки `width`, `height`, `depth` и `unit` относятся к валидации request parameters и приводят к `422`.

---

# PUT /api/v1/ar/models/{sku}

Обновить существующую AR-модель.

PUT используется для замены существующей модели.

Требуется Bearer authentication.

Если AR-модель с указанным SKU не существует, API возвращает `404`.

### Example

```bash
curl -X PUT \
  http://localhost:8000/api/v1/ar/models/BRAUSSET_black \
  -H "Authorization: Bearer $AR_WRITE_API_KEY" \
  -F "file=@./BRAUSSET_black_new.glb" \
  -F "width=240" \
  -F "height=80" \
  -F "depth=60" \
  -F "unit=cm"
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "sku": "BRAUSSET_black",
  "available": true,
  "format": "glb",
  "file_url": "/api/v1/ar/models/BRAUSSET_black/file",
  "width": 2.4,
  "height": 0.8,
  "depth": 0.6,
  "unit": "m"
}
```

### Errors

| Status | Description                                        |
| ------ | -------------------------------------------------- |
| `400`  | Unsupported format, file too large or invalid file |
| `401`  | Authentication required or invalid token           |
| `404`  | AR model not found                                 |
| `413`  | HTTP request body exceeds `AR_MAX_BODY_SIZE`       |
| `422`  | Invalid SKU format or invalid request parameters   |

---

# PATCH /api/v1/ar/models/{sku}/status

Изменить статус существующей AR-модели.

Требуется Bearer authentication.

Допустимые значения:

```text
active
not_active
```

### Request

```json
{
  "status": "active"
}
```

### Example

```bash
curl -X PATCH \
  http://localhost:8000/api/v1/ar/models/BRAUSSET_black/status \
  -H "Authorization: Bearer $AR_WRITE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status":"active"}'
```

### Response

```http
HTTP/1.1 200 OK
```

```json
{
  "sku": "BRAUSSET_black",
  "status": "active"
}
```

Если статус модели изменён на `not_active`, следующий запрос:

```http
GET /api/v1/ar/models/BRAUSSET_black
```

вернёт:

```http
HTTP/1.1 200 OK
```

```json
{
  "sku": "BRAUSSET_black",
  "available": false
}
```

При этом запрос файла:

```http
GET /api/v1/ar/models/BRAUSSET_black/file
```

вернёт:

```http
HTTP/1.1 404 Not Found
```

### Errors

| Status | Description                              |
| ------ | ---------------------------------------- |
| `401`  | Authentication required or invalid token |
| `404`  | AR model not found                       |
| `422`  | Invalid SKU format or invalid status     |

---

# DELETE /api/v1/ar/models/{sku}

Удалить AR-модель.

Требуется Bearer authentication.

Сначала удаляется запись AR-модели из базы данных и выполняется commit транзакции. После этого API удаляет физический файл из storage.

### Example

```bash
curl -X DELETE \
  http://localhost:8000/api/v1/ar/models/BRAUSSET_black \
  -H "Authorization: Bearer $AR_WRITE_API_KEY"
```

### Response

```http
HTTP/1.1 204 No Content
```

Если удаление физического файла после успешного удаления записи из базы данных не удалось, API всё равно возвращает `204`. Ошибка записывается в application log, а оставшийся файл может потребовать ручной очистки.

### Errors

| Status | Description                              |
| ------ | ---------------------------------------- |
| `401`  | Authentication required or invalid token |
| `404`  | AR model not found                       |
| `422`  | Invalid SKU format                       |

---

# Authentication

Write operations требуют Bearer API key:

```text
POST   /api/v1/ar/models/{sku}
PUT    /api/v1/ar/models/{sku}
PATCH  /api/v1/ar/models/{sku}/status
DELETE /api/v1/ar/models/{sku}
```

Read operations authentication не требуют:

```text
GET /api/v1/ar/models/{sku}
GET /api/v1/ar/models/{sku}/file
```

Пример:

```http
Authorization: Bearer <AR_WRITE_API_KEY>
```

При отсутствии credentials API возвращает:

```http
401 Unauthorized
```

При неверном token:

```http
401 Unauthorized
```

Возможны следующие authentication errors:

```text
Authentication required
```

```text
Invalid authentication scheme
```

```text
Invalid authentication token
```

---

# AR API status flow

Типичный flow для клиента:

```text
GET /api/v1/ar/models/{sku}
             │
             ├── available: true
             │        │
             │        └── GET file_url
             │
             └── available: false
                      │
                      ├── AR model отсутствует
                      ├── AR model имеет status=not_active
                      └── AR model file отсутствует
```

Например:

```bash
curl http://localhost:8000/api/v1/ar/models/BRAUSSET_black
```

Если модель существует, активна и файл доступен:

```json
{
  "sku": "BRAUSSET_black",
  "available": true,
  "format": "glb",
  "file_url": "/api/v1/ar/models/BRAUSSET_black/file",
  "width": 2.4,
  "height": 0.8,
  "depth": 0.6,
  "unit": "m"
}
```

Если модели нет, она неактивна или её файл отсутствует:

```json
{
  "sku": "BRAUSSET_black",
  "available": false
}
```

Таким образом, клиенту не нужно интерпретировать `404` для проверки наличия AR-модели: отсутствие доступной модели представляется обычным успешным ответом с `available: false`.

`404` используется для получения самого файла и для write-операций, когда запрашиваемая AR-модель не существует.

---

# AR API error summary

| HTTP status | Когда возникает                                                               |
| ----------- | ----------------------------------------------------------------------------- |
| `200`       | Успешный GET/PATCH/PUT                                                        |
| `201`       | AR-модель успешно создана                                                     |
| `204`       | AR-модель успешно удалена из базы данных                                      |
| `400`       | Некорректный AR-файл, неподдерживаемый формат или превышение размера AR-файла |
| `401`       | Отсутствует или неверный Bearer token                                         |
| `404`       | AR-модель или файл не найден                                                  |
| `409`       | AR-модель с таким SKU уже существует                                          |
| `413`       | HTTP request body превышает `AR_MAX_BODY_SIZE`                                |
| `422`       | Некорректный SKU или параметры request                                        |
| `500`       | Необработанная внутренняя ошибка                                              |
| `503`       | Database schema не готова, например не применены Alembic migrations           |

Для `POST` и `PUT` ошибки `width`, `height`, `depth` и `unit` относятся к валидации входных параметров и возвращают `422`.

Для проверки точного формата JSON error response следует ориентироваться на глобальные exception handlers приложения (`app/core/errors_handlers.py`).

При превышении `AR_MAX_BODY_SIZE` middleware возвращает:

```json
{
  "detail": "Request body too large"
}
```

# E-Commerce Marketplace API

API REST modular para gestión de productos, carrito de compras y órdenes. Construida con Django REST Framework siguiendo una arquitectura limpia con separación en servicios y selectores (CQRS-lite).

## Stack

| Capa        | Tecnología                                                  |
| ----------- | ----------------------------------------------------------- |
| Backend     | Django 6 + Django REST Framework 3.17                       |
| Base Datos  | PostgreSQL (vía psycopg[binary] 3)                          |
| Cache       | Redis (LocMemCache por defecto en desarrollo)               |
| Auth        | JWT (SimpleJWT con refresh token rotation)                  |
| Documentación | OpenAPI 3 (drf-spectacular) — Swagger UI y Redoc          |
| Tests       | pytest + factory-boy + coverage                             |

## Arquitectura

La API sigue un patrón **Service/Selector** (CQRS-lite):

```
Request → View → Serializer → Service (escritura)
                              → Selector (lectura)
```

Cada app es autónoma y contiene sus propios modelos, vistas, serializadores, servicios y selectores.

```
ecommerce-api/
├── products/       # Catálogo de productos (CRUD admin, lectura pública)
├── cart/           # Carrito de compras por usuario anónimo/autenticado
├── orders/         # Órdenes con snapshots de precios y manejo de stock
├── users/          # Registro y perfil de usuarios
├── config/         # Configuración central (settings, urls, excepciones)
└── tests/          # Tests E2E y de autenticación
```

## Endpoints

| Método | Endpoint                     | Auth     | Descripción                        |
| ------ | ---------------------------- | -------- | ---------------------------------- |
| POST   | `/api/v1/auth/register/`     | No       | Registrar nuevo usuario            |
| POST   | `/api/v1/auth/token/`        | No       | Obtener JWT token (login)          |
| POST   | `/api/v1/auth/token/refresh/`| No       | Refrescar JWT token                |
| GET    | `/api/v1/auth/me/`           | Bearer   | Información del usuario autenticado |
| GET    | `/api/v1/products/`          | No*      | Listar productos (paginado)        |
| GET    | `/api/v1/products/{id}/`     | No*      | Detalle de producto                |
| POST   | `/api/v1/products/`          | Admin    | Crear producto                     |
| PATCH  | `/api/v1/products/{id}/`     | Admin    | Actualizar producto                |
| DELETE | `/api/v1/products/{id}/`     | Admin    | Desactivar producto (soft delete)  |
| GET    | `/api/v1/products/{id}/stock/`| No*     | Verificar stock disponible         |
| GET    | `/api/v1/cart/`              | Mixto†   | Resumen del carrito                |
| POST   | `/api/v1/cart/add/`          | Mixto†   | Agregar producto al carrito        |
| PATCH  | `/api/v1/cart/items/{id}/`   | Mixto†   | Actualizar cantidad de un item     |
| DELETE | `/api/v1/cart/items/{id}/`   | Mixto†   | Eliminar item del carrito          |
| POST   | `/api/v1/cart/clear/`        | Mixto†   | Vaciar carrito                     |
| GET    | `/api/v1/orders/`            | Bearer   | Listar órdenes del usuario         |
| POST   | `/api/v1/orders/`            | Bearer   | Crear orden desde el carrito       |
| GET    | `/api/v1/orders/{id}/`       | Bearer   | Detalle de orden                   |
| PATCH  | `/api/v1/orders/{id}/cancel/`| Bearer   | Cancelar orden propia              |
| PATCH  | `/api/v1/orders/{id}/status/`| Admin    | Actualizar estado de una orden     |

\* Lectura pública, escritura solo admin.
† Anónimo: carrito por sesión. Autenticado: carrito propio del usuario.

## Primeros pasos

### 1. Clonar e instalar dependencias

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env según tu entorno (al menos DB_NAME, DB_USER, DB_PASSWORD)
```

### 3. Crear la base de datos

```bash
createdb ecommerce_db
```

### 4. Migrar y crear superusuario

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Iniciar servidor de desarrollo

```bash
python manage.py runserver
```

La API corre en `http://localhost:8000/api/v1/`.

## Tests

```bash
# Ejecutar todos los tests con cobertura
pytest

# Solo tests unitarios
pytest -m unit

# Solo tests de integración
pytest -m integration

# Tests de una app específica
pytest products/tests/

# Reporte HTML de cobertura
# Se genera en htmlcov/ (abrir index.html en el navegador)
```

## Documentación interactiva

Con el servidor corriendo:

- **Swagger UI:** http://localhost:8000/api/docs/
- **Redoc:** http://localhost:8000/api/redoc/
- **Schema OpenAPI:** http://localhost:8000/api/schema/

## Comandos útiles

```bash
# Recopilar archivos estáticos
python manage.py collectstatic

# Crear migraciones
python manage.py makemigrations

# Ver SQL de las migraciones
python manage.py sqlmigrate products 0001

# Shell de Django
python manage.py shell

# Dump/Load data (fixtures)
python manage.py dumpdata products --indent 2 > products/fixtures/data.json
python manage.py loaddata products/fixtures/data.json
```

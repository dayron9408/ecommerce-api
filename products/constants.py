# Rango de precios permitidos
MIN_PRODUCT_PRICE = 0.01
MAX_PRODUCT_PRICE = 999999.99

# Longitud maxima de campos
MAX_PRODUCT_NAME_LENGTH = 255
MAX_SKU_LENGTH = 50

# Valores por defecto
DEFAULT_PRODUCT_STOCK = 0

# Cache timeouts (en segundos)
PRODUCT_CACHE_TIMEOUT = 300  # 5 minutos
PRODUCT_LIST_CACHE_TIMEOUT = 60  # 1 minuto

# Imagenes de productos
PRODUCT_IMAGE_MAX_SIZE_MB = 2  # 2MB maximo
PRODUCT_IMAGE_ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp']
PRODUCT_IMAGE_UPLOAD_PATH = 'products/images/'

from django.apps import AppConfig


class ProductsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'products'
    verbose_name = 'Servicio de Productos'

    def ready(self):
        """Importar senales y registrar handlers al iniciar la app."""
        pass  # No signals needed yet

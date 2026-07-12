# Entry point de FastAPI. Cada módulo monta aquí su router cuando implemente su infrastructure/http.
from fastapi import FastAPI

app = FastAPI(title="Tienda Sistema API")

# TODO: app.include_router(...) por cada módulo (modulo_a_seguridad, modulo_b_inventario, modulo_c_ventas, modulo_d_documentos)

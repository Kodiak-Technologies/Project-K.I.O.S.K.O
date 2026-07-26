# Dependencias de FastAPI del Módulo B.
# El patrón del proyecto es que los routers importan las factorías desde
# `module_container` y llaman a la factoría con `Depends(get_db)` adentro.
# Este archivo queda para re-exports opcionales y compatibilidad.
from app.modules.modulo_b_inventario import module_container as contenedor


# Re-exports de factorías (uso: Depends(contenedor.x_usecase)).
__all__ = ["contenedor"]

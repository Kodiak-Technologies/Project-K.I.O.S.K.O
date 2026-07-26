# DTOs Pydantic (request/response) del módulo de seguridad.
# Validación de FORMATO aquí; las reglas de NEGOCIO viven en domain/application.
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.modules.modulo_a_seguridad.domain.entities import (
    ConfiguracionNegocio,
    Permiso,
    RegistroAuditoria,
    Rol,
    Usuario,
)


# ---------- Auth ----------
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=30)
    password: str = Field(min_length=1, max_length=200)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=200)


class UsuarioResponse(BaseModel):
    id: int
    username: str
    nombre: str
    rol_id: int
    rol: str
    activo: bool
    debe_cambiar_password: bool
    ultimo_acceso: datetime | None
    created_at: datetime | None

    @classmethod
    def desde_entidad(cls, u: Usuario) -> "UsuarioResponse":
        return cls(
            id=u.id, username=u.username, nombre=u.nombre, rol_id=u.rol_id, rol=u.rol_nombre,
            activo=u.activo, debe_cambiar_password=u.debe_cambiar_password,
            ultimo_acceso=u.ultimo_acceso, created_at=u.created_at,
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


# ---------- Usuarios ----------
class CrearUsuarioRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    nombre: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=200)
    rol_id: int
    forzar_cambio_password: bool = True


class EditarUsuarioRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    rol_id: int | None = None


class CambiarEstadoRequest(BaseModel):
    activo: bool


class ResetearPasswordRequest(BaseModel):
    password_nueva: str = Field(min_length=8, max_length=200)
    forzar_cambio: bool = True


class EliminarUsuarioRequest(BaseModel):
    motivo: str | None = None


# ---------- Roles y permisos ----------
class PermisoResponse(BaseModel):
    id: int
    codigo: str
    descripcion: str

    @classmethod
    def desde_entidad(cls, p: Permiso) -> "PermisoResponse":
        return cls(id=p.id, codigo=p.codigo, descripcion=p.descripcion)


class RolResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str

    @classmethod
    def desde_entidad(cls, r: Rol) -> "RolResponse":
        return cls(id=r.id, nombre=r.nombre, descripcion=r.descripcion)


class AsignarPermisosRequest(BaseModel):
    permisos: list[str]  # códigos, ej. ["ventas.registrar", "inventario.ver"]


# ---------- Bitácora ----------
class RegistroBitacoraResponse(BaseModel):
    id: int
    usuario_id: int | None
    rol: str
    accion: str
    entidad: str
    entidad_id: str | None
    valor_anterior: dict[str, Any] | None
    valor_nuevo: dict[str, Any] | None
    motivo: str | None
    ip: str
    user_agent: str
    created_at: datetime | None

    @classmethod
    def desde_entidad(cls, r: RegistroAuditoria) -> "RegistroBitacoraResponse":
        return cls(
            id=r.id, usuario_id=r.usuario_id, rol=r.rol, accion=r.accion,
            entidad=r.entidad, entidad_id=r.entidad_id,
            valor_anterior=r.valor_anterior, valor_nuevo=r.valor_nuevo,
            motivo=r.motivo, ip=r.ip, user_agent=r.user_agent, created_at=r.created_at,
        )


class BitacoraPaginadaResponse(BaseModel):
    registros: list[RegistroBitacoraResponse]
    total: int
    pagina: int
    tamano_pagina: int
    # Cursor de la última fila devuelta: mandalo como `cursor` para pedir el
    # tramo siguiente sin que las inserciones de arriba corran las páginas.
    # `None` cuando no hay más registros.
    siguiente_cursor: str | None = None


# ---------- Configuración ----------
class ConfiguracionResponse(BaseModel):
    nombre_negocio: str
    logo_url: str
    color_primario: str
    color_secundario: str
    tipografia: str
    session_ttl_admin_minutos: int
    session_ttl_cajero_minutos: int
    max_intentos_login: int
    minutos_bloqueo: int
    updated_at: datetime | None

    @classmethod
    def desde_entidad(cls, c: ConfiguracionNegocio) -> "ConfiguracionResponse":
        return cls(
            nombre_negocio=c.nombre_negocio, logo_url=c.logo_url,
            color_primario=c.color_primario, color_secundario=c.color_secundario,
            tipografia=c.tipografia,
            session_ttl_admin_minutos=c.session_ttl_admin_minutos,
            session_ttl_cajero_minutos=c.session_ttl_cajero_minutos,
            max_intentos_login=c.max_intentos_login, minutos_bloqueo=c.minutos_bloqueo,
            updated_at=c.updated_at,
        )


class ActualizarConfiguracionRequest(BaseModel):
    nombre_negocio: str | None = Field(default=None, max_length=120)
    logo_url: str | None = None
    color_primario: str | None = Field(default=None, max_length=20)
    color_secundario: str | None = Field(default=None, max_length=20)
    tipografia: str | None = Field(default=None, max_length=60)
    session_ttl_admin_minutos: int | None = Field(default=None, gt=0)
    session_ttl_cajero_minutos: int | None = Field(default=None, gt=0)
    max_intentos_login: int | None = Field(default=None, gt=0, le=10)
    minutos_bloqueo: int | None = Field(default=None, gt=0, le=1440)

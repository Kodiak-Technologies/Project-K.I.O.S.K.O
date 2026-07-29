# Entidades de dominio del módulo de seguridad. Python puro: sin FastAPI ni SQLAlchemy.
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


@dataclass
class Rol:
    id: int
    nombre: str  # "ADMIN" | "CAJERO"
    descripcion: str = ""


@dataclass
class Permiso:
    id: int
    codigo: str  # ej. "ventas.anular"
    descripcion: str = ""


@dataclass
class Usuario:
    id: int | None
    username: str
    nombre: str
    password_hash: str
    rol_id: int
    rol_nombre: str = ""
    activo: bool = True
    debe_cambiar_password: bool = False
    intentos_fallidos: int = 0
    bloqueado_hasta: datetime | None = None
    ultimo_acceso: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_by: int | None = None

    @property
    def eliminado(self) -> bool:
        return self.deleted_at is not None

    def esta_bloqueado(self, ahora: datetime | None = None) -> bool:
        ahora = ahora or datetime.now(timezone.utc)
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > ahora

    def puede_iniciar_sesion(self) -> bool:
        return self.activo and not self.eliminado


@dataclass
class SesionToken:
    """Un refresh token vigente. Solo se guarda el hash, nunca el token en claro."""

    id: int | None
    usuario_id: int
    refresh_token_hash: str
    ip: str
    user_agent: str
    expira_en: datetime
    revocada: bool = False
    created_at: datetime | None = None

    def es_valida(self, ahora: datetime | None = None) -> bool:
        ahora = ahora or datetime.now(timezone.utc)
        return not self.revocada and self.expira_en > ahora


@dataclass
class RegistroAuditoria:
    """Un evento inmutable de la bitácora: quién hizo qué, cuándo y con qué valores."""

    id: int | None
    usuario_id: int | None  # None en login fallido de username inexistente
    rol: str
    accion: str  # ej. "login_exitoso", "usuario_creado"
    entidad: str  # ej. "usuarios", "ventas"
    entidad_id: str | None = None
    valor_anterior: dict[str, Any] | None = None
    valor_nuevo: dict[str, Any] | None = None
    motivo: str | None = None
    ip: str = ""
    user_agent: str = ""
    created_at: datetime | None = None


@dataclass
class ConfiguracionNegocio:
    """Fila única editable por ADMIN. Los TTL y límites de login viven aquí para
    poder ajustarlos sin redeploy."""

    id: int
    nombre_negocio: str
    logo_url: str = ""
    color_primario: str = "#2563eb"
    color_secundario: str = "#f59e0b"
    tipografia: str = "Inter"
    session_ttl_admin_minutos: int = 43200  # 30 días
    session_ttl_cajero_minutos: int = 720  # 12 horas
    max_intentos_login: int = 3
    minutos_bloqueo: int = 15
    #: % de ganancia por defecto al crear un producto desde un ingreso.
    margen_ganancia_default: Decimal = Decimal("20")
    updated_by: int | None = None
    updated_at: datetime | None = None

    def ttl_para_rol(self, rol_nombre: str) -> int:
        return self.session_ttl_admin_minutos if rol_nombre == "ADMIN" else self.session_ttl_cajero_minutos

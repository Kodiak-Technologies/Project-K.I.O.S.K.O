// Tipos/DTOs del módulo de seguridad (espejo de los schemas Pydantic del backend).

export interface Usuario {
  id: number;
  username: string;
  nombre: string;
  rol_id: number;
  rol: "ADMIN" | "CAJERO" | string;
  activo: boolean;
  debe_cambiar_password: boolean;
  ultimo_acceso: string | null;
  created_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  usuario: Usuario;
}

export interface Rol {
  id: number;
  nombre: string;
  descripcion: string;
}

export interface RegistroBitacora {
  id: number;
  usuario_id: number | null;
  rol: string;
  accion: string;
  entidad: string;
  entidad_id: string | null;
  valor_anterior: Record<string, unknown> | null;
  valor_nuevo: Record<string, unknown> | null;
  motivo: string | null;
  ip: string;
  user_agent: string;
  created_at: string | null;
}

export interface BitacoraPaginada {
  registros: RegistroBitacora[];
  total: number;
  pagina: number;
  tamano_pagina: number;
  /** Cursor de la última fila; se manda como `cursor` para pedir el tramo
   *  siguiente. La bitácora recibe eventos constantemente y con OFFSET las
   *  páginas se corrían. Lo administra `useBitacora`. */
  siguiente_cursor?: string | null;
}

export interface FiltrosBitacora {
  desde?: string;
  hasta?: string;
  usuario_id?: number;
  accion?: string;
  entidad?: string;
  pagina?: number;
  tamano_pagina?: number;
  /** Paginación por cursor: si va, el backend ignora `pagina`. */
  cursor?: string;
}

export interface Configuracion {
  nombre_negocio: string;
  logo_url: string;
  color_primario: string;
  color_secundario: string;
  tipografia: string;
  session_ttl_admin_minutos: number;
  session_ttl_cajero_minutos: number;
  max_intentos_login: number;
  minutos_bloqueo: number;
  updated_at: string | null;
}

// Puerto: interfaz de subida de la foto de boleta (va a Google Drive).
// Fuente de verdad: backend/app/modules/modulo_b_inventario/infrastructure/http/storage_router.py
import type { StorageResult } from "../types";

export interface StoragePort {
  /** `POST /storage/upload` — multipart/form-data con `carpeta` y `file`. */
  subir(carpeta: string, archivo: File): Promise<StorageResult>;
}

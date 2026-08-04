// Adaptador: implementa storage.port.ts usando el cliente HTTP compartido (axios).
// Importante: este endpoint recibe `multipart/form-data` (carpeta + file), no JSON.
import { httpClient, TIMEOUT_ARCHIVOS_MS } from "../../../shared/lib/http-client";
import type { StorageResult } from "../types";
import type { StoragePort } from "./storage.port";

export const storageHttpAdapter: StoragePort = {
  async subir(carpeta: string, archivo: File) {
    const fd = new FormData();
    fd.append("carpeta", carpeta);
    fd.append("file", archivo);
    const { data } = await httpClient.post<StorageResult>("/storage/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
      // La foto de la boleta va a Drive desde el celular del cajero: con el
      // tope normal, una subida sana con mala señal se cortaría a mitad.
      timeout: TIMEOUT_ARCHIVOS_MS,
    });
    return data;
  },
};

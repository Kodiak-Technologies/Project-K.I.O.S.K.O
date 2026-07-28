// Adaptador: implementa storage.port.ts usando el cliente HTTP compartido (axios).
// Importante: este endpoint recibe `multipart/form-data` (carpeta + file), no JSON.
import { httpClient } from "../../../shared/lib/http-client";
import type { StorageResult } from "../types";
import type { StoragePort } from "./storage.port";

export const storageHttpAdapter: StoragePort = {
  async subir(carpeta: string, archivo: File) {
    const fd = new FormData();
    fd.append("carpeta", carpeta);
    fd.append("file", archivo);
    const { data } = await httpClient.post<StorageResult>("/storage/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },
};

// Adaptador: implementa boletas.port.ts usando el cliente HTTP compartido (axios).
import { httpClient } from "../../../shared/lib/http-client";
import type { BoletasPort } from "./boletas.port";

export const boletasHttpAdapter: BoletasPort = {
  async listar(desde, hasta, cliente) {
    const { data } = await httpClient.get("/boletas", { params: { desde, hasta, cliente } });
    return data;
  },

  async descargarPng(boletaId) {
    const { data } = await httpClient.get(`/boletas/${boletaId}/png`, {
      responseType: "blob",
    });
    return data;
  },

  async subirDrive(boletaId) {
    await httpClient.post(`/boletas/${boletaId}/subir-drive`);
  },
};

// Puerto: interfaz de consulta/descarga de boletas.
import type { Boleta } from "../types";

export interface BoletasPort {
  listar(desde?: string, hasta?: string, cliente?: string): Promise<Boleta[]>;
  descargarPng(boletaId: number): Promise<Blob>;
  subirDrive(boletaId: number): Promise<void>;
}

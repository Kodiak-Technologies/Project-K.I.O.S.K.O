import { DatePicker } from "./DatePicker";
import { TimePicker } from "./TimePicker";

export interface DateTimePickerProps {
  label?: string;
  value?: string;
  onChange: (value: string | undefined) => void;
  disabled?: boolean;
  requerido?: boolean;
  horaPorDefecto?: string;
  className?: string;
}

export function DateTimePicker({
  label,
  value,
  onChange,
  disabled = false,
  requerido = false,
  horaPorDefecto,
  className = "",
}: DateTimePickerProps) {
  let fechaPart: string | undefined = undefined;
  let horaPart: string | undefined = undefined;

  if (value) {
    const normalizada = value.replace(" ", "T");
    const [f, h] = normalizada.split("T");
    if (f) fechaPart = f;
    if (h) horaPart = h.substring(0, 5);
  }

  const horaFallback =
    horaPorDefecto || (label && label.toLowerCase().includes("hasta") ? "23:59" : "00:00");

  function alCambiarFecha(nuevaFecha: string | undefined) {
    if (!nuevaFecha) {
      onChange(undefined);
      return;
    }
    const h = horaPart || horaFallback;
    onChange(`${nuevaFecha}T${h}`);
  }

  function alCambiarHora(nuevaHora: string | undefined) {
    if (!nuevaHora) {
      if (fechaPart) {
        onChange(`${fechaPart}T${horaFallback}`);
      } else {
        onChange(undefined);
      }
      return;
    }
    const f = fechaPart || new Date().toISOString().split("T")[0];
    onChange(`${f}T${nuevaHora}`);
  }

  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-zinc-700">
          {label}
          {requerido && <span className="text-peligro"> *</span>}
        </label>
      )}
      <div className="grid grid-cols-2 gap-2">
        <DatePicker
          value={fechaPart}
          onChange={alCambiarFecha}
          disabled={disabled}
          placeholder="Fecha"
        />
        <TimePicker
          value={horaPart}
          onChange={alCambiarHora}
          disabled={disabled}
          placeholder="Hora"
        />
      </div>
    </div>
  );
}

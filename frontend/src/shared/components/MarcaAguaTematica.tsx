// Marca de agua de temporada para la pantalla de Inicio: una calabaza con cara
// en el estilo Halloween y un arbolito en el estilo Navidad. Con cualquier otro
// estilo no se muestra nada. Es decorativa: no recibe clics ni la leen los
// lectores de pantalla.
import { useEstiloUI } from "../lib/estilo-context";

function Calabaza() {
  return (
    <svg viewBox="0 0 200 190" className="h-auto w-full">
      {/* Tallo y zarcillo (el cuerpo tapa la base del tallo) */}
      <path d="M94 52 C94 30 98 18 108 10 L115 17 C107 25 105 36 106 52 Z" fill="#4d7c0f" />
      <path d="M106 34 C118 20 138 22 140 36" fill="none" stroke="#65a30d" strokeWidth="4" strokeLinecap="round" />
      {/* Cuerpo: gajos superpuestos */}
      <ellipse cx="62" cy="112" rx="48" ry="62" fill="#ea580c" />
      <ellipse cx="138" cy="112" rx="48" ry="62" fill="#ea580c" />
      <ellipse cx="82" cy="112" rx="40" ry="66" fill="#f97316" />
      <ellipse cx="118" cy="112" rx="40" ry="66" fill="#f97316" />
      <ellipse cx="100" cy="112" rx="30" ry="68" fill="#fb923c" />
      {/* Cara */}
      <g fill="#431407">
        <polygon points="56,100 84,100 70,76" />
        <polygon points="116,100 144,100 130,76" />
        <polygon points="92,120 108,120 100,107" />
        <path d="M52 128 C68 162 132 162 148 128 L134 133 L126 143 L116 135 L106 145 L94 145 L84 135 L74 143 L66 133 Z" />
      </g>
    </svg>
  );
}

function Arbolito() {
  return (
    <svg viewBox="0 0 200 215" className="h-auto w-full">
      {/* Tronco */}
      <rect x="88" y="178" width="24" height="30" rx="3" fill="#78350f" />
      {/* Copa en tres niveles */}
      <polygon points="100,90 170,185 30,185" fill="#15803d" />
      <polygon points="100,60 156,140 44,140" fill="#16a34a" />
      <polygon points="100,30 140,95 60,95" fill="#22c55e" />
      {/* Esferas */}
      <g>
        <circle cx="80" cy="80" r="6" fill="#dc2626" />
        <circle cx="118" cy="72" r="6" fill="#eab308" />
        <circle cx="70" cy="125" r="6" fill="#eab308" />
        <circle cx="124" cy="118" r="6" fill="#dc2626" />
        <circle cx="58" cy="170" r="6" fill="#dc2626" />
        <circle cx="100" cy="160" r="6" fill="#eab308" />
        <circle cx="142" cy="165" r="6" fill="#dc2626" />
      </g>
      {/* Estrella */}
      <polygon
        points="100,8 104.1,18.3 115.2,19.1 106.7,26.2 109.4,36.9 100,31 90.6,36.9 93.3,26.2 84.8,19.1 95.9,18.3"
        fill="#facc15"
      />
    </svg>
  );
}

export function MarcaAguaTematica() {
  const { estiloActivo } = useEstiloUI();
  if (estiloActivo !== "halloween" && estiloActivo !== "navidad") return null;

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute bottom-0 right-0 z-0 w-44 opacity-20 sm:w-64 lg:w-80"
    >
      {estiloActivo === "halloween" ? <Calabaza /> : <Arbolito />}
    </div>
  );
}

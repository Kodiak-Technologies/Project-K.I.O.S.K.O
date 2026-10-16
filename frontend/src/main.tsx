// Entry point de React. Monta <App /> en el DOM.
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
// Antes de montar: el navegador avisa "se puede instalar" una sola vez, al cargar.
import "./shared/lib/pwa";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

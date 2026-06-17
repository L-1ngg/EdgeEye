import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { applyTheme, type Theme } from "./theme/useTheme";
import "./styles/global.css";

// Apply the persisted/system theme before first render to avoid a flash.
const initialTheme: Theme =
  typeof window !== "undefined"
    ? window.localStorage.getItem("edgeeye-theme") === "dark" ||
      (window.localStorage.getItem("edgeeye-theme") === null &&
        window.matchMedia?.("(prefers-color-scheme: dark)").matches)
      ? "dark"
      : "light"
    : "light";
applyTheme(initialTheme);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);

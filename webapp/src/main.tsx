import "@fontsource-variable/onest";
import { createRoot } from "react-dom/client";
import "./styles.css";

// Outside Telegram the dev server fakes the WebApp and the API (never in a production build).
if (import.meta.env.DEV && !window.Telegram?.WebApp.initData) await import("./dev/mock");
const { default: App } = await import("./App");

createRoot(document.getElementById("root")!).render(<App />);

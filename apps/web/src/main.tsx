import ReactDOM from "react-dom/client";

import { AppRouter } from "@/router";
import "@/styles/globals.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
    throw new Error("Root element not found");
}

ReactDOM.createRoot(rootElement).render(<AppRouter />);

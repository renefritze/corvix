import { render } from "preact";
import { App } from "./app";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./styles/app.css";

const appRoot = document.getElementById("app");

if (!appRoot) {
	throw new Error("App root element '#app' was not found");
}

render(
	<ErrorBoundary>
		<App />
	</ErrorBoundary>,
	appRoot,
);

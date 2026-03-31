import { render } from "preact";
import { App } from "./app";
import "./styles/app.css";

const appRoot = document.getElementById("app");

if (!appRoot) {
	throw new Error("App root element '#app' was not found");
}

render(<App />, appRoot);

import { mount } from "svelte";
import App from "./App.svelte";
import "./styles/app.css";

const target = document.getElementById("app");

if (!target) {
	throw new Error("App root element '#app' was not found");
}

export default mount(App, { target });

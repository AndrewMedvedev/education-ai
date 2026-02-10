import { initApp } from "../general/createModules.js";

const dataElement = document.getElementById("initial-data");
const data = JSON.parse(dataElement.textContent);

initApp(data);

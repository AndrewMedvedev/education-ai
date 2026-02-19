import { renderModule } from "../general/createModules.js";
import { initializeChat } from "./chat.js";
import { getModuleById } from "../general/utils.js";
// import { course } from "../general/data.js";

const dataElement = document.getElementById("initial-data");
const data = JSON.parse(dataElement.textContent);
const baseURL = data[baseURL]
const moduleId = data[moduleId];
const course = data[course];

// const moduleId = "70601b76-7d82-4251-8409-055a3ccced00";
const module = getModuleById(moduleId, course);
renderModule(module.content_blocks);

document.addEventListener("DOMContentLoaded", () => {
  initializeChat();
});

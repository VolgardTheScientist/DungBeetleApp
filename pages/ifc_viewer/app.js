
import { Color } from "three";
import { IfcViewerAPI } from "web-ifc-viewer";

function sendMessageToStreamlitClient(type, data) {
    const message = { ...data, isStreamlitMessage: true, type };
    window.parent.postMessage(message, "*");
}

function init() {
    sendMessageToStreamlitClient("streamlit:componentReady", {apiVersion: 1});
}

function setFrameHeight(height) {
    sendMessageToStreamlitClient("streamlit:setFrameHeight", {height});
}

const viewer = new IfcViewerAPI({container: document.getElementById('viewer-container'), backgroundColor: new Color(0xffffff)});
viewer.axes.setAxes();
viewer.grid.setGrid();

async function loadIfc(url) {
    // Load the model
    const model = await viewer.IFC.loadIfcUrl(url, COORDINATE_TO_ORIGIN = true);
  
    // Add dropped shadow and post-processing effect
    await viewer.shadowDropper.renderShadow(model.modelID);
    viewer.context.renderer.postProduction.active = true;  
  }

function onDataFromPython(event) {
    if (event.data.type !== "streamlit:render") return;
    const url = event.data.args.url;
    if(url){
        fileUrl = url; // Save the url to the fileUrl variable
        loadIfc(url);
    }
}

let fileUrl = ''; // This will hold the URL of the file to download

const container = document.getElementById("button-container");

const button_container = document.getElementById("button-container");
const button = document.createElement("button");
button_container.appendChild(button);
button.textContent = "Download IFC";
button.onclick = (event) => {
    event.preventDefault(); // Add this line to prevent the default action
    if (fileUrl !== '') {
        fetch(fileUrl)
            .then(response => response.blob())
            .then(blob => {
                const href = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = href;
                link.download = 'reuse_component.ifc';
                document.body.appendChild(link);
                link.click();
                link.remove();
            })
            .catch(console.error);
    } else {
        console.log("No file URL has been passed from Python.")
    }
};

// Hook things up!
window.addEventListener("message", onDataFromPython);
init();

// Hack to autoset the iframe height.
window.addEventListener("load", function() {
    window.setTimeout(function() {
        setFrameHeight(500)
    }, 0);
});

// Floor plan viewing

const allPlans = viewer.plans.getAll(model.modelID);

for (const plan of allPlans) {
    const currentPlan = viewer.plans.planLists[model.modelID][plan];
    console.log(currentPlan);

    const buttonPlan = document.createElement('button');
    container.appendChild(button);
    buttonPlan.textContent = currentPlan.name;
    buttonPlan.onclick = () => {
        viewer.plans.goTo(model.modelID, plan);
        viewer.edges.toggle('example', true);
    };
}

const buttonExit = document.createElement('button');
container.appendChild(button);
buttonExit.textContent = 'Exit';
buttonExit.onclick = () => {
    viewer.plans.exitPlanView();
    viewer.edges.toggle('example', false);
};

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

function toggleShadow(active) {
    const shadows = Object.values(viewer.shadowDropper.shadows);
    for (shadow of shadows) {
      shadow.root.visible = active;
    }
  }
  
  function togglePostproduction(active) {
    viewer.context.renderer.postProduction.active = active;
  }

const viewer = new IfcViewerAPI({container: document.getElementById('viewer-container'), backgroundColor: new Color(0xffffff)});
viewer.axes.setAxes();
viewer.grid.setGrid();

async function loadIfc(url) {
    // Load the model
    const model = await viewer.IFC.loadIfcUrl(url, COORDINATE_TO_ORIGIN = true);
  
    // Add dropped shadow and post-processing effect
    await viewer.shadowDropper.renderShadow(model.modelID);

    await viewer.plans.computeAllPlanViews(model.modelID);

    // Floor plan navigation 

    const lineMaterial = new LineBasicMaterial({ color: "black" });
    const baseMaterial = new MeshBasicMaterial({
      polygonOffset: true,
      polygonOffsetFactor: 1, // positive value pushes polygon further away
      polygonOffsetUnits: 1,
    });

    viewer.edges.create(
      "example-edges",
      model.modelID,
      lineMaterial,
      baseMaterial
    );
    
    const allPlans = viewer.plans.getAll(model.modelID);
    
    const container = document.getElementById("button-container");
    
    for (const plan of allPlans) {
      const currentPlan = viewer.plans.planLists[model.modelID][plan];
      console.log(currentPlan);
    
      const button = document.createElement("button");
      container.appendChild(button);
      button.textContent = currentPlan.name;
      button.onclick = () => {
        viewer.plans.goTo(model.modelID, plan);
        viewer.edges.toggle("example-edges", true);
        togglePostproduction(false);
        toggleShadow(false);
      };
    }
  
    const button = document.createElement("button");
    container.appendChild(button);
    button.textContent = "Exit floorplans";
    button.onclick = () => {
      viewer.plans.exitPlanView();
      viewer.edges.toggle("example-edges", false);
      togglePostproduction(true);
      toggleShadow(true);
    };

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
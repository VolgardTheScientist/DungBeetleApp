
import { IfcViewerAPI } from "web-ifc-viewer";
import { Color, LineBasicMaterial, MeshBasicMaterial } from "three";
import Drawing from "dxf-writer";

let floorPlanClicked = false;

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

let model;
let allPlans;

async function loadIfc(url) {
    // Load the model
    const model = await viewer.IFC.loadIfcUrl(url, COORDINATE_TO_ORIGIN = true);
  
    // Add dropped shadow and post-processing effect
    await viewer.shadowDropper.renderShadow(model.modelID);
    // viewer.context.renderer.postProduction.active = true; Postproduction off
    togglePostproduction(true);
    toggleShadow(true);



    // Add download IFC button
    const container = document.getElementById("button-container");

    if (document.getElementById("download-ifc-button") === null) {
      const buttonIfc = document.createElement("button");
      buttonIfc.id = "download-ifc-button";
      container.appendChild(buttonIfc);
      buttonIfc.textContent = "Download IFC";
      buttonIfc.onclick = (event) => {
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
    }

    // Compute 2D plans
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
    

    
    for (const plan of allPlans) {
      const currentPlan = viewer.plans.planLists[model.modelID][plan];
      console.log(currentPlan);
    
      if (document.getElementById(`plan-button-${plan}`) === null) {
        const button = document.createElement("button");
        container.appendChild(button);
        button.textContent = currentPlan.name;
        button.onclick = () => {
          viewer.plans.goTo(model.modelID, plan);
          viewer.edges.toggle("example-edges", true);
          togglePostproduction(false);
          toggleShadow(false);
          floorPlanClicked = true;
          if (document.getElementById("exit-floor-plans-button") === null) {
            addExitFloorPlansButton();
        };
      }
    }
  
    function addExitFloorPlansButton() {
      const button = document.createElement("button");
      button.id = "exit-floor-plans-button";
      container.appendChild(button);
      button.textContent = "Exit floor plan";
      button.onclick = () => {
        viewer.plans.exitPlanView();
        viewer.edges.toggle("example-edges", false);
        togglePostproduction(true);
        toggleShadow(true);
        floorPlanClicked = false;
        button.remove();
      };
    }

    // Floor plan export
    const project = await viewer.IFC.getSpatialStructure(model.modelID);

    const storeys = project.children[0].children[0].children;
    for (const storey of storeys) {
      for (const child of storey.children) {
        if (child.children.length) {
          storey.children.push(...child.children);
        }
      }
    }

    viewer.dxf.initializeJSDXF(Drawing);

    for (const plan of allPlans) {
      const currentPlan = viewer.plans.planLists[model.modelID][plan];
      console.log(currentPlan);
      if (document.getElementById(`dxf-button-${plan}`) === null) {
        const button = document.createElement("button");
        button.id = `dxf-button-${plan}`;
        container.appendChild(button);
        button.textContent = 'Download 2D DXF';
        button.onclick = () => {
          const storey = storeys.find(storey => storey.expressID === currentPlan.expressID);
          exportDXF(storey, currentPlan, model.modelID);
        };
      }  
    }

  }

}

const dummySubsetMaterial  = new MeshBasicMaterial({visible: false});

async function exportDXF(storey, plan, modelID) {

  // Create a new drawing (if it doesn't exist)
  if (!viewer.dxf.drawings[plan.name]) {
    viewer.dxf.newDrawing(plan.name);
  }

  // Get the IDs of all the items to draw
  const ids = storey.children.map(item => item.expressID);

  // If no items to draw in this layer in this floor plan, let's continue
  if (!ids.length) return;

  // If there are items, extract its geometry
  const subset = viewer.IFC.loader.ifcManager.createSubset({
    modelID,
    ids,
    removePrevious: true,
    customID: 'floor_plan_generation',
    material: dummySubsetMaterial
  });

  // Get the projection of the items in this floor plan
  const filteredPoints = [];
  const edges = await viewer.edgesProjector.projectEdges(subset);
  const positions = edges.geometry.attributes.position.array;

  // Lines shorter than this won't be rendered
  const tolerance = 0.01;
  for (let i = 0; i < positions.length - 5; i += 6) {

    const a = positions[i] - positions[i + 3];
    // Z coords are multiplied by -1 to match DXF Y coordinate
    const b = -positions[i + 2] + positions[i + 5];

    const distance = Math.sqrt(a * a + b * b);

    if (distance > tolerance) {
      filteredPoints.push([positions[i], -positions[i + 2], positions[i + 3], -positions[i + 5]]);
    }

  }

  // Draw the projection of the items
  viewer.dxf.drawEdges(plan.name, filteredPoints, 'Projection', Drawing.ACI.BLUE, 'CONTINUOUS');

  // Clean up
  edges.geometry.dispose();

  // Draw all sectioned items. thick and thin are the default layers created by IFC.js
    viewer.dxf.drawNamedLayer(plan.name, plan, 'thick', 'Section', Drawing.ACI.RED, 'CONTINUOUS');
    viewer.dxf.drawNamedLayer(plan.name, plan, 'thin', 'Section_Secondary', Drawing.ACI.CYAN, 'CONTINUOUS');

  // Download the generated floorplan
  const result = viewer.dxf.exportDXF(plan.name);
  const link = document.createElement('a');
  link.download = 'floorplan.dxf';
  link.href = URL.createObjectURL(result);
  document.body.appendChild(link);
  link.click();
  link.remove();

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





// Hook things up!
window.addEventListener("message", onDataFromPython);
init();

// Hack to autoset the iframe height.
window.addEventListener("load", function() {
    window.setTimeout(function() {
        setFrameHeight(500)
    }, 0);
});
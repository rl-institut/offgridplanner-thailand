const shsDiv = document.getElementById("accordion-shs")
const shsDivTitle = document.getElementById("selectShsBoxTitle")
const shsCheckbox = document.getElementById("id_include_shs")
const maxGridCostInput = document.getElementById('id_shs_max_grid_cost')
const shsLifetimeLabel = document.getElementById('shsLifetimeLabel')
const shsLifetimeUnit = document.getElementById('shsLifetimeUnit')

function stopVideo() {
    var video = document.getElementById("tutorialVideo");
    video.pause();
}

function change_shs_box_visibility() {
    if (shsCheckbox.checked) {
        shsDiv.classList.remove('box--not-selected');
        maxGridCostInput.disabled = false;
        shsLifetimeLabel.classList.remove('disabled');
        shsLifetimeUnit.classList.remove('disabled');
        shsDivTitle.style.removeProperty("color");
    } else {
        shsDiv.classList.add('box--not-selected');
        maxGridCostInput.disabled = true;
        shsLifetimeLabel.classList.add('disabled');
        shsLifetimeUnit.classList.add('disabled');
        shsDivTitle.style.color = "darkred";

    }
}

document.addEventListener('DOMContentLoaded', function () {
    change_shs_box_visibility();
    shsCheckbox.addEventListener("change", change_shs_box_visibility);
});

// Road draw:created handler — polylines only, no consumer logic
map.on(L.Draw.Event.CREATED, function (event) {
    const layer = event.layer;
    drawnItems.addLayer(layer);
    if (event.layerType === 'polyline') {
        const coords = layer.getLatLngs().map(ll => [ll.lat, ll.lng]);
        const road_id = "m-" + (road_elements.filter((road) => road.how_added === "manual").length + 1)
        const road = { coordinates: coords, is_clicked: false, how_added: "manual", road_type: "polyline", road_id: road_id, layer: layer};
        road_elements.push(road);
        makeRoadLayerClickable(layer, road);
    }
    polygonCoordinates.push(layer.getLatLngs());
});

// Override: trash clears road drawings only, not consumer markers
function customTrashBinAction() {
    road_elements.filter(r => r.is_clicked).forEach(r => {
        if (r.layer) drawnItems.removeLayer(r.layer);
    });
    road_elements = road_elements.filter(r => !r.is_clicked);
}

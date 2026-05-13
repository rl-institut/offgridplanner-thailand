// Road draw:created handler — polylines only, no consumer logic
map.on(L.Draw.Event.CREATED, function (event) {
    const layer = event.layer;
    drawnItems.addLayer(layer);
    if (event.layerType === 'polyline') {
        const coords = layer.getLatLngs().map(ll => [ll.lat, ll.lng]);
        road_elements.push({ coordinates: coords });
    }
    polygonCoordinates.push(layer.getLatLngs());
});

// Override: trash clears road drawings only, not consumer markers
function customTrashBinAction() {
    drawnItems.clearLayers();
    road_elements = [];
    polygonCoordinates = [];
}

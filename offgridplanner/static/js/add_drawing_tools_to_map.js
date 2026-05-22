/**
 * The script integrates interactive drawing tools into a Leaflet.js map withina FastAPI web application. Primarily
 * utilized on the "consumer-selection" page, it empowers users to draw markers, rectangles, and polygons on the
 * map. These drawings are crucial for designating consumer locations and marking
 * specific areas of interest.
 *
 * Key Features:
 * - Polygon and Rectangle Drawing: Enables users to draw polygons and rectangles on the map with predefined
 *   shape and color settings, enhancing the map's interactivity and user engagement.
 *
 * - Custom Marker Controls: Facilitates the addition of distinct icons, such as power houses or consumers,
 *   onto the map, allowing for a more detailed and customized mapping experience.
 *
 * - Event Listeners: Actively listens for and responds to the creation of new shapes or markers. It ensures
 *   that the map elements are updated in real time, reflecting user actions instantaneously.
 *
 * - Dynamic Marker Management: Provides functionalities to dynamically add or remove markers based on user
 *   interactions, offering a flexible and responsive user interface.
 *
 * - Trash Bin Control: Incorporates a custom control to clear all drawn items from the map, simplifying the
 *   process of resetting or starting a new selection.
 *
 * - GeoSearch Integration: Utilizes the GeoSearch library to enable location searching capabilities,
 *   enhancing the usability and functionality of the map.
 *
 * - Consumer Toggle Feature: Includes a toggle mechanism to switch between adding and removing consumers
 *   from the map, offering versatility in map manipulation.
 *
 * - Consumer Count Display: Counts and displays the number of consumers currently present on the map, providing
 *   valuable insights at a glance.
 */

var polygonDrawer = new L.Draw.Polygon(map, {
    shapeOptions: {
        color: '#1F567D80'
    }
});

var lineDrawer = new L.Draw.Polyline(map, {
    shapeOptions: {
        color: '#1F567D80'
    }
});

var rectangleDrawer = new L.Draw.Rectangle(map, {
    shapeOptions: {
        color: '#1F567D80'
    }
});


let isPowerHouseMarker = false;


var myCustomMarker = L.Icon.extend({
    options: {
        shadowUrl: null,
        iconAnchor: new L.Point(12, 12),
        iconSize: new L.Point(24, 24),
        iconUrl: "/static/icons/i_consumer.svg"
    }
});


const iconB = L.icon({
    iconUrl: "/static/icons/i_power_house.svg",
    iconSize: [12, 12],
    iconAnchor: [12, 12],
    popupAnchor: [1, -12]
});


L.NewMarker = L.Draw.Marker.extend({
    options: {
        icon: iconB
    }
});


const roadDrawControls = {
    polyline: {
        shapeOptions: { color: '#9933ff', weight: 3, opacity: 1 }
    },
    polygon: false,
    circle: false,
    circlemarker: false,
    rectangle: false,
    marker: false,
};

const consumerDrawControls = {
    polyline: false,
    polygon: true,
    circle: false,
    circlemarker: false,
    rectangle: true,
    marker: {
        icon: new myCustomMarker()
    }
};

let drawControl = new L.Control.Draw({
    position: 'topleft',
    draw: step === "consumerSelection" ? consumerDrawControls : roadDrawControls,
});


const searchProvider = new GeoSearch.OpenStreetMapProvider();

const searchInput = document.getElementById('search-input');

searchInput.addEventListener('keypress', async (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        let query = searchInput.value;
        if (!query) return;

        let results = await searchProvider.search({ query });
        if (results && results.length > 0) {
            const { x: lng, y: lat } = results[0];

            if (isLatLngInMapBounds(lat, lng)) {
                map.setView([lat, lng], 13);
            } else {
                const responseMsg = document.getElementById("responseMsg");
                if (responseMsg) {
                    responseMsg.innerHTML = 'Location not inside country bounds';
                }
            }
        } else {
            alert('No results found');
        }
    }
});

function isLatLngInMapBounds(lat, lng) {
    const latLng = L.latLng(lat, lng);
    return map.options.maxBounds.contains(latLng);
}

let input = document.getElementById('toggleswitch');


function removeBoundaries() {
    drawnItems.clearLayers();
    polygonCoordinates = [];
}


// ─── Unified Toolbar ─────────────────────────────────────────────────────────

const UnifiedToolbar = L.Control.extend({
    options: {
        position: 'topleft',
        buttons: [] // pass an array of button keys to include
    },

    onAdd: function (map) {
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
        L.DomEvent.disableClickPropagation(container);

        const addBtn = (title, innerHTML, onClick) => {
            const a = L.DomUtil.create('a', '', container);
            a.href = '#';
            a.title = title;
            a.innerHTML = innerHTML;
            a.style.display = 'flex';
            a.style.alignItems = 'center';
            a.style.justifyContent = 'center';
            L.DomEvent.on(a, 'click', L.DomEvent.stopPropagation)
                .on(a, 'click', L.DomEvent.preventDefault)
                .on(a, 'click', onClick);
            return a;
        };

        const buttonDefs = {
            zoom: () => addBtn(
                'Zoom to all',
                `<img src="/static/images/imgZoomToAll.png" style="width:20px;height:20px;display:block" alt="Zoom">`,
                () => zoomAll(map)
            ),

            trash: () => addBtn(
                'Clear all',
                '<svg widh="20" height="20" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><path d="m21.12 5.09a3 3 0 0 0 -4.24 0l-8.59 8.58-4.58 4.59a3 3 0 0 0 0 4.24l2.88 2.88h-3.59a1 1 0 0 0 0 2h21a1 1 0 0 0 0-2h-2.59l7.88-7.88a3 3 0 0 0 0-4.24zm-16 16a1 1 0 0 1 0-1.42l3.88-3.88 9.59 9.59h-9.18zm22.76-5-7.88 7.91-9.59-9.59 7.88-7.91a1 1 0 0 1 1.42 0l8.17 8.17a1 1 0 0 1 0 1.42z"/></svg>',
                () => customTrashBinAction()
            ),

            selectAll: () => addBtn(
                'Select all roads',
                '<svg fill="none" height="20" viewBox="0 0 24 24" width="20" xmlns="http://www.w3.org/2000/svg"><g clip-rule="evenodd" fill="rgb(0,0,0)" fill-rule="evenodd"><path d="m1.75 4c0-1.24264 1.00736-2.25 2.25-2.25h13c1.2427 0 2.25 1.00737 2.25 2.25v13c0 1.2427-1.0073 2.25-2.25 2.25h-13c-1.24263 0-2.25-1.0073-2.25-2.25zm2.25-.75c-.41421 0-.75.33579-.75.75v13c0 .4142.33578.75.75.75h13c.4142 0 .75-.3358.75-.75v-13c0-.41422-.3358-.75-.75-.75z"/><path d="m21.9997 5.75098c.4142 0 .75.33578.75.75v14.49902c0 .9665-.7835 1.75-1.75 1.75h-14.49824c-.41421 0-.75-.3358-.75-.75s.33579-.75.75-.75h14.49824c.138 0 .25-.1119.25-.25v-14.49902c0-.41422.3358-.75.75-.75z"/><path d="m15.0227 7.32173c.297.28866.3039.76348.0152 1.06055l-5.0002 5.14582c-.28316.2915-.74697.3044-1.04591.0291l-2.99985-2.7626c-.30469-.2806-.32423-.755-.04364-1.05974.2806-.3047.75507-.32424 1.05976-.04364l2.46274 2.26788 4.4913-4.62214c.2887-.29707.7635-.30389 1.0606-.01523z"/></g></svg>',
                () => selectAllRoads()
            ),

            deselectAll: () => addBtn(
                'Deselect all roads',
                '<svg height="16" viewBox="0 0 32 32" width="16" xmlns="http://www.w3.org/2000/svg"><path d="m26 1h-20a5 5 0 0 0 -5 5v20a5 5 0 0 0 5 5h20a5 5 0 0 0 5-5v-20a5 5 0 0 0 -5-5zm3 25a3 3 0 0 1 -3 3h-20a3 3 0 0 1 -3-3v-20a3 3 0 0 1 3-3h20a3 3 0 0 1 3 3z"/><path d="m24.71 7.29a1 1 0 0 0 -1.42 0l-7.29 7.3-7.29-7.3a1 1 0 1 0 -1.42 1.42l7.3 7.29-7.3 7.29a1 1 0 0 0 0 1.42 1 1 0 0 0 1.42 0l7.29-7.3 7.29 7.3a1 1 0 0 0 1.42 0 1 1 0 0 0 0-1.42l-7.3-7.29 7.3-7.29a1 1 0 0 0 0-1.42z"/></svg>',
                () => deselectAllRoads()
            ),

            fetchOSM: () => addBtn(
                'Fetch OSM roads',
                `<img src="https://www.freeiconspng.com/uploads/maps-icon-30.png" style="width:20px;height:20px;display:block" title="Fetch OSM roads" alt="Fetch OSM">`,
                () => add_roads_inside_boundary({ boundariesCoordinates: bounds })
            ),

            powerhouse: () => addBtn(
                'Place power-house',
                `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="20" height="20"><path d="M6,64H58a2,2,0,0,0,2-2V24a2,2,0,0,0-.71-1.53l-26-22a2,2,0,0,0-2.58,0l-26,22A2,2,0,0,0,4,24V62A2,2,0,0,0,6,64ZM8,24.93,32,4.62,56,24.93V60H8Z"/><path d="M44,33H35.33L37,22.3a2,2,0,0,0-1.08-2.08,2,2,0,0,0-2.31.37l-18,18a2,2,0,0,0-.44,2.18A2,2,0,0,0,17,42h7.69L23,53.72A2,2,0,0,0,25,56a2,2,0,0,0,1.41-.59l19-19a2,2,0,0,0,.44-2.18A2,2,0,0,0,44,33ZM27.83,48.34,29,40.28A2,2,0,0,0,27,38H21.83L32.09,27.73,31,34.7A2,2,0,0,0,33,37h6.17Z"/></svg>`,
                () => {
                    isPowerHouseMarker = true;
                    for (let type in drawControl._toolbars.draw._modes) {
                        if (drawControl._toolbars.draw._modes[type].handler.enabled()) {
                            drawControl._toolbars.draw._modes[type].handler.disable();
                        }
                    }
                    new L.Draw.Marker(map, { icon: iconB }).enable();
                }
            ),
        };

        this.options.buttons.forEach(key => {
            if (buttonDefs[key]) buttonDefs[key]();
        });

        return container;
    }
});


// ─── Map setup helpers ────────────────────────────────────────────────────────

function addDrawingToolsToConsumerMap() {
    map.addControl(new UnifiedToolbar({ buttons: ['zoom', 'trash', 'powerhouse'] }));
    map.addControl(drawControl);
    mergeDrawToolsIntoUnifiedBar();
}

function mergeDrawToolsIntoUnifiedBar() {
    requestAnimationFrame(() => {
        const unifiedBar = document.querySelector('.leaflet-top.leaflet-left .leaflet-bar.leaflet-control:not(.leaflet-control-zoom)');
        const drawButtons = document.querySelectorAll('.leaflet-draw.leaflet-control .leaflet-draw-toolbar a');

        drawButtons.forEach(a => {
            const srOnly = a.querySelector('.sr-only');
            if (srOnly) srOnly.remove();
            unifiedBar.appendChild(a);
        });

        const drawContainer = document.querySelector('.leaflet-draw.leaflet-control');
        if (drawContainer) drawContainer.remove();
    });
}

function addDrawingToolsToConsumerMap() {
    map.addControl(new UnifiedToolbar({ buttons: ['zoom', 'trash', 'powerhouse'] }));
    map.addControl(drawControl);
    mergeDrawToolsIntoUnifiedBar();
}

function addDrawingToolsToGridMap() {
    map.addControl(new UnifiedToolbar({ buttons: ['zoom', 'trash', 'selectAll', 'deselectAll', 'fetchOSM'] }));
    map.addControl(drawControl);
    mergeDrawToolsIntoUnifiedBar();
}
// Flag to track if a download is in progress
let isDownloadingCSV = false;

// -----------------------------
// Plotly UI theme (web-app look)
// -----------------------------
// Centralize palette + typography so all figures look consistent.
// Keep this minimal and override locally when a plot truly needs it.
const PLOTLY_THEME = {
    // You can swap this to any CSS-available font (e.g. "Inter", "Roboto", ...)
    fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif',

    // 5-color palette (primary/secondary/accent/warn/danger)
    colors: {
        primary: '#17688E',   // blue
        secondary: '#47AE9E', // teal
        accent: '#A1D58F',    // violet
        warn: '#FF7D00',      // amber
        danger: '#DC2626',    // red
        neutral: '#78290F',   // slate
        grid: '#E5E7EB',
        axis: '#111827',
        paper: '#FFFFFF',
        plot: '#FFFFFF',
    },
};

// Common Plotly config: responsive sizing + cleaner modebar.
const PLOTLY_CONFIG = {
    responsive: true,
    displaylogo: false,
    // Keep the modebar but reduce clutter a bit.
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
};

document.addEventListener('shown.bs.tab', (event) => {
  const targetSelector = event.target?.getAttribute('data-bs-target');
  if (!targetSelector) return;

  const pane = document.querySelector(targetSelector);
  if (!pane) return;

  // Let layout finish before resizing (important for smoothness)
  requestAnimationFrame(() => resizePlotlyIn(pane));
});

function ensureResponsiveContainer(el) {
    // Helps Plotly autosize to your wrapper containers.
    // (You can also do this in CSS, but keeping it here avoids touching other files.)
    if (!el) return;
    if (typeof el === 'string') el = document.getElementById(el);
    if (!el) return;
    el.style.width = '100%';
    el.style.height = '100%';
}

function applyBaseLayout(layout, { legend = true } = {}) {
    // Mutate-friendly helper: we return a merged layout without big refactors.
    return {
        template: 'plotly_white',
        paper_bgcolor: PLOTLY_THEME.colors.paper,
        plot_bgcolor: PLOTLY_THEME.colors.plot,
        ...(layout || {}),
        font: {
            family: PLOTLY_THEME.fontFamily,
            size: (layout && layout.font && layout.font.size) ? layout.font.size : 14,
            color: PLOTLY_THEME.colors.axis,
            ...(layout && layout.font ? layout.font : {}),
        },
        margin: {
            l: 56,
            r: 24,
            t: 36,
            b: 48,
            ...(layout && layout.margin ? layout.margin : {}),
        },
        hovermode: 'x unified',
        hoverlabel: { bgcolor: 'rgba(255,255,255,0.95)' },
        legend: legend ? {
            orientation: 'h',
            x: 0.5,
            y: 1.15,
            xanchor: 'center',
            yanchor: 'bottom',
            bgcolor: 'rgba(255, 255, 255, 1)',
            bordercolor: PLOTLY_THEME.colors.grid,
            borderwidth: 1,
            ...(layout && layout.legend ? layout.legend : {}),
        } : (layout && layout.legend ? layout.legend : undefined),
        xaxis: {
            showline: true,
            linewidth: 1,
            linecolor: PLOTLY_THEME.colors.grid,
            gridcolor: PLOTLY_THEME.colors.grid,
            zerolinecolor: PLOTLY_THEME.colors.grid,
            tickfont: { size: 13, color: PLOTLY_THEME.colors.axis },
            titlefont: { size: 14, color: PLOTLY_THEME.colors.axis },
            ...(layout && layout.xaxis ? layout.xaxis : {}),
        },
        yaxis: {
            showline: true,
            linewidth: 1,
            linecolor: PLOTLY_THEME.colors.grid,
            gridcolor: PLOTLY_THEME.colors.grid,
            zerolinecolor: PLOTLY_THEME.colors.grid,
            tickfont: { size: 13, color: PLOTLY_THEME.colors.axis },
            titlefont: { size: 14, color: PLOTLY_THEME.colors.axis },
            ...(layout && layout.yaxis ? layout.yaxis : {}),
        },
        autosize: true,
    };
}

function resizePlotlyIn(container) {
  if (!container) return;
  // Resize any Plotly graphs inside this container
  container.querySelectorAll('.js-plotly-plot').forEach((gd) => {
    try {
      Plotly.Plots.resize(gd);
      // Optional: force autosize calculation again
      // Plotly.relayout(gd, { autosize: true });
    } catch (e) {
      // no-op: graph may not be initialized yet
    }
  });
}

document.addEventListener('DOMContentLoaded', function () {
    load_results(proj_id);
});

document.getElementById('downloadCSV').addEventListener('click', function (event) {
    event.preventDefault();

    // Check if a download is already in progress
    if (isDownloadingCSV) {
        // Optionally, inform the user
        alert('A download is already in progress. Please wait.');
        return; // Exit the function to prevent multiple downloads
    }

    // Set the flag to indicate a download is in progress
    isDownloadingCSV = true;

    const downloadButton = this;
    const originalButtonText = downloadButton.innerHTML;

    // Disable the button visually and functionally
    downloadButton.style.pointerEvents = 'none'; // Prevent further clicks
    downloadButton.style.opacity = '0.6'; // Make it look disabled
    downloadButton.innerHTML = 'Processing...';

    // Allow the UI to update before starting the download
    requestAnimationFrame(() => {
        (async () => {
            try {
                // Fetch the CSV file
                const response = await fetch(downloadExcelResultsUrl);
                if (!response.ok) {
                    throw new Error(`Network response was not ok: ${response.statusText}`);
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);

                // Create a temporary link to trigger the download
                const a = document.createElement('a');
                a.href = url;
                a.download = `offgridplanner_data.xlsx`;
                document.body.appendChild(a);
                a.click();

                // Clean up
                a.remove();
                window.URL.revokeObjectURL(url);

                // Change button text to 'Downloading...'
                downloadButton.innerHTML = 'Downloading...';

                // Re-enable the button after a delay (e.g., 2 minutes)
                setTimeout(() => {
                    downloadButton.innerHTML = originalButtonText;
                }, 5000); // Delay of 120,000 milliseconds (2 minutes)

                // Re-enable the button after a delay (e.g., 2 minutes)
                setTimeout(() => {
                    // Reset the flag and re-enable the button
                    isDownloadingCSV = false;
                    downloadButton.style.pointerEvents = '';
                    downloadButton.style.opacity = '';
                }, 120000); // Delay of 120,000 milliseconds (2 minutes)
            } catch (error) {
                console.error('Error downloading CSV:', error);
                alert('An error occurred while downloading the XLSX file. Please try again.');

                // Reset the flag and re-enable the button immediately
                isDownloadingCSV = false;
                downloadButton.style.pointerEvents = '';
                downloadButton.style.opacity = '';
                downloadButton.innerHTML = originalButtonText;
            }
        })();
    });
});


// Flag to track if a PDF download is in progress
let isDownloadingPDF = false;

document.getElementById('downloadPDF').addEventListener('click', function (event) {
    event.preventDefault();

    // Check if a download is already in progress
    if (isDownloadingPDF) {
        alert('A download is already in progress. Please wait.');
        return; // Exit the function to prevent multiple downloads
    }

    // Set the flag to indicate a download is in progress
    isDownloadingPDF = true;

    const downloadButton = this;
    const originalButtonText = downloadButton.innerHTML;

    // Disable the button visually and functionally
    downloadButton.style.pointerEvents = 'none'; // Prevent further clicks
    downloadButton.style.opacity = '0.6'; // Make it look disabled
    downloadButton.innerHTML = 'Processing...';

    // Use setTimeout to allow the UI to update before heavy computations
    setTimeout(() => {
        (async () => {
            try {
                const plotIds = [];
                // TODO here check if steps are selected when implemented
                plotIds.push('demandTs'); // if do_demand_estimation
                plotIds.push('map'); // if do_grid_optimization
                plotIds.push('sankeyDiagram', 'energyFlows', 'lcoeBreakdown', 'demandCoverage'); // if do_es_design_optimization

                // Generate images (ensure this function is asynchronous)
                const images = await generateImages(plotIds);

                // Filter out null values
                const validImages = images.filter(img => img !== null);
                if (validImages.length === 0) {
                    console.warn('No valid images to send.');
                    alert('No valid images were generated. Please try again.');
                    throw new Error('No valid images generated.');
                }

                // Send images to the backend
                await sendImagesToBackend(validImages);

                // Change button text to 'Downloading...'
                downloadButton.innerHTML = 'Downloading...';
                setTimeout(() => {
                    downloadButton.innerHTML = originalButtonText;
                }, 5000); // Delay of 120,000 milliseconds (2 minutes)

                // Re-enable the button after a delay (e.g., 2 minutes)
                setTimeout(() => {
                    // Reset the flag and re-enable the button
                    isDownloadingPDF = false;
                    downloadButton.style.pointerEvents = '';
                    downloadButton.style.opacity = '';
                }, 120000); // Delay of 120,000 milliseconds (2 minutes)

            } catch (error) {
                console.error('Error generating PDF:', error);
                alert('An error occurred while generating the PDF. Please try again.');

                // Reset the flag and re-enable the button immediately
                isDownloadingPDF = false;
                downloadButton.style.pointerEvents = '';
                downloadButton.style.opacity = '';
                downloadButton.innerHTML = originalButtonText;
            }
        })();
    }, 0); // Delay of 0 milliseconds
});



function generateImages(plotIds) {
    const imagePromises = plotIds.map(plotId => {
        const plotElement = document.getElementById(plotId);
        if (!plotElement) {
            console.warn(`Plot element with ID '${plotId}' was not found.`);
            return Promise.resolve(null);
        }

        if (plotId === "map") {
            // Existing code for generating map image
            return generateMapImage(map) // Ensure 'map' is defined
                .then(function(imageData) {
                    return { id: plotId, data: imageData };
                })
                .catch(function(error) {
                    console.error(`Error generating image for ${plotId}:`, error);
                    return null;
                });
        } else if (plotId === 'energyFlows' || plotId === 'demandCoverage' || plotId === 'sankeyDiagram') {
            // For these plots, we need to clone and adjust data, x-axis, and legend

            // Clone the plot data and layout
            const clonedData = JSON.parse(JSON.stringify(plotElement.data));
            const clonedLayout = JSON.parse(JSON.stringify(plotElement.layout));

            // Ensure exported plots use the same typography/background.
            clonedLayout.font = clonedLayout.font || {};
            clonedLayout.font.family = PLOTLY_THEME.fontFamily;
            clonedLayout.template = clonedLayout.template || 'plotly_white';
            clonedLayout.paper_bgcolor = PLOTLY_THEME.colors.paper;
            clonedLayout.plot_bgcolor = PLOTLY_THEME.colors.plot;

            // Specific adjustments based on plotId
            if (plotId === 'sankeyDiagram') {
                // 1. Change margin top and bottom to 30
                clonedLayout.margin = clonedLayout.margin || {};
                clonedLayout.margin.t = 30;
                clonedLayout.margin.b = 30;

                // 2. Reduce height by 33% (set to 67% of original)
                if (clonedLayout.height) {
                    clonedLayout.height = clonedLayout.height * 0.5;
                } else {
                    // If height is not defined, set a default height reduced by 33%
                    clonedLayout.height = 600 * 0.5; // Example: original height = 600
                }
            } else if (plotId === 'energyFlows' || plotId === 'demandCoverage') {
                // Reduce height to 80% of original
                if (clonedLayout.height) {
                    clonedLayout.height = clonedLayout.height * 0.80;
                } else {
                    // If height is not defined, set a default height reduced to 80%
                    clonedLayout.height = 400; // Example: original height = 600
                }
            }

            // Determine the x-axis range
            let maxX = 0;
            clonedData.forEach(trace => {
                if (trace.x && trace.x.length > 0) {
                    const traceMaxX = Math.max(...trace.x);
                    if (traceMaxX > maxX) {
                        maxX = traceMaxX;
                    }
                }
            });

            // Desired x-axis end point
            const desiredEnd = 168; // Adjusted as per your requirement

            // Adjust x-axis range(s)
            for (let axisName in clonedLayout) {
                if (axisName.startsWith('xaxis')) {
                    clonedLayout[axisName] = clonedLayout[axisName] || {};
                    // Set the x-axis range based on data availability
                    if (maxX >= desiredEnd) {
                        clonedLayout[axisName].range = [0, desiredEnd];
                    } else {
                        clonedLayout[axisName].range = [0, maxX];
                    }
                    clonedLayout[axisName].autorange = false; // Disable autorange
                }
            }

            // **New Part: Replace data between x=0 and x=24 with data from x=24 to x=48**
            clonedData.forEach(trace => {
                if (trace.x && trace.y) {
                    const x = trace.x;
                    const y = trace.y;

                    // Check if we have enough data to perform the replacement
                    const hasEnoughData = x.some(value => value >= 48);

                    if (hasEnoughData) {
                        // Create new arrays for x and y
                        const newY = [...y]; // Clone y to avoid modifying original

                        // Map x values between 0 and 24 to x + 24
                        for (let i = 0; i < x.length; i++) {
                            if (x[i] >= 0 && x[i] <= 24) {
                                // Find the index where x equals x[i] + 24
                                const targetX = x[i] + 24;
                                const targetIndex = x.indexOf(targetX);
                                if (targetIndex !== -1) {
                                    // Replace y value at current index with y value from target index
                                    newY[i] = y[targetIndex];
                                }
                            }
                        }
                        // Assign the modified y-values back to the trace
                        trace.y = newY;
                    } else {
                        console.warn(`Not enough data to replace values for ${plotId}.`);
                    }
                }
            });

            // Create a hidden div
            const tempDiv = document.createElement('div');
            tempDiv.style.display = 'none';
            document.body.appendChild(tempDiv);

            // Render the cloned plot into the hidden div
            return Plotly.newPlot(tempDiv, clonedData, clonedLayout, PLOTLY_CONFIG).then(function() {
                // Generate the image
                return Plotly.toImage(tempDiv, { format: 'svg' })
                    .then(function(imageData) {
                        return { id: plotId, data: imageData };
                    })
                    .catch(function(error) {
                        console.error(`Error generating image for ${plotId}:`, error);
                        return null;
                    })
                    .finally(function() {
                        // Clean up
                        Plotly.purge(tempDiv);
                        tempDiv.parentNode.removeChild(tempDiv);
                    });
            }).catch(function(error) {
                console.error(`Error rendering cloned plot for ${plotId}:`, error);
                // Clean up
                Plotly.purge(tempDiv);
                tempDiv.parentNode.removeChild(tempDiv);
                return null;
            });
        } else {
            // For other plots, proceed as usual
            return Plotly.toImage(plotElement, { format: 'svg' })
                .then(function(imageData) {
                    return { id: plotId, data: imageData };
                })
                .catch(function(error) {
                    console.error(`Error generating image for ${plotId}:`, error);
                    return null;
                });
        }
    });

    return Promise.all(imagePromises);
}


function generateMapImage(map) {
    return new Promise((resolve, reject) => {
        if (!map || typeof map.getContainer !== 'function') {
            console.error('Map-Objekt ist nicht definiert oder ungültig.');
            return reject(new Error('Ungültiges Map-Objekt.'));
        }

        const mapContainer = map.getContainer();

        // Select elements you want to hide (adjust selectors as needed)
        const zoomControl = document.querySelector('.leaflet-control-zoom');
        const layerControl = document.querySelector('.leaflet-control-layers');
        const customZoomButton = document.querySelector('.leaflet-control-custom');

        // Hide elements before capturing
        if (zoomControl) zoomControl.style.display = 'none';
        if (layerControl) layerControl.style.display = 'none';
        if (customZoomButton) customZoomButton.style.display = 'none';

        const fixedWidth = 1600;
        const fixedHeight = 800;

        html2canvas(mapContainer, {
            useCORS: true,
            allowTaint: true,
            logging: false,
            backgroundColor: null,
            scale: 1,
            windowWidth: fixedWidth,
            windowHeight: fixedHeight,
            scrollX: -window.scrollX,
            scrollY: -window.scrollY
        })
        .then(canvas => {
            const imgData = canvas.toDataURL('image/png');
            resolve(imgData);

            // Restore the visibility of hidden elements after capturing
            if (zoomControl) zoomControl.style.display = '';
            if (layerControl) layerControl.style.display = '';
            if (customZoomButton) customZoomButton.style.display = '';
        })
        .catch(err => {
            console.error('Fehler beim Generieren des Kartenbildes mit html2canvas:', err);
            reject(err);

            // Restore visibility if there's an error
            if (zoomControl) zoomControl.style.display = '';
            if (layerControl) layerControl.style.display = '';
            if (customZoomButton) customZoomButton.style.display = '';
        });
    });
}


function sendImagesToBackend(images) {
    const data = {
        images: images  // Array of { id: plotId, data: imageData }
    };
    fetch(downloadPDFReportUrl, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.blob(); // Get the response as a blob (PDF file)
    })
    .then(blob => {
        // Create a URL for the blob
        const url = window.URL.createObjectURL(blob);
        // Create a temporary link to trigger the download
        const a = document.createElement('a');
        a.href = url;
        a.download = `offgridplanner_results.pdf`;
        document.body.appendChild(a);
        a.click();
        // Clean up
        a.remove();
        window.URL.revokeObjectURL(url);
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}


var targetNode = document.getElementById('responseMsg');
var config = {childList: true, subtree: true, characterData: true};
var callback = function (mutationsList, observer) {
    for (let mutation of mutationsList) {
        if ((mutation.type === 'childList' || mutation.type === 'characterData') && targetNode.textContent.trim() !== '') {
            var modal = document.getElementById('msgBox');
            modal.style.display = "block";
        }
    }
};
var observer = new MutationObserver(callback);
observer.observe(targetNode, config);
document.getElementById("msgBox").style.zIndex = "9999";

// plot functions used for the plots in results page of web app.
// Functions are called from function plot in backend_communication.js


function plot_bar_chart(data) {
    kwAssets = {"pv": "PV", "inverter": "Inverter", "rectifier": "Rectifier",
     "diesel_genset": "Diesel Genset", "fuel_cell": "Fuel Cell", "electrolyzer": "Electrolyzer",
     "peak_demand": "Peak Demand", "surplus": "Max. Surplus"}
    kwhAssets = {"battery": "Battery", "h2_storage": "H2 storage"}
    let yValueKw = [];
    let yValueKwh = [];
    let xValueKw = [];
    let xValueKwh = [];
    let colors = [];
    let optimal_capacities = data;

    for (const [key, label] of Object.entries(kwAssets)) {
        xValueKw.push(Number(optimal_capacities[key]));
        yValueKw.push(gettext(label));
        if (key === "surplus") {
            colors.push(PLOTLY_THEME.colors.accent);
        } else {
            colors.push(PLOTLY_THEME.colors.primary);
        }
    }

    for (const [key, label] of Object.entries(kwhAssets)) {
        xValueKwh.push(Number(optimal_capacities[key]));
        yValueKwh.push(gettext(label));
    }

    let optimalSizes = document.getElementById('optimalSizes');

    // Reverse the arrays
    xValueKw = xValueKw.reverse();
    yValueKw = yValueKw.reverse();
    colors = colors.reverse();  // Reverse the color array

    var dataTraces = [
        {
            y: yValueKw,
            x: xValueKw,
            xaxis: 'x1',
            type: 'bar',
            orientation: 'h',
            text: xValueKw.map(String),
            textposition: 'auto',
            hoverinfo: 'none',
            opacity: 0.7,
            marker: {
                color: colors,
                line: {
                    color: 'rgba(17, 24, 39, 0.55)',
                    width: 1.5
                }
            },
            hovertemplate: '%{y}<br>%{x:.2f} kWh<extra></extra>',
            showlegend: false
        },
        {
            y: yValueKwh,
            x: xValueKwh,
            xaxis: 'x2',
            type: 'bar',
            orientation: 'h',
            marker: { color: PLOTLY_THEME.colors.accent },
            hovertemplate: '%{y}<br>%{x:.2f} kWh<extra></extra>',
            showlegend: false
        }
    ];

    ensureResponsiveContainer(optimalSizes);

    const layout = applyBaseLayout({
        hovermode: false,
        yaxis: { automargin: true },
        xaxis: {
            title: gettext('Capacity in kW'),
            side: 'top',
        },
        xaxis2: {
            title: gettext('Capacity in kWh'),
            showgrid: false,
            zeroline: false,
            overlaying: 'x',
            side: 'bottom',
        },
        barmode: 'stack',
        bargap: 0.5,
        showlegend: false,
        margin: { l: 90, r: 24, b: 56, t: 56 },
    }, { legend: false });

    Plotly.newPlot(optimalSizes, dataTraces, layout, PLOTLY_CONFIG);
};



function plot_lcoe_pie(lcoe_breakdown) {
    const lcoeBreakdownEl = document.getElementById('lcoeBreakdown') || lcoeBreakdown;

    const items = [
        { key: 'renewable_assets', label: gettext('Renewable Assets'), color: PLOTLY_THEME.colors.primary },
        { key: 'non_renewable_assets', label: gettext('Non-Renewable Assets'), color: PLOTLY_THEME.colors.neutral },
        { key: 'grid', label: gettext('Grid'), color: PLOTLY_THEME.colors.accent },
        { key: 'fuel', label: gettext('Fuel'), color: PLOTLY_THEME.colors.warn },
    ];

    const values = items.map(({ key }) => Number(lcoe_breakdown[key]));
    const labels = items.map(({ label }) => label);
    const colors = items.map(({ color }) => color);

    let data = [{
        type: 'pie',
        hole: .6,
        values: values,
        labels: labels,
        marker: {
            colors: colors,
            line: {
                color: 'rgba(17, 24, 39, 0.55)',
                width: 1.5
            }
        },
        textinfo: 'label+percent',
        textposition: 'outside',
        automargin: true,
        opacity: 0.9,
    }];

    ensureResponsiveContainer(lcoeBreakdownEl);

    let layout = applyBaseLayout({
        margin: { t: 8, b: 8, l: 8, r: 8 },
        showlegend: false,
        hovermode: false,
    }, { legend: false });

    Plotly.newPlot(lcoeBreakdownEl, data, layout, PLOTLY_CONFIG);
}


function plot_sankey(data) {
    const sankey_data = data;

    // Keep identical output: pv_to_surplus is hard-set to 0 in the original
    const valueByKey = {
        fuel_to_diesel_genset: Number(sankey_data['fuel_to_diesel_genset']),
        diesel_genset_to_rectifier: Number(sankey_data['diesel_genset_to_rectifier']),
        diesel_genset_to_demand: Number(sankey_data['diesel_genset_to_demand']),
        rectifier_to_dc_bus: Number(sankey_data['rectifier_to_dc_bus']),
        pv_to_dc_bus: Number(sankey_data['pv_to_dc_bus']),
        battery_to_dc_bus: Number(sankey_data['battery_to_dc_bus']),
        dc_bus_to_battery: Number(sankey_data['dc_bus_to_battery']),
        dc_bus_to_inverter: Number(sankey_data['dc_bus_to_inverter']),
        pv_to_surplus: 0,
        inverter_to_demand: Number(sankey_data['inverter_to_demand']),
        hydrogen_bus_to_h2_storage: Number(sankey_data['hydrogen_bus_to_h2_storage']),
        h2_storage_to_hydrogen_bus: Number(sankey_data['h2_storage_to_hydrogen_bus']),
        fuel_cell_to_dc_bus: Number(sankey_data['fuel_cell_to_dc_bus']),
        electrolyzer_to_hydrogen_bus: Number(sankey_data['electrolyzer_to_hydrogen_bus']),
        dc_bus_to_electrolyzer: Number(sankey_data['dc_bus_to_electrolyzer']),
        hydrogen_bus_to_fuel_cell: Number(sankey_data['hydrogen_bus_to_fuel_cell']),
    };

    const nodes = [
        gettext('Fuel'),          // 0
        gettext('Diesel Genset'), // 1
        gettext('Rectifier'),     // 2
        gettext('PV'),            // 3
        gettext('DC Bus'),        // 4
        gettext('Battery'),       // 5
        gettext('Inverter'),      // 6
        gettext('Demand'),        // 7
        gettext('Surplus'),       // 8
        gettext('Hydrogen'),       // 9
        gettext('H2 Storage'),       // 10
        gettext('Electrolyzer'),       // 11
        gettext('Fuel Cell'),       // 12
    ];

    const links = [
        { source: 0, target: 1, key: 'fuel_to_diesel_genset', label: gettext('Fuel supplied to the diesel genset') },
        { source: 1, target: 2, key: 'diesel_genset_to_rectifier', label: gettext('Diesel genset output sent to the rectifier') },
        { source: 1, target: 7, key: 'diesel_genset_to_demand', label: gettext('AC demand covered by the diesel genset') },
        { source: 2, target: 4, key: 'rectifier_to_dc_bus', label: gettext('Diesel genset electricity converted to DC') },
        { source: 3, target: 4, key: 'pv_to_dc_bus', label: gettext('PV electricity generation') },
        { source: 5, target: 4, key: 'battery_to_dc_bus', label: gettext('Battery discharge') },
        { source: 4, target: 5, key: 'dc_bus_to_battery', label: gettext('Battery charge') },
        { source: 4, target: 6, key: 'dc_bus_to_inverter', label: gettext('DC electricity sent to the inverter') },
        { source: 3, target: 8, key: 'pv_to_surplus', label: gettext('Surplus PV electricity') },
        { source: 6, target: 7, key: 'inverter_to_demand', label: gettext('AC demand covered by the PV system') },
        { source: 9, target: 10, key: 'hydrogen_bus_to_h2_storage', label: gettext('H2 storage charge') },
        { source: 10, target: 9, key: 'h2_storage_to_hydrogen_bus', label: gettext('H2 storage discharge') },
        { source: 12, target: 4, key: 'fuel_cell_to_dc_bus', label: gettext('DC electricity produced by fuel cell') },
        { source: 11, target: 9, key: 'electrolyzer_to_hydrogen_bus', label: gettext('Hydrogen produced by electrolyzer') },
        { source: 4, target: 11, key: 'dc_bus_to_electrolyzer', label: gettext('DC electricity going into electrolyzer') },
        { source: 9, target: 12, key: 'hydrogen_bus_to_fuel_cell', label: gettext('Hydrogen going into fuel cell') },
    ];

    var data = [{
        type: 'sankey',
        orientation: 'h',
        node: {
            pad: 10,
            thickness: 20,
            valueformat: ".3f",
            valuesuffix: "MWh",
            line: {
                color: 'black',
                width: 0.5
            },
            label: nodes,
            color: PLOTLY_THEME.colors.primary,
        },
        link: {
            source: links.map(l => l.source),
            target: links.map(l => l.target),
            value: links.map(l => valueByKey[l.key]),
            label: links.map(l => l.label),
            color: 'rgba(100, 116, 139, 0.35)',
        }
    }];

    ensureResponsiveContainer(sankeyDiagram);

    const layout = applyBaseLayout({
        margin: { l: 8, r: 8, t: 24, b: 8 },
    });

    Plotly.react(sankeyDiagram, data, layout, PLOTLY_CONFIG);
}


// ENERGY FLOWS PLOT
function plot_energy_flows(energy_flows, elementId, filterKeys = null) {
    const {
        diesel_genset_production,
        pv_production,
        battery,
        battery_content,
        h2_storage,
        h2_storage_content,
        electrolyzer_production,
        fuel_cell_production,
        demand,
        surplus
    } = energy_flows;

    const time = Array.from({ length: pv_production.length }, (_, i) => i);

    const energyFlows = document.getElementById(elementId);

    var tracesSpec = [
        { y: diesel_genset_production, name: gettext('Diesel Genset') },
        { y: pv_production, name: gettext('PV') },
        { y: battery, name: gettext('Battery In-/Output') },
        { y: battery_content, name: gettext('Battery Content'), yaxis: 'y2', visible: 'legendonly' },
        { y: h2_storage, name: gettext('H2 Storage In-/Output'), yaxis: 'y2'},
        { y: h2_storage_content, name: gettext('H2 Storage Content'), yaxis: 'y2', visible: 'legendonly' },
        { y: electrolyzer_production, name: gettext('Electrolyzer')},
        { y: fuel_cell_production, name: gettext('Fuel cell')},
        { y: demand, name: gettext('Demand') },
        { y: surplus, name: gettext('Surplus') },
    ];

    if (filterKeys?.length) {
      tracesSpec = tracesSpec
        .filter(t => filterKeys.includes(t.name))
        .map(t => {
          if (t.visible === 'legendonly') {
            const { visible, ...rest } = t;
            return rest;            // equivalent to default visible = true
          }
          return t;
        });
    }
    const data = tracesSpec.map(spec => ({
        x: time,
        y: spec.y,
        mode: 'lines',
        name: spec.name,
        line: { shape: 'hv', width: 2 },
        type: 'scatter',
        ...(spec.yaxis ? { yaxis: spec.yaxis } : {}),
        ...(spec.visible ? { visible: spec.visible } : {}),
    }));

    ensureResponsiveContainer(energyFlows);

    const layout = applyBaseLayout({
        xaxis: { title: gettext('Time in hours') },
        yaxis: { title: gettext('Energy Flow in kW') },
        yaxis2: {
            title: gettext('Battery Content in kWh'),
            overlaying: 'y',
            side: 'right',
            showgrid: false,
        },
    });

    // Apply a consistent colorway to the figure
    layout.colorway = [
        PLOTLY_THEME.colors.danger,
        PLOTLY_THEME.colors.primary,
        PLOTLY_THEME.colors.secondary,
        PLOTLY_THEME.colors.accent,
        PLOTLY_THEME.colors.warn,
        PLOTLY_THEME.colors.neutral,
    ];

    Plotly.newPlot(energyFlows, data, layout, PLOTLY_CONFIG);
}

// Storage states plot
function plot_storage_states(data, elementId) {
  const filteredData = { ...data };

  filteredData.series = data.series.filter(s =>
    ['H2 Storage', 'Battery Storage'].includes(s.name)
  );

  plot_energy_flows(filteredData, elementId);
}


// DEMAND COVERAGE PLOT
function plot_demand_coverage(demand_coverage) {

    const { renewable, non_renewable, demand, surplus } = demand_coverage;
    const time = Array.from({ length: renewable.length }, (_, i) => i);

    const demandCoverage = document.getElementById("demandCoverage");

    const tracesSpec = [
        { y: non_renewable, name: gettext('Non-Renewable'), stackgroup: 'one' },
        { y: renewable, name: gettext('Renewable'), stackgroup: 'one' },
        { y: demand, name: gettext('Demand'), mode: 'line', line: { color: 'black', width: 2.5 } },
        { y: surplus, name: gettext('Surplus'), stackgroup: 'one' },
    ];

    const data = tracesSpec.map(spec => ({
        x: time,
        y: spec.y,
        name: spec.name,
        ...(spec.stackgroup ? { stackgroup: spec.stackgroup } : {}),
        ...(spec.mode ? { mode: spec.mode } : {}),
        ...(spec.line ? { line: spec.line } : {}),
    }));

    ensureResponsiveContainer(demandCoverage);

    const layout = applyBaseLayout({
        xaxis: { title: gettext('Time in hours') },
        yaxis: { title: gettext('Demand in kW') },
        colorway: [
            PLOTLY_THEME.colors.neutral,
            PLOTLY_THEME.colors.secondary,
            PLOTLY_THEME.colors.primary,
            PLOTLY_THEME.colors.accent,
        ],
    });

    Plotly.newPlot(demandCoverage, data, layout, PLOTLY_CONFIG);
}


// DURATION CURVES
function plot_duration_curves(duration_curves) {
    const {
        diesel_genset_duration,
        pv_duration,
        rectifier_duration,
        inverter_duration,
        battery_charge_duration,
        battery_discharge_duration,
        h2_storage_charge_duration,
        h2_storage_discharge_duration,
        pv_percentage,
    } = duration_curves;

    const durationCurves = document.getElementById("durationCurves");

    const tracesSpec = [
        { y: diesel_genset_duration, name: gettext('Diesel Genset') },
        { y: pv_duration, name: gettext('PV') },
        { y: rectifier_duration, name: gettext('Rectifier') },
        { y: inverter_duration, name: gettext('Inverter') },
        { y: battery_charge_duration, name: gettext('Battery - Charging') },
        { y: battery_discharge_duration, name: gettext('Battery - Discharging') },
        { y: h2_storage_charge_duration, name: gettext('H2 Storage - Charging') },
        { y: h2_storage_discharge_duration, name: gettext('H2 Storage - Discharging') },
    ];

    const data = tracesSpec.map(spec => ({
        x: pv_percentage,
        y: spec.y,
        mode: 'lines',
        name: spec.name,
    }));

    ensureResponsiveContainer(durationCurves);

    const layout = applyBaseLayout({
        xaxis: { title: gettext('Percentage of Operation in %') },
        yaxis: { title: gettext('Load in %') },
        colorway: [
            PLOTLY_THEME.colors.danger,
            PLOTLY_THEME.colors.primary,
            PLOTLY_THEME.colors.warn,
            PLOTLY_THEME.colors.secondary,
            PLOTLY_THEME.colors.accent,
            PLOTLY_THEME.colors.neutral,
        ],
    });

    Plotly.newPlot(durationCurves, data, layout, PLOTLY_CONFIG);
}


// CO2 EMISSIONS PLOT
function plot_co2_emissions(co2_emissions) {
    const { non_renewable_electricity_production, hybrid_electricity_production } = co2_emissions;

    const time = Array.from({ length: non_renewable_electricity_production.length }, (_, i) => i);
    const non_renewable = non_renewable_electricity_production;
    const hybrid = hybrid_electricity_production;

    const xAxisTitle = time.length > 366 ? 'Time in hours' : 'Time in days';
    const co2Emissions = document.getElementById("co2Emissions");

    const tracesSpec = [
        { y: non_renewable, mode: 'lines', name: gettext('Non-Renewable') },
        { y: hybrid, mode: 'none', fill: 'tonexty', name: gettext('Savings') },
        { y: hybrid, mode: 'lines', name: gettext('Hybrid') },
    ];

    const data = tracesSpec.map(spec => ({
        x: time,
        y: spec.y,
        mode: spec.mode,
        name: spec.name,
        ...(spec.fill ? { fill: spec.fill } : {}),
    }));

    // Apply a more consistent palette for this figure
    if (data[0] && data[0].line) data[0].line.color = PLOTLY_THEME.colors.danger;
    if (data[2] && data[2].line) data[2].line.color = PLOTLY_THEME.colors.secondary;
    if (data[1]) data[1].fillcolor = 'rgba(15, 118, 110, 0.18)';

    ensureResponsiveContainer(co2Emissions);

    const layout = applyBaseLayout({
        xaxis: { title: xAxisTitle },
        yaxis: { title: gettext('CO<sub>2</sub> Emissions [tons]') },
    });

    Plotly.newPlot(co2Emissions, data, layout, PLOTLY_CONFIG);
}

async function redirect(href) {
    window.location.href = href;
}

async function hide_grid_results() {
    // Hide the GRID section
    const gridSubtitle = document.getElementById('gridTitle'); // Find the subtitle element
    const gridRow = document.getElementById('gridResultsRow');
    if (gridSubtitle) {
        gridSubtitle.style.display = 'none'; // Hide the subtitle
    }
    if (gridRow && gridRow.classList.contains('row')) {
        gridRow.style.display = 'none'; // Hide the row associated with the GRID subtitle
    }
    // Now perform the row swap
    const row1 = document.getElementById('actionButtonsRow'); // Assuming this is the row with action buttons
    const row2 = document.getElementById('resultsChart'); // The row with results chart
    // Get the parent element of the rows
    const parentElement = row1.parentElement;
    // Ensure both rows exist before attempting to swap
    if (row1 && row2 && parentElement) {
        // Swap the rows using insertBefore
        parentElement.insertBefore(row2, row1);
    }
    hideElements("firstRow");
}




async function hide_es_results() {
    hideElements('resultsChart');
    hideElements('demandcoverageChart');
    hideElements('energyflowsChart');
    hideElements('capacityChart');
    hideElements('durationcurveChart');
    hideElements('sankeyChart');
        }

function hideElements(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = 'none';
    }
}

function plot_demand_24h(data) {
    let demandTs = document.getElementById("demandTs");

    ensureResponsiveContainer(demandTs);

    var layout = applyBaseLayout({
        xaxis: {
            title: gettext('Hour of the day'),
            hoverformat: '.1f',
        },
        yaxis: {
            title: gettext('Demand (kW)'),
            hoverformat: '.1f',
        },
        colorway: [
            PLOTLY_THEME.colors.secondary,
            PLOTLY_THEME.colors.warn,
            PLOTLY_THEME.colors.primary,
        ]
    });

    // Extract data from the passed-in data object
    let {
        'x': x,
        'Very High Consumption': Very_High,
        'High Consumption': High,
        'Middle Consumption': Middle,
        'Low Consumption': Low,
        'Very Low Consumption': Very_Low,
        'Average': Average,
        'households': households,
        'enterprises': enterprises,
        'public_services': public_services,
    } = data.timeseries;

    // Define traces with 'stackgroup'
    var traceHouseholds = {
        x: x,
        y: households,
        type: 'scatter',
        mode: 'lines',
        name: gettext('Demand of Households'),
        line: { shape: 'spline', width: 2, color: PLOTLY_THEME.colors.primary },
        fill: 'tonexty',
        fillcolor: 'rgba(29, 78, 216, 0.25)',
        stackgroup: 'one' // Group for stacking
    };

    var traceEnterprises = {
        x: x,
        y: enterprises,
        type: 'scatter',
        mode: 'lines',
        name: gettext('Demand of Enterprises'),
        line: { shape: 'spline', width: 2, color: PLOTLY_THEME.colors.warn },
        fill: 'tonexty',
        fillcolor: 'rgba(245, 158, 11, 0.25)',
        stackgroup: 'one' // Same group as above
    };

    var tracePublicServices = {
        x: x,
        y: public_services,
        type: 'scatter',
        mode: 'lines',
        name: gettext('Demand of Public Services'),
        line: { shape: 'spline', width: 2, color: PLOTLY_THEME.colors.secondary },
        fill: 'tonexty',
        fillcolor: 'rgba(15, 118, 110, 0.25)',
        stackgroup: 'one' // Same group as above
    };

    // Data array
    var dataTraces = [tracePublicServices, traceEnterprises, traceHouseholds];

    // Render plot with the traces
    Plotly.react(demandTs, dataTraces, layout, PLOTLY_CONFIG);
}

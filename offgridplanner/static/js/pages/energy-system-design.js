/**
 * This script manages UI elements and SVG diagram interactions in a web application.
 * - Uses MutationObserver to display a modal when specific DOM changes occur.
 * - Defines and manipulates SVG elements for a dynamic energy system diagram.
 * - Enables and disables various options based on user input and system configuration.
 * - Dynamically styles SVG components (blocks, lines, arrows) based on user selections.
 * - Refreshes the diagram to reflect current system configuration, including energy sources and flow.
 */


const targetNode = document.getElementById('responseMsg');
const config = {childList: true, subtree: true, characterData: true};
const callback = function (mutationsList, observer) {
    for (let mutation of mutationsList) {
        if ((mutation.type === 'childList' || mutation.type === 'characterData') && targetNode.textContent.trim() !== '') {
            var modal = document.getElementById('msgBox');
            modal.style.display = "block";
        }
    }
};

const observer = new MutationObserver(callback);
observer.observe(targetNode, config);


const xLeft = 40;
var yTop = 130;
var roundCornerBlock = 5;
var roundCornerBus = 2;
var widthBlock = 125;
var widthBus = 10;
var heightBlock = 60;
var heightBus = 6 * heightBlock;
var lengthFlow = 90;

var lineCorrectionWidthBlock = 1;
var lineCorrectionLengthFlow = 1;

const component = [
    'pv',
    'battery',
    'diesel_genset',
    'hydrogen',
    'inverter',
    'rectifier',
    'shortage',
    // 'surplus',
];

document.addEventListener('DOMContentLoaded', function () {
    initDiagram();
    refreshBlocksOnDiagramOnLoad();
    check_box_visibility('shortage');
    component.forEach(id => {
        var el = document.getElementById(assetCheckBox(id))
        el.addEventListener("click", () => check_box_visibility(id));
        // Only add diagram refresh listener for components with diagrams
        if (id !== 'hydrogen') {
            el.addEventListener("click", () => refreshBlocksOnDiagram(id));
        }
    });
    setupAccordionAutoClose();
});

/************************************************************/
/*                ENABLING DISABLING OPTIONS                */

/************************************************************/

function assetCheckBox(id) {
    return "id_" + id + "_settings_is_selected"
}

function optimizationCheckBox(id) {
    return id + "_settings_design_optimized"
}

function check_optimization_strategy(id) {
    // Check if the optimization checkbox exists first
    const optimizationCheckbox = document.getElementById(optimizationCheckBox(id));
    if (!optimizationCheckbox) return;

    // Only update diagram styles for components that have diagram elements
    const componentsWithDiagram = ['diesel_genset', 'pv', 'battery', 'inverter', 'rectifier', 'shortage'];

    if (componentsWithDiagram.includes(id)) {
        // Update the styles after changing the optimization strategy
        styleBlock(id);
        styleText(id);
        styleLine(id);
        styleArrow(id);
        styleInformation(id);
    }

    const nominalCapacityInput = document.getElementById("id_" + id + "_parameters_nominal_capacity");
    const nominalCapacityLabel = document.getElementById(id + "_parameters_nominal_capacity_label");
    const nominalCapacityUnit = document.getElementById(id + "_parameters_nominal_capacity_unit");

    if (optimizationCheckbox.checked) {
        if (nominalCapacityInput) nominalCapacityInput.readOnly = true;
        if (nominalCapacityLabel) nominalCapacityLabel.classList.add('readonly-disabled');
        if (nominalCapacityUnit) nominalCapacityUnit.classList.add('readonly-disabled');
    } else {
        if (nominalCapacityInput) nominalCapacityInput.readOnly = false;
        if (nominalCapacityLabel) nominalCapacityLabel.classList.remove('readonly-disabled');
        if (nominalCapacityUnit) nominalCapacityUnit.classList.remove('readonly-disabled');
    }

    if (window.renderESDDiagram) window.renderESDDiagram();
}

function check_box_visibility(id) {
    const inverter = document.getElementById(assetCheckBox('inverter'));
    const pv = document.getElementById(assetCheckBox('pv'));
    const battery = document.getElementById(assetCheckBox('battery'));

    const isChecked = (element) => element && element.checked;

    if (id === 'inverter' && !isChecked(inverter)) {
        pv.checked = false;
        battery.checked = false;
        ['pv', 'battery'].forEach(item => {
            change_box_visibility(item);
            refreshBlocksOnDiagram(item);
        });
    }

    if ((id === 'pv' && isChecked(pv)) || (id === 'battery' && isChecked(battery))) {
        inverter.checked = true;
        change_box_visibility('inverter');
        refreshBlocksOnDiagram('inverter');
    }

    if (!isChecked(pv) && !isChecked(battery)) {
        inverter.checked = false;
        change_box_visibility('inverter');
        refreshBlocksOnDiagram('inverter');
    }

    change_box_visibility(id);

    // Only refresh diagram for components that have diagrams
    if (id !== 'hydrogen') {
        refreshBlocksOnDiagram(id);
    }

    if (window.renderESDDiagram) {
        window.renderESDDiagram();
    }
}


function change_box_visibility(id) {
    let checkBox = document.getElementById(assetCheckBox(id));
    let box = document.getElementById("select" + toTitleCase(id) + "Box");

    if (!checkBox || !box) return;

    let isChecked = checkBox.checked;

    // Update the box's selected state
    box.classList.toggle('accordion-item--not-selected', !isChecked);

    // Find the accordion button and title
    let accordionButton = box.querySelector('.accordion-button');
    let accordionTitle = box.querySelector('.grid-title');

    if (accordionButton) {
        accordionButton.classList.toggle('text-muted', !isChecked);
    }

    if (accordionTitle) {
        accordionTitle.classList.toggle('text-muted', !isChecked);
    }

    // Find the accordion body (skip the checkbox in the header)
    let accordionBody = box.querySelector('.accordion-body');
    if (!accordionBody) return;

    // Special handling for hydrogen - disable all nested accordions
    if (id === 'hydrogen') {
        let nestedAccordions = accordionBody.querySelectorAll('.accordion-item');
        nestedAccordions.forEach(nestedItem => {
            let nestedButton = nestedItem.querySelector('.accordion-button');
            let nestedTitle = nestedItem.querySelector('.grid-title');
            let nestedBody = nestedItem.querySelector('.accordion-body');

            if (nestedButton) nestedButton.classList.toggle('text-muted', !isChecked);
            if (nestedTitle) nestedTitle.classList.toggle('text-muted', !isChecked);

            if (nestedBody) {
                let nestedInputs = nestedBody.querySelectorAll("input, select, textarea, button");
                let nestedLabels = nestedBody.querySelectorAll("label, span.input-group-text");

                nestedInputs.forEach(input => input.disabled = !isChecked);
                nestedLabels.forEach(label => label.classList.toggle('text-muted', !isChecked));
            }
        });
    } else {
        // Regular handling for non-hydrogen components
        let inputs = accordionBody.querySelectorAll("input, select, textarea, button");
        let labels = accordionBody.querySelectorAll("label, span.input-group-text");

        inputs.forEach(input => input.disabled = !isChecked);
        labels.forEach(label => label.classList.toggle('text-muted', !isChecked));
    }

    // Check optimization strategy if applicable
    if (id !== "shortage" && id !== "hydrogen") {
        check_optimization_strategy(id);
    }
}

function refreshBlocksOnDiagramOnLoad() {
    const componentsWithDiagram = ['diesel_genset', 'pv', 'battery', 'inverter', 'rectifier', 'shortage'];

    component.forEach(id => {
        // Only refresh diagram blocks for components that have diagrams
        if (componentsWithDiagram.includes(id)) {
            refreshBlocksOnDiagram(id);
        }

        if (id !== 'shortage' && id !== 'hydrogen') {
            check_box_visibility(id);
            check_optimization_strategy(id);
        } else {
            change_box_visibility(id);
        }
    });

    // Refresh demand diagram
    refreshBlocksOnDiagram('demand');

    if (window.renderESDDiagram) {
        window.renderESDDiagram();
    }

}

function setupAccordionAutoClose() {
    // Get all accordion collapse elements
    const allCollapseElements = document.querySelectorAll('.esd-sidebar__category .accordion-collapse');

    allCollapseElements.forEach(collapseElement => {
        // Listen to Bootstrap's 'shown.bs.collapse' event (fires AFTER the accordion is fully opened)
        collapseElement.addEventListener('shown.bs.collapse', function() {

            // Find all other open accordions
            const allOpenCollapses = document.querySelectorAll('.esd-sidebar__category .accordion-collapse.show');

            allOpenCollapses.forEach(openCollapse => {
                // Skip itself and parent/child relationships
                if (openCollapse !== this &&
                    !openCollapse.contains(this) &&
                    !this.contains(openCollapse)) {

                    const collapseInstance = bootstrap.Collapse.getInstance(openCollapse);
                    if (collapseInstance) {
                        collapseInstance.hide();
                    } else {
                        // If instance doesn't exist, create one and hide
                        const newInstance = new bootstrap.Collapse(openCollapse, {toggle: false});
                        newInstance.hide();
                    }
                }
            });
        });
    });
}

/************************************************************/
/*                 DRAW AND STYLE THE BLOCKS                */

/************************************************************/
function drawBlock(id, x, y) {
    const block = document.getElementById("block" + toTitleCase(id));

    if (id.slice(2, 6) === "Bus") {
        rxy = roundCornerBus;
        width = widthBus;
        height = heightBus;
    } else {
        rxy = roundCornerBlock;
        width = widthBlock;
        height = heightBlock;
    }

    block.setAttribute('x', x);
    block.setAttribute('y', y);
    block.setAttribute('rx', rxy);
    block.setAttribute('ry', rxy);
    block.setAttribute('width', width);
    block.setAttribute('height', height);
}

function styleBlock(id) {
    const block = document.getElementById("block" + toTitleCase(id));
    if (id === 'demand') {
        block.classList.add('components-block--demand');
    } else if (id === 'shortage') {
        // } else if (id === 'shortage' || id === 'surplus') {
        block.classList.add('components-block--constraints');
    } else if (document.getElementById(optimizationCheckBox(id)).checked) {
        block.classList.remove('components-block--dispatch');
        block.classList.add('components-block--design');
    } else {
        block.classList.remove('components-block--design');
        block.classList.add('components-block--dispatch');
    }
}


/************************************************************/
/*                    WRITE THE BLOCK TEXT                  */

/************************************************************/
function writeText(id, x, y) {
    const text = document.getElementById("text" + toTitleCase(id));

    text.setAttribute('x', x);
    text.setAttribute('y', y);
}

function writeInformation(id, x, y) {
    const information = document.getElementById("information" + toTitleCase(id));

    if (id !== 'demand') {
        information.setAttribute('x', x);
        information.setAttribute('y', y);
        if (id == 'shortage') {
            const informationSecondLine = document.getElementById("information" + toTitleCase(id) + "SecondLine");
            informationSecondLine.setAttribute('x', x);
            informationSecondLine.setAttribute('y', 0.9 * y);
        }
    }
}

function styleText(id) {
    const text = document.getElementById("text" + toTitleCase(id));

    if (id === 'demand') {
        text.classList.add('components-text--demand');
    } else if (id === 'shortage') {
        // } else if (id === 'shortage' || id === 'surplus') {
        text.classList.add('components-text--constraints');
    } else if (document.getElementById(optimizationCheckBox(id)).checked) {
        text.classList.remove('components-text--dispatch');
        text.classList.add('components-text--design');
    } else {
        text.classList.remove('components-text--design');
        text.classList.add('components-text--dispatch');
    }

}

function styleInformation(id) {
    const information = document.getElementById("information" + toTitleCase(id));
    if (!information) return; // Exit if the element does not exist

    if (id === 'shortage') {
        const secondLine = document.getElementById("information" + toTitleCase(id) + "SecondLine");
        const maxTotal = document.getElementById("id_shortage_parameters_max_shortage_total")?.value;
        const maxTimestep = document.getElementById("id_shortage_parameters_max_shortage_timestep")?.value;
        const unit = document.getElementById("shortage_parameters_max_shortage_timestep_unit")?.innerText;
        information.textContent = `max. each timestep ${maxTimestep} ${unit}`;
        if (secondLine) {
            secondLine.textContent = `max. total ${maxTotal} ${unit}`;
            secondLine.classList.add('components-information--constraints');
        }
        information.classList.add('components-information--constraints');
    } else {
        const optCheckbox = document.getElementById(optimizationCheckBox(id));
        if (optCheckbox?.checked) {
            information.textContent = "optimized capacity";
            information.classList.replace('components-information--dispatch', 'components-information--design');
        } else {
            const capacity = document.getElementById("id_" + id + "_parameters_nominal_capacity")?.value;
            const unit = document.getElementById(id + "_parameters_nominal_capacity_unit")?.innerText;
            information.textContent = `fixed capacity - ${capacity} ${unit}`;
            information.classList.replace('components-information--design', 'components-information--dispatch');
        }
    }
}

function drawLine(id, linePoints1, linePoints2) {
    // Lines always start from one side of the blocks and end at the bus

    // id is in form of for example linePV or lineDieselGenset
    const line1 = document.getElementById("line" + toTitleCase(id));

    line1.setAttribute('x1', linePoints1[0][0]);
    line1.setAttribute('y1', linePoints1[0][1]);
    line1.setAttribute('x2', linePoints1[1][0]);
    line1.setAttribute('y2', linePoints1[1][1]);

    // For inverter and rectifier there should be two lines.
    if (linePoints2.length > 0) {
        const line2 = document.getElementById("line" + toTitleCase(id) + "2");

        line2.setAttribute('x1', linePoints2[0][0]);
        line2.setAttribute('y1', linePoints2[0][1]);
        line2.setAttribute('x2', linePoints2[1][0]);
        line2.setAttribute('y2', linePoints2[1][1]);
    }
}

function styleLine(id) {
    const line1 = document.getElementById("line" + toTitleCase(id));

    if (id === 'demand') {
        line1.classList.add('components-flow--demand');
    } else if (id === 'shortage') {
        // } else if (id === 'shortage' || id === 'surplus') {
        line1.classList.add('components-flow--constraints');
    } else if (document.getElementById(optimizationCheckBox(id)).checked) {
        line1.classList.remove('components-flow--dispatch');
        line1.classList.add('components-flow--design');
    } else {
        line1.classList.remove('components-flow--design');
        line1.classList.add('components-flow--dispatch');
    }

    // For inverter and rectifier there should be two lines.
    if (id === "inverter" || id === "rectifier") {
        const line2 = document.getElementById("line" + toTitleCase(id) + "2");

        if (document.getElementById(optimizationCheckBox(id)).checked) {
            line2.classList.remove('components-flow--dispatch');
            line2.classList.add('components-flow--design');

        } else {
            line2.classList.remove('components-flow--design');
            line2.classList.add('components-flow--dispatch');
        }
    }
}

function drawArrow(id, arrowOutPoints1, arrowInPoints1, arrowOutPoints2, arrowInPoints2) {
    // The default arrow is the `arrowOut` which always at the end of the line,
    // that means it is outward (block ---> bus ).
    // Another type of arrow is called `arrowIn`, which corresponds to the arrows
    // entering a block (bus ---> block).

    // points should be in the format [[x1,y1], [x2,y2], [x3,y3]]
    const arrowOut1 = document.getElementById("arrowOut" + toTitleCase(id));
    const arrowIn1 = document.getElementById("arrowIn" + toTitleCase(id));

    arrowOut1.setAttribute('points', arrowOutPoints1);
    arrowIn1.setAttribute('points', arrowInPoints1);

    // For inverter and rectifier there are two lines and therefore, two arrows are required
    if (arrowOutPoints2.length > 0) {
        const arrowOut2 = document.getElementById("arrowOut" + toTitleCase(id) + "2");
        const arrowIn2 = document.getElementById("arrowIn" + toTitleCase(id) + "2");

        arrowOut2.setAttribute('points', arrowOutPoints2);
        arrowIn2.setAttribute('points', arrowInPoints2);
    }
}

function styleArrow(id) {
    const arrowOut1 = document.getElementById("arrowOut" + toTitleCase(id));
    const arrowIn1 = document.getElementById("arrowIn" + toTitleCase(id));

    if (id === 'demand') {
        $(arrowOut1).attr("visibility", "hidden");
        arrowIn1.classList.add('components-flow--demand');
    } else if (id === 'shortage') {
        $(arrowIn1).attr("visibility", "hidden");
        arrowOut1.classList.add('components-flow--constraints');
        // } else if (id === 'surplus') {
        //     $(arrowOut1).attr("visibility", "hidden");
        //     arrowIn1.classList.add('components-flow--constraints');
    } else if (document.getElementById(optimizationCheckBox(id)).checked) {
        if (id === 'pv' || id === 'diesel_genset' || id === 'shortage') {
            $(arrowIn1).attr("visibility", "hidden");
            arrowOut1.classList.remove('components-flow--dispatch');
            arrowOut1.classList.add('components-flow--design');
        } else if (id === 'battery') {
            arrowOut1.classList.remove('components-flow--dispatch');
            arrowIn1.classList.remove('components-flow--dispatch');
            arrowOut1.classList.add('components-flow--design');
            arrowIn1.classList.add('components-flow--design');
        } else {
            const arrowOut2 = document.getElementById("arrowOut" + toTitleCase(id) + "2");
            const arrowIn2 = document.getElementById("arrowIn" + toTitleCase(id) + "2");
            if (id === 'rectifier') {
                $(arrowOut1).attr("visibility", "hidden");
                $(arrowIn2).attr("visibility", "hidden");
                arrowOut2.classList.remove('components-flow--dispatch');
                arrowIn1.classList.remove('components-flow--dispatch');
                arrowOut2.classList.add('components-flow--design');
                arrowIn1.classList.add('components-flow--design');
            } else {
                $(arrowOut2).attr("visibility", "hidden");
                $(arrowIn1).attr("visibility", "hidden");
                arrowOut1.classList.remove('components-flow--dispatch');
                arrowIn2.classList.remove('components-flow--dispatch');
                arrowOut1.classList.add('components-flow--design');
                arrowIn2.classList.add('components-flow--design');
            }
        }
        ;
    } else {
        if (id === 'pv' || id === 'diesel_genset' || id === 'shortage') {
            $(arrowIn1).attr("visibility", "hidden");
            arrowOut1.classList.add('components-flow--dispatch');
            arrowOut1.classList.remove('components-flow--design');
        } else if (id === 'battery') {
            arrowOut1.classList.add('components-flow--dispatch');
            arrowIn1.classList.add('components-flow--dispatch');
            arrowOut1.classList.remove('components-flow--design');
            arrowIn1.classList.remove('components-flow--design');
        } else {
            const arrowOut2 = document.getElementById("arrowOut" + toTitleCase(id) + "2");
            const arrowIn2 = document.getElementById("arrowIn" + toTitleCase(id) + "2");
            if (id === 'inverter') {
                $(arrowOut1).attr("visibility", "hidden");
                $(arrowIn2).attr("visibility", "hidden");
                arrowOut2.classList.add('components-flow--dispatch');
                arrowIn1.classList.add('components-flow--dispatch');
                arrowOut2.classList.remove('components-flow--design');
                arrowIn1.classList.remove('components-flow--design');
            } else {
                $(arrowOut2).attr("visibility", "hidden");
                $(arrowIn1).attr("visibility", "hidden");
                arrowOut1.classList.add('components-flow--dispatch');
                arrowIn2.classList.add('components-flow--dispatch');
                arrowOut1.classList.remove('components-flow--design');
                arrowIn2.classList.remove('components-flow--design');
            }
        }
        ;
    }

    // For inverter and rectifier there should be two lines.
    if (id === "inverter" || id === "rectifier") {
        const line2 = document.getElementById("line" + toTitleCase(id) + "2");

        if (document.getElementById(optimizationCheckBox(id)).checked) {
            line2.classList.remove('components-flow--dispatch');
            line2.classList.add('components-flow--design');

        } else {
            line2.classList.remove('components-flow--design');
            line2.classList.add('components-flow--dispatch');
        }
    }

}

function refreshBusesOnDiagram() {
    // This function draw/remove AC and DC buses and their texts in the diagram
    // depending on if the attached blocks to them are selected or not.
    const groupDcBus = document.getElementById("groupDcBus");
    const groupAcBus = document.getElementById("groupAcBus");

    var busCoordinates = {
        'dcBus': {
            'x': xLeft + widthBlock + lengthFlow,
            'y': yTop - heightBlock,
        },
        'acBus': {
            'x': xLeft + 2 * widthBlock + 3 * lengthFlow + widthBus,
            'y': yTop - heightBlock,
        },
    };

    const selectPv = document.getElementById(assetCheckBox("pv")).checked;
    const selectBattery = document.getElementById(assetCheckBox("battery")).checked;
    const selectInverter = document.getElementById(assetCheckBox("inverter")).checked;
    const selectRectifier = document.getElementById(assetCheckBox("rectifier")).checked;

    // Since there is always demand, AC bus is always visible
    $(groupAcBus).attr("visibility", "visible");
    drawBlock(
        id = "acBus",
        x = busCoordinates.acBus.x,
        y = busCoordinates.acBus.y,
    )
    writeText(
        id = "acBus",
        x = busCoordinates.acBus.x + 0.5 * widthBus,
        y = 0.7 * busCoordinates.acBus.y
    )

    // DC bus is not necessarily always visible
    if (selectPv || selectBattery || selectInverter || selectRectifier) {
        $(groupDcBus).attr("visibility", "visible");
        drawBlock(
            id = "dcBus",
            x = busCoordinates.dcBus.x,
            y = busCoordinates.dcBus.y,
        )
        writeText(
            id = "dcBus",
            x = busCoordinates.dcBus.x + 0.5 * widthBus,
            y = 0.7 * busCoordinates.dcBus.y
        )
    } else {
        // First make the SVG group visible
        $(groupDcBus).attr("visibility", "hidden");
    }

}

function refreshBlocksOnDiagram(id) {
    // Skip if this component doesn't have diagram coordinates
    const componentsWithDiagram = ['pv', 'battery', 'inverter', 'rectifier', 'diesel_genset', 'shortage', 'demand', 'surplus'];
    if (!componentsWithDiagram.includes(id)) {
        return;
    }

    // This function draw/remove all blocks and their texts and flows in the diagram depending on
    // if they are selected by user or not.
    // For AC and DC buses, the function `refreshBusesOnDiagram` does the same work.
    const groupId = document.getElementById("group" + toTitleCase(id));

    if (id === 'demand') {
        var isSelected = true;
    } else if (id === 'shortage') {
        // } else if (id === 'shortage' || id === 'surplus') {
        if (document.getElementById(assetCheckBox("shortage")).checked) {
            var isSelected = document.getElementById(assetCheckBox(id)).checked;
        } else {
            var isSelected = false;
        }
    } else {
        var isSelected = document.getElementById(assetCheckBox(id)).checked;
    }

    var blockCoordinates = {
        'pv': {
            'x': xLeft,
            'y': yTop,
        },
        'battery': {
            'x': xLeft,
            'y': yTop + 3 * heightBlock,
        },
        'inverter': {
            'x': xLeft + widthBlock + 2 * lengthFlow + widthBus,
            'y': yTop - 0.5 * heightBlock,
        },
        'rectifier': {
            'x': xLeft + widthBlock + 2 * lengthFlow + widthBus,
            'y': yTop - 0.5 * heightBlock + 2 * heightBlock,
        },
        'diesel_genset': {
            'x': xLeft + widthBlock + 2 * lengthFlow + widthBus,
            'y': yTop - heightBlock / 2 + 4 * heightBlock,
        },
        'shortage': {
            'x': xLeft + 2 * widthBlock + 4 * lengthFlow + 2 * widthBus,
            'y': yTop + 0.5 * heightBlock,
        },
        'demand': {
            'x': xLeft + 2 * widthBlock + 4 * lengthFlow + 2 * widthBus,
            'y': yTop - heightBlock + 3.5 * heightBlock,
        },
        'surplus': {
            'x': xLeft + 2 * widthBlock + 4 * lengthFlow + 2 * widthBus,
            'y': yTop - heightBlock + 5 * heightBlock,
        },
    };

    if (isSelected) {
        // First make the SVG group visible
        $(groupId).attr("visibility", "visible");

        /**************/
        /*   BLOCKS   */
        /**************/
        drawBlock(
            id = id,
            x = blockCoordinates[id].x,
            y = blockCoordinates[id].y,
        )
        styleBlock(id = id);

        /*************/
        /*   TEXTS   */
        /*************/
        writeText(
            id = id,
            x = blockCoordinates[id].x + 0.5 * widthBlock,
            y = blockCoordinates[id].y + 0.5 * heightBlock
        )
        styleText(id);

        writeInformation(
            id = id,
            x = blockCoordinates[id].x,
            y = blockCoordinates[id].y - 0.1 * heightBlock,
        );
        styleInformation(id);


        /***********************/
        /*   LINES AND ARROWS  */
        /***********************/
        if (id === 'demand' || id === 'shortage') {
            // if (id === 'demand' || id === 'surplus' || id === 'shortage') {
            lineCorrectionWidthBlock = 0;
            lineCorrectionLengthFlow = -1;
        } else {
            lineCorrectionWidthBlock = 1;
            lineCorrectionLengthFlow = 1;
        }
        ;
        linePoints1 = [
            [blockCoordinates[id].x + lineCorrectionWidthBlock * widthBlock, blockCoordinates[id].y + 0.5 * heightBlock],
            [blockCoordinates[id].x + lineCorrectionWidthBlock * widthBlock + lineCorrectionLengthFlow * lengthFlow, blockCoordinates[id].y + 0.5 * heightBlock]
        ];

        arrowOutPoints1 = [
            [
                linePoints1[1][0] - lineCorrectionLengthFlow * 0.15 * lengthFlow,
                linePoints1[1][1] - lineCorrectionLengthFlow * 0.1 * lengthFlow
            ],
            [linePoints1[1][0], linePoints1[1][1]],
            [
                linePoints1[1][0] - lineCorrectionLengthFlow * 0.15 * lengthFlow,
                linePoints1[1][1] + lineCorrectionLengthFlow * 0.1 * lengthFlow
            ],
        ];

        arrowInPoints1 = [
            [
                linePoints1[0][0] + lineCorrectionLengthFlow * 0.15 * lengthFlow,
                linePoints1[0][1] - lineCorrectionLengthFlow * 0.1 * lengthFlow
            ],
            [linePoints1[0][0], linePoints1[1][1]],
            [
                linePoints1[0][0] + lineCorrectionLengthFlow * 0.15 * lengthFlow,
                linePoints1[0][1] + lineCorrectionLengthFlow * 0.1 * lengthFlow
            ],
        ];

        // For inverter and rectifier there would be two lines
        if (id === "inverter" || id === "rectifier") {
            lineCorrectionWidthBlock = 0;
            lineCorrectionLengthFlow = -1;
            linePoints2 = [
                [blockCoordinates[id].x + lineCorrectionWidthBlock * widthBlock, blockCoordinates[id].y + 0.5 * heightBlock],
                [blockCoordinates[id].x + lineCorrectionWidthBlock * widthBlock + lineCorrectionLengthFlow * lengthFlow, blockCoordinates[id].y + 0.5 * heightBlock]
            ];

            arrowOutPoints2 = [
                [
                    linePoints2[1][0] - lineCorrectionLengthFlow * 0.15 * lengthFlow,
                    linePoints2[1][1] - lineCorrectionLengthFlow * 0.1 * lengthFlow
                ],
                [linePoints2[1][0], linePoints2[1][1]],
                [
                    linePoints2[1][0] - lineCorrectionLengthFlow * 0.15 * lengthFlow,
                    linePoints2[1][1] + lineCorrectionLengthFlow * 0.1 * lengthFlow
                ],
            ];

            arrowInPoints2 = [
                [
                    linePoints2[0][0] + lineCorrectionLengthFlow * 0.15 * lengthFlow,
                    linePoints2[0][1] - lineCorrectionLengthFlow * 0.1 * lengthFlow
                ],
                [linePoints2[0][0], linePoints2[1][1]],
                [
                    linePoints2[0][0] + lineCorrectionLengthFlow * 0.15 * lengthFlow,
                    linePoints2[0][1] + lineCorrectionLengthFlow * 0.1 * lengthFlow
                ],
            ];
        } else {
            linePoints2 = [];
            arrowOutPoints2 = [];
            arrowInPoints2 = [];
        }
        drawLine(
            id = id,
            linePoints1 = linePoints1,
            linePoints2 = linePoints2
        )
        styleLine(id);

        drawArrow(
            id = id,
            arrowOutPoints1 = arrowOutPoints1,
            arrowInPoints1 = arrowInPoints1,
            arrowOutPoints2 = arrowOutPoints2,
            arrowInPoints2 = arrowInPoints2,
        )
        styleArrow(id);

    } else {
        $(groupId).attr("visibility", "hidden");
    }

    refreshBusesOnDiagram();
}

function toTitleCase(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

  // Wait for D3 to load
function initDiagram() {
    if (typeof d3 === 'undefined') {
      console.error('D3.js not loaded');
      return;
    }

    function readSystemDataFromForm() {
      const isChecked = (id) => {
        const el = document.getElementById(id);
        return !!(el && el.checked);
      };

      return {
        diesel_genset: isChecked("id_diesel_genset_settings_is_selected"),
        pv: isChecked("id_pv_settings_is_selected"),
        battery: isChecked("id_battery_settings_is_selected"),
        hydrogen: isChecked("id_hydrogen_settings_is_selected")
      };
    }

    // Configuration
    const esdConfig = {
      categoryWidth: 232,
      categoryGap: 62,
      componentWidth: 202,
      buildingsWidth: 194,
      componentHeight: 120,
      hydrogenHeight: 186,
      hydrogenSubComponentWidth: 145,
      hydrogenSubComponentHeight: 120,
      hydrogenSubComponentGap: 10,
      categoryPadding: 16,
      borderRadius: 8,
      categoryNumberSize: 24,
      categoryHeaderHeight: 40,
      categoryTopMargin: 50,
      arrowSize: 62
    };

    // Component icons mapping
    const componentIcons = {
      "Diesel Generator": "/static/images/energy-system/component-generator.svg",
      "Solar Panels": "/static/images/energy-system/component-pv.svg",
      "Battery": "/static/images/energy-system/component-battery.svg",
      "Hydrogen": "/static/images/energy-system/component-h2.svg",
      "Fuel cell": "/static/images/energy-system/component-fuel-cell.svg",
      "Hydrogen Storage": "/static/images/energy-system/component-storage.svg",
      "Electrolyzer": "/static/images/energy-system/component-electrolyzer.svg",
      "Buildings": "/static/images/energy-system/component-building.svg"
    };

    window.renderESDDiagram = function () {
        const systemData = readSystemDataFromForm();

      // Clear existing diagram
      d3.select("#esd-diagram").selectAll("*").remove();


    // Component data based on system configuration
    const optBadge = (id) => {
        const el = document.getElementById(optimizationCheckBox(id));
        return (el && el.checked) ? "Optimized" : "Fixed";
    };

          function drawStatusBadge(parentGroup, centerX, centerY, badgeText) {
        const badgeTextWidth = (badgeText || "").length * 6; // keep your existing approximation
        const badgePadding = 8;
        const badgeWidth = badgeTextWidth + badgePadding * 2 + 12; // +12 for dot space
        const badgeHeight = 16;

        const dotColor = badgeText === "Optimized" ? "#6BC779" : "#5E798D";

        const badge = parentGroup.append("g")
          .attr("transform", `translate(${centerX - badgeWidth / 2}, ${centerY - badgeHeight / 2})`);

        badge.append("rect")
          .attr("width", badgeWidth)
          .attr("height", badgeHeight)
          .attr("rx", badgeHeight / 2)
          .attr("ry", badgeHeight / 2)
          .attr("fill", "#fff");

        badge.append("circle")
          .attr("cx", badgePadding + 3)
          .attr("cy", badgeHeight / 2)
          .attr("r", 3)
          .attr("fill", dotColor);

        badge.append("text")
          .attr("class", "esd-badge")
          .attr("x", badgePadding + 10)
          .attr("y", badgeHeight / 2 + 4)
          .text(badgeText);

        return badge;
      }


    function getComponents() {
      const supply = [];
      const storage = [];

      if (systemData.diesel_genset) {
        supply.push({ name: "Diesel Generator", badge: optBadge("diesel_genset") });
      }
      if (systemData.pv) {
        supply.push({ name: "Solar Panels", badge: optBadge("pv") });
      }
      if (systemData.battery) {
        storage.push({ name: "Battery", badge: optBadge("battery") });
      }
      // Hydrogen is handled separately as it spans both categories

      return {
        supply: supply,
        storage: storage,
        use: [{ name: "Buildings", badge: "Active" }],
        hasHydrogen: systemData.hydrogen
      };
    }

    // Calculate category heights based on content
    function getCategoryHeight(componentCount, isUseCategory = false) {
      if (isUseCategory) {
        // Energy Use is just a component, no category box
        return 0;
      }
      if (componentCount === 0) {
        return esdConfig.categoryPadding * 2 + 60; // Space for "No active component"
      }
      return (componentCount * esdConfig.componentHeight) + (esdConfig.categoryPadding * (componentCount + 1));
    }

    const components = getComponents();

    // Calculate the base height for regular components (store for later use)
    const supplyBaseHeight = getCategoryHeight(components.supply.length);
    const storageBaseHeight = getCategoryHeight(components.storage.length);
    const regularComponentsMaxHeight = Math.max(supplyBaseHeight, storageBaseHeight);

    // If hydrogen is present, add its height to both supply and storage
    const supplyHeight = components.hasHydrogen ? supplyBaseHeight + esdConfig.hydrogenHeight + esdConfig.categoryPadding : supplyBaseHeight;
    const storageHeight = components.hasHydrogen ? storageBaseHeight + esdConfig.hydrogenHeight + esdConfig.categoryPadding : storageBaseHeight;

    const maxCategoryHeight = Math.max(supplyHeight, storageHeight);

    const categoryHeights = {
      supply: maxCategoryHeight,
      storage: maxCategoryHeight,
      use: getCategoryHeight(components.use.length, true)
    };

    const maxHeight = Math.max(...Object.values(categoryHeights));

    // Calculate dimensions (now that maxCategoryHeight is defined)
    const leftMargin = 10; // Add margin to prevent border clipping
    const totalWidth = (esdConfig.categoryWidth * 3) + (esdConfig.categoryGap * 2) + (leftMargin * 2);
    const svgHeight = esdConfig.categoryTopMargin + maxCategoryHeight + 100; // Add space for legend with extra margin

    // Create SVG
    const svg = d3.select("#esd-diagram")
      .append("svg")
      .attr("viewBox", `0 0 ${totalWidth} ${svgHeight}`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .style("width", "100%")
      .style("height", "auto")
      .style("max-width", `${totalWidth}px`);

    // Create main group with left margin
    const mainGroup = svg.append("g")
      .attr("transform", `translate(${leftMargin}, 0)`);

    // Define arrowhead marker
    mainGroup.append("defs")
      .append("marker")
      .attr("id", "arrowhead")
      .attr("markerWidth", 10)
      .attr("markerHeight", 10)
      .attr("refX", 9)
      .attr("refY", 3)
      .attr("orient", "auto")
      .append("polygon")
      .attr("points", "0 0, 10 3, 0 6")
      .attr("fill", "#72879A");

    // Category data
    const categories = [
      { id: 1, label: "ENERGY SUPPLY", x: 0 },
      { id: 2, label: "ENERGY STORAGE", x: esdConfig.categoryWidth + esdConfig.categoryGap },
      { id: 3, label: "ENERGY USE", x: (esdConfig.categoryWidth + esdConfig.categoryGap) * 2 }
    ];

  // Draw categories
  categories.forEach((category, idx) => {
      const categoryGroup = mainGroup.append("g")
        .attr("class", "category")
        .attr("transform", `translate(${category.x}, ${esdConfig.categoryTopMargin})`);

      const heightKey = idx === 0 ? 'supply' : idx === 1 ? 'storage' : 'use';
      const height = categoryHeights[heightKey];
      const isUseCategory = idx === 2;

      // Calculate center X position for the category
      const centerX = isUseCategory ? (esdConfig.buildingsWidth / 2) + ((esdConfig.categoryWidth - esdConfig.buildingsWidth) / 2) : esdConfig.categoryWidth / 2;

      // Measure approximate text width to position number dynamically
      const labelWidth = category.label.length * 7; // Approximate width
      const numberOffset = (labelWidth / 2) + 35; // 35px gap from text edge

      // Category number circle (to the left of the centered label)
      categoryGroup.append("circle")
        .attr("cx", centerX - numberOffset)
        .attr("cy", -25)
        .attr("r", 12)
        .attr("fill", "#94A3B8");

      categoryGroup.append("text")
        .attr("class", "esd-category-number")
        .attr("x", centerX - numberOffset)
        .attr("y", -25)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .text(category.id);

      // Category label (above the box, centered)
      categoryGroup.append("text")
        .attr("class", "esd-category-label")
        .attr("x", centerX)
        .attr("y", -22)
        .attr("text-anchor", "middle")
        .text(category.label);

      // Only draw category box for Supply and Storage (not for Use)
      if (!isUseCategory) {
        categoryGroup.append("rect")
          .attr("class", "esd-category-box")
          .attr("width", esdConfig.categoryWidth)
          .attr("height", height);
      }

      // Draw components
      const componentList = idx === 0 ? components.supply : idx === 1 ? components.storage : components.use;

      if (componentList.length === 0 && !isUseCategory) {
        // Show "No active component" only if there's no hydrogen either
        if (!components.hasHydrogen || idx !== 1) {  // idx 1 is storage category
          categoryGroup.append("text")
            .attr("class", "esd-no-component-text")
            .attr("x", esdConfig.categoryWidth / 2)
            .attr("y", height / 2)
            .attr("text-anchor", "middle")
            .text("No active component");
        }
      } else {
        componentList.forEach((component, compIdx) => {
          let componentY;
          let componentWidth;
          let componentHeight;
          let componentX;

          if (isUseCategory) {
            // For Energy Use, make the component stretch to match category height
            componentY = 0;
            componentWidth = esdConfig.buildingsWidth;
            componentHeight = maxCategoryHeight;
            componentX = (esdConfig.categoryWidth - esdConfig.buildingsWidth) / 2;
        } else {
          // For Supply and Storage categories
          // Don't center components if hydrogen is present - they should be at the top
          if (components.hasHydrogen) {
            componentY = esdConfig.categoryPadding + (compIdx * (esdConfig.componentHeight + esdConfig.categoryPadding));
          } else {
            const totalComponentsHeight = (componentList.length * esdConfig.componentHeight) +
                                            ((componentList.length - 1) * esdConfig.categoryPadding);
            const topOffset = (maxCategoryHeight - totalComponentsHeight) / 2;
            componentY = topOffset + (compIdx * (esdConfig.componentHeight + esdConfig.categoryPadding));
          }
          componentWidth = esdConfig.componentWidth;
          componentHeight = esdConfig.componentHeight;
          componentX = esdConfig.categoryPadding;
        }

        const componentGroup = categoryGroup.append("g")
          .attr("class", "component")
          .attr("transform", `translate(${componentX}, ${componentY})`);

        // Component box
        componentGroup.append("rect")
          .attr("class", component.name === "Buildings" ? "esd-component-box buildings" : "esd-component-box")
          .attr("width", componentWidth)
          .attr("height", componentHeight);

        // Component icon
        const iconY = isUseCategory ? componentHeight / 2 - 30 : 35;
        const iconSize = 48;

        componentGroup.append("image")
          .attr("xlink:href", componentIcons[component.name] || "")
          .attr("x", componentWidth / 2 - iconSize / 2)
          .attr("y", iconY - iconSize / 2)
          .attr("width", iconSize)
          .attr("height", iconSize);

        // Component label
        const labelY = isUseCategory ? componentHeight / 2 + 20 : 85;
        componentGroup.append("text")
          .attr("class", component.name === "Buildings" ? "esd-component-label buildings" : "esd-component-label")
          .attr("x", componentWidth / 2)
          .attr("y", labelY)
          .attr("text-anchor", "middle")
          .text(component.name);

        // Badge - 14px below the label (10px + 4px margin)
        if (!isUseCategory) {
          const badgeY = labelY + 14;
          drawStatusBadge(componentGroup, componentWidth / 2, badgeY, component.badge);
          }
        });
      }
  });

  // Draw Hydrogen component if present (spans both Supply and Storage)
  if (components.hasHydrogen) {
    const hydrogenWidth = esdConfig.categoryWidth * 2 + esdConfig.categoryGap - (esdConfig.categoryPadding * 2);
    // Position hydrogen after the regular components (regularComponentsMaxHeight already includes bottom padding)
    const hydrogenY = esdConfig.categoryTopMargin + regularComponentsMaxHeight;
    const hydrogenX = esdConfig.categoryPadding;

    const hydrogenGroup = mainGroup.append("g")
      .attr("class", "hydrogen-component")
      .attr("transform", `translate(${hydrogenX}, ${hydrogenY})`);

    // Hydrogen background box
    hydrogenGroup.append("rect")
      .attr("class", "esd-component-box")
      .attr("width", hydrogenWidth)
      .attr("height", esdConfig.hydrogenHeight)
      .attr("fill", "rgba(223, 229, 237, 0.3)")
      .attr("stroke", "#CBD5E1")
      .attr("stroke-width", 1)
      .attr("rx", 8)
      .attr("ry", 8);

    // Hydrogen title with H2 icon
    const titleGroup = hydrogenGroup.append("g")
      .attr("transform", `translate(${hydrogenWidth / 2}, 20)`);

    // Hydrogen icon/image
    const h2TitleIconSize = 32;
    titleGroup.append("image")
      .attr("xlink:href", componentIcons["Hydrogen"] || "")
      .attr("x", -60)
      .attr("y", -h2TitleIconSize / 2)
      .attr("width", h2TitleIconSize)
      .attr("height", h2TitleIconSize);

    // H2 text
    titleGroup.append("text")
      .attr("x", -20)
      .attr("y", 5)
      .attr("font-size", "16px")
      .attr("font-weight", "bold")
      .attr("fill", "#212529")
      .text("H₂");

    // Hydrogen label
    titleGroup.append("text")
      .attr("x", 5)
      .attr("y", 5)
      .attr("font-size", "16px")
      .attr("font-weight", "bold")
      .attr("fill", "#212529")
      .text("Hydrogen");

    // Sub-components positions
    const subComponentY = 50;
    const totalSubComponentWidth = (esdConfig.hydrogenSubComponentWidth * 3) + (esdConfig.hydrogenSubComponentGap * 2);
    const startX = (hydrogenWidth - totalSubComponentWidth) / 2;

    const fuelCellX = startX;
    const hydrogenStorageX = startX + esdConfig.hydrogenSubComponentWidth + esdConfig.hydrogenSubComponentGap;
    const electrolyzerX = startX + (esdConfig.hydrogenSubComponentWidth * 2) + (esdConfig.hydrogenSubComponentGap * 2);

    // Fuel Cell
    const fuelCellGroup = hydrogenGroup.append("g")
      .attr("transform", `translate(${fuelCellX}, ${subComponentY})`);

    fuelCellGroup.append("rect")
      .attr("width", esdConfig.hydrogenSubComponentWidth)
      .attr("height", esdConfig.hydrogenSubComponentHeight)
      .attr("fill", "#DFE5ED")
      .attr("stroke", "#CBD5E1")
      .attr("stroke-width", 1)
      .attr("rx", 8);

    const h2IconSize = 36;
    fuelCellGroup.append("image")
      .attr("xlink:href", componentIcons["Fuel cell"] || "")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2 - h2IconSize / 2)
      .attr("y", 30 - h2IconSize / 2)
      .attr("width", h2IconSize)
      .attr("height", h2IconSize);

    fuelCellGroup.append("text")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2)
      .attr("y", 68)
      .attr("text-anchor", "middle")
      .attr("font-size", "14px")
      .attr("font-weight", "bold")
      .attr("fill", "#212529")
      .text("Fuel cell");

    fuelCellGroup.append("text")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2)
      .attr("y", 83)
      .attr("text-anchor", "middle")
      .attr("font-size", "11px")
      .attr("fill", "#5E798D")
      .text("Converts to electricity");

    // Fuel cell badge (4px margin from description text)
    const fuelCellBadgeY = 97;
    drawStatusBadge(
      fuelCellGroup,
      esdConfig.hydrogenSubComponentWidth / 2,
      fuelCellBadgeY,
      optBadge("fuel_cell")
      );

    // Hydrogen Storage
    const storageGroup = hydrogenGroup.append("g")
      .attr("transform", `translate(${hydrogenStorageX}, ${subComponentY})`);

    storageGroup.append("rect")
      .attr("width", esdConfig.hydrogenSubComponentWidth)
      .attr("height", esdConfig.hydrogenSubComponentHeight)
      .attr("fill", "#DFE5ED")
      .attr("stroke", "#CBD5E1")
      .attr("stroke-width", 1)
      .attr("rx", 8);

    storageGroup.append("image")
      .attr("xlink:href", componentIcons["Hydrogen Storage"] || "")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2 - h2IconSize / 2)
      .attr("y", 30 - h2IconSize / 2)
      .attr("width", h2IconSize)
      .attr("height", h2IconSize);

    storageGroup.append("text")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2)
      .attr("y", 68)
      .attr("text-anchor", "middle")
      .attr("font-size", "14px")
      .attr("font-weight", "bold")
      .attr("fill", "#212529")
      .text("Hydrogen Storage");

    storageGroup.append("text")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2)
      .attr("y", 83)
      .attr("text-anchor", "middle")
      .attr("font-size", "11px")
      .attr("fill", "#5E798D")
      .text("Stores hydrogen");

    // Hydrogen storage badge (4px margin from description text)
    const storageBadgeY = 97;
    drawStatusBadge(
      storageGroup,
      esdConfig.hydrogenSubComponentWidth / 2,
      storageBadgeY,
      optBadge("h2_storage")
    );

    // Electrolyzer
    const electrolyzerGroup = hydrogenGroup.append("g")
      .attr("transform", `translate(${electrolyzerX}, ${subComponentY})`);

    electrolyzerGroup.append("rect")
      .attr("width", esdConfig.hydrogenSubComponentWidth)
      .attr("height", esdConfig.hydrogenSubComponentHeight)
      .attr("fill", "#DFE5ED")
      .attr("stroke", "#CBD5E1")
      .attr("stroke-width", 1)
      .attr("rx", 8);

    electrolyzerGroup.append("image")
      .attr("xlink:href", componentIcons["Electrolyzer"] || "")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2 - h2IconSize / 2)
      .attr("y", 30 - h2IconSize / 2)
      .attr("width", h2IconSize)
      .attr("height", h2IconSize);

    electrolyzerGroup.append("text")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2)
      .attr("y", 68)
      .attr("text-anchor", "middle")
      .attr("font-size", "14px")
      .attr("font-weight", "bold")
      .attr("fill", "#212529")
      .text("Electrolyzer");

    electrolyzerGroup.append("text")
      .attr("x", esdConfig.hydrogenSubComponentWidth / 2)
      .attr("y", 83)
      .attr("text-anchor", "middle")
      .attr("font-size", "11px")
      .attr("fill", "#5E798D")
      .text("Converts to hydrogen");

    // Electrolyzer badge (4px margin from description text)
    const electrolyzerBadgeY = 97;
    drawStatusBadge(
      electrolyzerGroup,
      esdConfig.hydrogenSubComponentWidth / 2,
      electrolyzerBadgeY,
      optBadge("electrolyzer")
    );

    // Internal arrows showing hydrogen flow
    const arrowY = subComponentY + esdConfig.hydrogenSubComponentHeight / 2;

    // Define internal arrow marker
    mainGroup.append("defs")
      .append("marker")
      .attr("id", "hydrogenArrowhead")
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .attr("refX", 7)
      .attr("refY", 2.5)
      .attr("orient", "auto")
      .append("polygon")
      .attr("points", "0 0, 8 2.5, 0 5")
      .attr("fill", "#94A3B8");

    // Arrow from Hydrogen Storage to Fuel Cell (curved, pointing left)
    const arrow1StartX = hydrogenStorageX;
    const arrow1EndX = fuelCellX + esdConfig.hydrogenSubComponentWidth;
    const arrow1Y = arrowY;

    hydrogenGroup.append("path")
      .attr("d", `M ${arrow1StartX} ${arrow1Y} Q ${arrow1StartX - 15} ${arrow1Y + 20}, ${arrow1EndX} ${arrow1Y}`)
      .attr("stroke", "#94A3B8")
      .attr("stroke-width", 2)
      .attr("fill", "none")
      .attr("marker-end", "url(#hydrogenArrowhead)");

    // Arrow from Electrolyzer to Hydrogen Storage (curved, pointing left)
    const arrow2StartX = electrolyzerX;
    const arrow2EndX = hydrogenStorageX + esdConfig.hydrogenSubComponentWidth;
    const arrow2Y = arrowY;

    hydrogenGroup.append("path")
      .attr("d", `M ${arrow2StartX} ${arrow2Y} Q ${arrow2StartX - 15} ${arrow2Y + 20}, ${arrow2EndX} ${arrow2Y}`)
      .attr("stroke", "#94A3B8")
      .attr("stroke-width", 2)
      .attr("fill", "none")
      .attr("marker-end", "url(#hydrogenArrowhead)");
  }

  // Draw arrows between categories
  function drawArrow(fromX, toX, y) {
    const startX = fromX + esdConfig.categoryWidth;
    const endX = toX;
    const arrowY = y;

    mainGroup.append("path")
      .attr("class", "esd-arrow")
      .attr("d", `M ${startX} ${arrowY} L ${endX} ${arrowY}`);
  }

  // Calculate arrow Y positions based on category centers
  const arrowY = esdConfig.categoryTopMargin + (maxCategoryHeight / 2);

  // Arrow from Supply to Storage
  drawArrow(0, esdConfig.categoryWidth + esdConfig.categoryGap, arrowY);

  // Arrow from Storage to Use
  // Calculate the left edge of the Buildings component
  const buildingsX = (esdConfig.categoryWidth + esdConfig.categoryGap) * 2 + (esdConfig.categoryWidth - esdConfig.buildingsWidth) / 2;
  drawArrow(
    esdConfig.categoryWidth + esdConfig.categoryGap,
    buildingsX,
    arrowY
  );

  // Add legend text
  let legendText = "";
  if (systemData.hydrogen && systemData.battery) {
    legendText = "Sun and diesel produce electricity → stored in battery or converted to hydrogen → used by buildings";
  } else if (systemData.hydrogen) {
    legendText = "Sun and diesel produce electricity → converted to hydrogen → used by buildings";
  } else if (systemData.pv && systemData.battery) {
    legendText = "Sun and diesel produce electricity → stored in battery → used by buildings";
  } else if (systemData.battery) {
    legendText = "Diesel produces electricity → stored in battery → used by buildings";
  } else if (systemData.pv) {
    legendText = "Sun and diesel produce electricity → used by buildings";
  } else {
    legendText = "Diesel produces electricity → used by buildings";
  }

  mainGroup.append("text")
    .attr("class", "esd-legend-text")
    .attr("x", (totalWidth - leftMargin * 2) / 2)
    .attr("y", esdConfig.categoryTopMargin + maxCategoryHeight + 50)
    .attr("text-anchor", "middle")
    .text(legendText);
  };

  window.renderESDDiagram();
  };

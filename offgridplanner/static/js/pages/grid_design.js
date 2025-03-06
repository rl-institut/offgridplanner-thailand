const shsDiv = document.getElementById("selectShsBox")
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
    } else {
        shsDiv.classList.add('box--not-selected');
        maxGridCostInput.disabled = true;
        shsLifetimeLabel.classList.add('disabled');
        shsLifetimeUnit.classList.add('disabled');
    }
}

document.addEventListener('DOMContentLoaded', function () {
    shsCheckbox.addEventListener("change", change_shs_box_visibility);
});

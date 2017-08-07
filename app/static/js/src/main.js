$(document).ready(function(){

    /* Semantic UI
     ************************************************/
    $('.tabmenu .item').tab({history:false});
    $('.ui.radio.checkbox').checkbox();
    $('.ui.checkbox').checkbox();
    $('.ui.dropdown').dropdown();
    $('select.dropdown').dropdown();
    $('.accordion').accordion();
    $('.ui.rating').rating("disable");
    $('.tooltip').popup();

    /* Sliders
     **********************/
    $('input[type="range"]').change(function(e) {
     $(this).closest(".ui.grid").find(".slidervalue")[0].value = $(this).val();
    });
    $('input[class="slidervalue"]').change(function(e) {
     $(this).closest(".ui.grid").find('input[type="range"]')[0].value = $(this).val();
    });

});

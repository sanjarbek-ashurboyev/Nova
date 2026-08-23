// Phone number masks for the login/register modal
$('#phone-mask').inputmask({
    "mask": "+\\9\\98(99) 999-99-99"
});
$('#phone-mask-two').inputmask({
    "mask": "+\\9\\98(99) 999-99-99"
});

$(document).ready(function () {
    // Phone mask initialization
    $('#phone-mask').inputmask({"mask": "+\\9\\98(99) 999-99-99"});
    $('#phone-mask1').inputmask({"mask": "+\\9\\98(99) 999-99-99"});

    // Owl Carousel initialization
    $('.owl-carousel-category').owlCarousel({
        loop: false,
        margin: 15,
        nav: true,
        dots: false,
        responsive: {
            0: {items: 2},
            576: {items: 3},
            768: {items: 4},
            992: {items: 5}
        }
    });
});
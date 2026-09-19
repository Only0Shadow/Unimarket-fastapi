// Vanilla JS is kept minimal by design -- almost everything in this app
// works via plain HTML forms and full-page navigations so it degrades
// gracefully. This file is a home for small progressive-enhancement
// touches only.

document.addEventListener("DOMContentLoaded", () => {
    // Confirm before destructive actions that don't already have an
    // inline onsubmit confirm (e.g. archiving a product).
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const message = form.getAttribute("data-confirm") || "Are you sure?";
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });
});

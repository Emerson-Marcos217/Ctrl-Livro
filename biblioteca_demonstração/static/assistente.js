const readingForm = document.getElementById("reading-form");
const readingButton = document.getElementById("reading-submit");
const readingStatus = document.getElementById("reading-status");
if (readingForm && readingButton) {
  readingForm.addEventListener("submit", () => {
    readingButton.disabled = true;
    readingStatus.hidden = false;
    readingForm.setAttribute("aria-busy", "true");
  });
  window.addEventListener("pageshow", () => {
    readingButton.disabled = false;
    readingStatus.hidden = true;
    readingForm.removeAttribute("aria-busy");
  });
}

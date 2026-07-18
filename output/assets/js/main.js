const button = document.querySelector(".menu-toggle");
const nav = document.querySelector(".top-nav");

if (button && nav) {
  const setMenu = (open) => {
    nav.classList.toggle("is-open", open);
    document.body.classList.toggle("menu-open", open);
    button.setAttribute("aria-expanded", String(open));
    button.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
  };

  button.setAttribute("aria-expanded", "false");
  button.setAttribute("aria-controls", "primary-navigation");
  nav.id = "primary-navigation";

  button.addEventListener("click", () => {
    setMenu(!nav.classList.contains("is-open"));
  });

  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) setMenu(false);
  });

  document.addEventListener("click", (event) => {
    if (
      nav.classList.contains("is-open") &&
      !nav.contains(event.target) &&
      !button.contains(event.target)
    ) {
      setMenu(false);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && nav.classList.contains("is-open")) {
      setMenu(false);
      button.focus();
    }
  });
}

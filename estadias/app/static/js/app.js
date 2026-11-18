// Interactividad mínima (sin scripts inline por la Content-Security-Policy)
(function () {
  // 1. Ventana de confirmación para formularios con data-confirm
  const dlg = document.getElementById("dlg-confirmar");
  let pendiente = null;
  document.addEventListener("submit", (ev) => {
    const form = ev.target;
    if (!dlg || !form.dataset.confirm || form.dataset.confirmado) return;
    ev.preventDefault();
    pendiente = form;
    dlg.querySelector("[data-msg]").textContent = form.dataset.confirm;
    dlg.showModal();
  });
  if (dlg) {
    dlg.querySelector("[data-si]").addEventListener("click", () => {
      dlg.close();
      if (pendiente) { pendiente.dataset.confirmado = "1"; pendiente.requestSubmit(); }
    });
    dlg.querySelector("[data-no]").addEventListener("click", () => { dlg.close(); pendiente = null; });
  }

  // 2. Búsqueda rápida en tablas: <input data-filtro="#id-tabla">
  document.querySelectorAll("[data-filtro]").forEach((input) => {
    const tabla = document.querySelector(input.dataset.filtro);
    input.addEventListener("input", () => {
      const t = input.value.toLowerCase().trim();
      tabla.querySelectorAll("tbody tr").forEach((tr) => {
        tr.classList.toggle("oculto", t && !tr.textContent.toLowerCase().includes(t));
      });
    });
  });

  // 3. Menú lateral en móvil
  const btnMenu = document.querySelector("[data-menu]");
  if (btnMenu) btnMenu.addEventListener("click", () => document.getElementById("lateral").classList.toggle("hidden"));

  // 4. Seleccionar todos (asignación masiva)
  const todos = document.querySelector("[data-todos]");
  if (todos) todos.addEventListener("change", () => {
    document.querySelectorAll("input[name=ids]").forEach((c) => {
      if (!c.closest("tr").classList.contains("oculto")) c.checked = todos.checked;
    });
  });

  // 5. Requisito: mostrar grupos solo si es "específico"
  const tipo = document.querySelectorAll("input[name=tipo]");
  const bloque = document.getElementById("bloque-grupos");
  if (tipo.length && bloque) {
    const actualizar = () => bloque.classList.toggle("hidden", document.querySelector("input[name=tipo]:checked").value !== "especifico");
    tipo.forEach((r) => r.addEventListener("change", actualizar));
    actualizar();
  }

  // 5b. Registro de prueba: datos de alumno solo si el rol es "alumno"
  const roles = document.querySelectorAll("input[name=rol]");
  const bloqueAlumno = document.getElementById("bloque-alumno");
  if (roles.length && bloqueAlumno) {
    const actualizarRol = () => {
      const marcado = document.querySelector("input[name=rol]:checked");
      bloqueAlumno.classList.toggle("hidden", !marcado || marcado.value !== "alumno");
    };
    roles.forEach((r) => r.addEventListener("change", actualizarRol));
    actualizarRol();
  }

  // 6. Revisión: la observación es obligatoria si no se aprueba
  document.querySelectorAll("form[data-revision]").forEach((form) => {
    form.addEventListener("submit", (ev) => {
      const boton = ev.submitter;
      const obs = form.querySelector("textarea[name=observacion]");
      if (boton && boton.value !== "aprobado" && !obs.value.trim()) {
        ev.preventDefault();
        ev.stopImmediatePropagation();
        obs.focus();
        obs.classList.add("ring-2", "ring-rose-400");
        form.querySelector("[data-obs-aviso]").classList.remove("hidden");
      }
    }, true);
  });

  // 7. Mostrar el nombre del archivo elegido y deshabilitar el botón al enviar
  document.querySelectorAll("form[data-subida]").forEach((form) => {
    form.addEventListener("submit", () => {
      const b = form.querySelector("button[type=submit]");
      if (b) { b.disabled = true; b.textContent = "Subiendo…"; }
    });
  });
})();

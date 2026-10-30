// IA utilizada: não foi utilizada neste projeto. Código foi construído e explicado manualmente.

const body = document.body;
const themeToggle = document.querySelector(".theme-toggle");
const menuToggle = document.querySelector(".menu-toggle");
const nav = document.querySelector(".site-nav");
const greeting = document.getElementById("greeting");
const year = document.getElementById("year");
const form = document.getElementById("contactForm");

function obterSaudacao(hora) {
  if (hora < 12) {
    return "Bom dia";
  } else if (hora < 18) {
    return "Boa tarde";
  } else {
    return "Boa noite";
  }
}

// Função: alterna o tema claro/escuro e salva a preferência no navegador.
function alternarTema() {
  const temaAtual = body.classList.toggle("light-theme");
  localStorage.setItem("theme", temaAtual ? "light" : "dark");

  const icon = themeToggle.querySelector(".theme-icon");
  icon.textContent = temaAtual ? "🌙" : "☀️";
}

// Função: aplica a saudação dinâmica com base na hora atual.
function atualizarSaudacao() {
  const horaAtual = new Date().getHours();
  greeting.textContent = obterSaudacao(horaAtual);
}

// Função: abre e fecha o menu no mobile.
function toggleMenu() {
  const isOpen = nav.classList.toggle("is-open");
  menuToggle.setAttribute("aria-expanded", String(isOpen));
}

// Função: valida o formulário e mostra mensagens de erro abaixo dos campos.
function validarFormulario() {
  const nome = document.getElementById("name");
  const email = document.getElementById("email");
  const mensagem = document.getElementById("message");
  const consentimento = document.getElementById("consent");
  const status = document.getElementById("formStatus");

  let valido = true;

  const campos = [nome, email, mensagem];
  campos.forEach((campo) => {
    const erro = campo.parentElement.querySelector(".error-message");
    erro.textContent = "";
    campo.setAttribute("aria-invalid", "false");
  });

  if (nome.value.trim().length < 2) {
    const erro = nome.parentElement.querySelector(".error-message");
    erro.textContent = "Informe seu nome completo.";
    nome.setAttribute("aria-invalid", "true");
    valido = false;
  }

  if (!email.value.includes("@") || !email.value.includes(".")) {
    const erro = email.parentElement.querySelector(".error-message");
    erro.textContent = "Informe um e-mail válido.";
    email.setAttribute("aria-invalid", "true");
    valido = false;
  }

  if (mensagem.value.trim().length < 20) {
    const erro = mensagem.parentElement.querySelector(".error-message");
    erro.textContent = "A mensagem deve ter pelo menos 20 caracteres.";
    mensagem.setAttribute("aria-invalid", "true");
    valido = false;
  }

  if (!consentimento.checked) {
    status.textContent = "Você precisa aceitar o consentimento antes de enviar.";
    status.style.color = "var(--error)";
    valido = false;
  }

  if (valido) {
    status.textContent = "Mensagem enviada com sucesso! Em breve retorno.";
    status.style.color = "var(--success)";
    form.reset();
    return true;
  }

  status.textContent = "Corrija os campos destacados antes de enviar.";
  status.style.color = "var(--error)";
  return false;
}

// Função: gera os cards de projetos a partir de um array de objetos.
function renderizarProjetos() {
  const projetos = [
    {
      titulo: "Senacursos",
      categoria: "Landing Page",
      descricao:
        "Plataforma de cursos online com foco em divulgação de disciplinas, facilidade de navegação e visual moderno para atrair estudantes.",
      tecnologias: ["HTML", "CSS", "Responsivo"]
    },
    {
      titulo: "Locadora",
      categoria: "Dashboard",
      descricao:
        "Sistema de gerenciamento de locação de veículos com interface organizada, busca por itens e apresentação clara das informações principais.",
      tecnologias: ["Grid", "JS", "UX"]
    },
    {
      titulo: "Empresa de Artesanato",
      categoria: "Portfólio",
      descricao:
        "Site institucional para divulgar produtos artesanais, contar a história da marca e apresentar peças com uma estética acolhedora e profissional.",
      tecnologias: ["Branding", "Layout", "Dark mode"]
    }
  ];

  const container = document.getElementById("projectList");

  projetos.forEach((projeto) => {
    const article = document.createElement("article");
    article.className = "project-card";

    const thumb = document.createElement("div");
    thumb.className = "project-thumb";

    const thumbVariant =
      projeto.categoria === "Landing Page"
        ? "thumb-one"
        : projeto.categoria === "Dashboard"
        ? "thumb-two"
        : "thumb-three";

    thumb.classList.add(thumbVariant);
    thumb.innerHTML = `<span>${projeto.categoria}</span>`;

    const body = document.createElement("div");
    body.className = "project-body";

    const titulo = document.createElement("h3");
    titulo.textContent = projeto.titulo;

    const paragrafo = document.createElement("p");
    paragrafo.textContent = projeto.descricao;

    const lista = document.createElement("ul");
    lista.className = "project-tags";

    projeto.tecnologias.forEach((tecnologia) => {
      const item = document.createElement("li");
      item.textContent = tecnologia;
      lista.appendChild(item);
    });

    body.appendChild(titulo);
    body.appendChild(paragrafo);
    body.appendChild(lista);

    article.appendChild(thumb);
    article.appendChild(body);

    container.appendChild(article);
  });
}

const savedTheme = localStorage.getItem("theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

if (savedTheme === "light" || (!savedTheme && !prefersDark)) {
  body.classList.add("light-theme");
  themeToggle.querySelector(".theme-icon").textContent = "🌙";
} else {
  themeToggle.querySelector(".theme-icon").textContent = "☀️";
}

themeToggle.addEventListener("click", alternarTema);
menuToggle.addEventListener("click", toggleMenu);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && nav.classList.contains("is-open")) {
    nav.classList.remove("is-open");
    menuToggle.setAttribute("aria-expanded", "false");
  }
});

nav.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    nav.classList.remove("is-open");
    menuToggle.setAttribute("aria-expanded", "false");
  });
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  validarFormulario();
});

year.textContent = new Date().getFullYear();
atualizarSaudacao();
renderizarProjetos();
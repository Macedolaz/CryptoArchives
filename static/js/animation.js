// Função para simular digitação automática
function typeWriter(textElement, text, speed) {
  let i = 0;
  const typingEffect = setInterval(() => {
    if (i < text.length) {
      textElement.textContent += text.charAt(i);
      i++;
    } else {
      clearInterval(typingEffect);
      setTimeout(() => {
        eraseText(textElement, text, speed);
      }, 1000); // Tempo para o texto ficar visível antes de apagar
    }
  }, speed);
}

// Função para apagar o texto
function eraseText(textElement, text, speed) {
  let i = text.length - 1;
  const erasingEffect = setInterval(() => {
    if (i >= 0) {
      textElement.textContent = text.substring(0, i);
      i--;
    } else {
      clearInterval(erasingEffect);
      setTimeout(() => {
        typeWriter(textElement, text, speed);
      }, 500); // Tempo antes de começar a digitar novamente
    }
  }, speed);
}

// Iniciar o efeito de digitação automática ao carregar a página
document.addEventListener('DOMContentLoaded', () => {
  const textElement = document.getElementById('typing-animation');
  const text = textElement.textContent.trim();
  const speed = 100; // Velocidade de digitação em milissegundos

  typeWriter(textElement, text, speed);
});
document.addEventListener("DOMContentLoaded", () => {
  const rawInput = document.getElementById("rawInput");
  const titleOverride = document.getElementById("titleOverride");
  const authorOverride = document.getElementById("authorOverride");
  const deptOverride = document.getElementById("deptOverride");
  const charCount = document.getElementById("charCount");
  const wordCount = document.getElementById("wordCount");
  const saveStatus = document.getElementById("saveStatus");
  const btnGenerate = document.getElementById("btnGenerate");
  const btnClear = document.getElementById("btnClear");
  const btnSample = document.getElementById("btnSample");
  const btnUpload = document.getElementById("btnUpload");
  const fileInput = document.getElementById("fileInput");
  const dropZone = document.getElementById("dropZone");
  const dropOverlay = document.getElementById("dropOverlay");
  const previewFrame = document.getElementById("previewFrame");
  const emptyState = document.getElementById("emptyState");
  const btnPrint = document.getElementById("btnPrint");
  const btnCopyHtml = document.getElementById("btnCopyHtml");
  const btnOpenNewTab = document.getElementById("btnOpenNewTab");
  const btnDownloadDocx = document.getElementById("btnDownloadDocx");
  const metaBar = document.getElementById("metaBar");
  const selectSignature = document.getElementById("selectSignature");
  const selectOrientation = document.getElementById("selectOrientation");
  const checkMetaBox = document.getElementById("checkMetaBox");
  const checkSubtitle = document.getElementById("checkSubtitle");
  const checkDescricaoGeral = document.getElementById("checkDescricaoGeral");
  
  // Controles de Logo
  const btnUploadLogo = document.getElementById("btnUploadLogo");
  const logoFileInput = document.getElementById("logoFileInput");
  const logoPreviewContainer = document.getElementById("logoPreviewContainer");
  const logoThumb = document.getElementById("logoThumb");
  const logoFileName = document.getElementById("logoFileName");
  const btnRemoveLogo = document.getElementById("btnRemoveLogo");
  const btnToggleTheme = document.getElementById("btnToggleTheme");
  const themeIcon = document.getElementById("themeIcon");
  const themeLabel = document.getElementById("themeLabel");
  const THEME_KEY = "modelo_relatorio_theme";
  // Controles de Menu Retrátil
  const btnToggleToolbar = document.getElementById("btnToggleToolbar");
  const collapsibleToolbar = document.getElementById("collapsibleToolbar");
  const paramsActiveCount = document.getElementById("paramsActiveCount");
  const TOOLBAR_OPEN_KEY = "modelo_relatorio_toolbar_open";

  function updateParamsActiveCount() {
    let count = 0;
    if (titleOverride.value.trim()) count++;
    if (deptOverride.value.trim()) count++;
    if (authorOverride.value.trim()) count++;
    if (currentLogoBase64) count++;
    if (selectOrientation.value === "landscape") count++;
    if (selectSignature.value === "nao") count++;
    if (!checkMetaBox.checked) count++;
    if (!checkSubtitle.checked) count++;
    if (checkDescricaoGeral.checked) count++;

    if (paramsActiveCount) {
      if (count > 0) {
        paramsActiveCount.textContent = count;
        paramsActiveCount.style.display = "inline-block";
      } else {
        paramsActiveCount.style.display = "none";
      }
    }
  }

  function setToolbarState(isOpen) {
    if (isOpen) {
      collapsibleToolbar.style.display = "block";
      btnToggleToolbar.classList.add("active");
    } else {
      collapsibleToolbar.style.display = "none";
      btnToggleToolbar.classList.remove("active");
    }
    localStorage.setItem(TOOLBAR_OPEN_KEY, isOpen ? "1" : "0");
  }

  if (btnToggleToolbar && collapsibleToolbar) {
    btnToggleToolbar.addEventListener("click", () => {
      const isCurrentlyOpen = collapsibleToolbar.style.display !== "none";
      setToolbarState(!isCurrentlyOpen);
    });

    // Restaura estado salvo do menu retrátil (padrão: recolhido para layout limpo)
    const savedToolbarOpen = localStorage.getItem(TOOLBAR_OPEN_KEY);
    if (savedToolbarOpen === "1") {
      setToolbarState(true);
    } else {
      setToolbarState(false);
    }
  }

  let currentLogoBase64 = "";
  let lastHtmlContent = "";
  let currentReportUrl = "";
  let saveTimeout = null;

  function applyTheme(isLight) {
    if (isLight) {
      document.body.classList.add("light-theme");
      if (themeIcon) themeIcon.textContent = "🌙";
      if (themeLabel) themeLabel.textContent = "Modo Escuro";
    } else {
      document.body.classList.remove("light-theme");
      if (themeIcon) themeIcon.textContent = "☀️";
      if (themeLabel) themeLabel.textContent = "Modo Claro";
    }
  }

  // Carrega preferência do tema salva
  const savedTheme = localStorage.getItem(THEME_KEY);
  if (savedTheme === "light") {
    applyTheme(true);
  }

  if (btnToggleTheme) {
    btnToggleTheme.addEventListener("click", () => {
      const isCurrentlyLight = document.body.classList.contains("light-theme");
      const nextIsLight = !isCurrentlyLight;
      applyTheme(nextIsLight);
      localStorage.setItem(THEME_KEY, nextIsLight ? "light" : "dark");
    });
  }

  // 1. Contador de Caracteres e Palavras
  function updateCounters() {
    const text = rawInput.value;
    charCount.textContent = `${text.length} caracteres`;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    if (wordCount) {
      wordCount.textContent = `${words} palavras`;
    }
  }

  // 2. Auto-save no LocalStorage (Draft)
  const STORAGE_KEY = "modelo_relatorio_draft";

  function saveDraft() {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      const draft = {
        text: rawInput.value,
        title: titleOverride.value,
        dept: deptOverride.value,
        author: authorOverride.value,
        orientation: selectOrientation.value,
        signature: selectSignature.value,
        metaBox: checkMetaBox.checked,
        subtitle: checkSubtitle.checked,
        descricaoGeral: checkDescricaoGeral.checked,
        logo: currentLogoBase64,
        logoName: logoFileName.textContent
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
      if (saveStatus) {
        saveStatus.classList.add("visible");
        setTimeout(() => saveStatus.classList.remove("visible"), 2000);
      }
    }, 600);
  }

  function loadDraft() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const draft = JSON.parse(saved);
        if (draft.text) rawInput.value = draft.text;
        if (draft.title) titleOverride.value = draft.title;
        if (draft.dept) deptOverride.value = draft.dept;
        if (draft.author) authorOverride.value = draft.author;
        if (draft.orientation) selectOrientation.value = draft.orientation;
        if (draft.signature) selectSignature.value = draft.signature;
        if (typeof draft.metaBox === "boolean") checkMetaBox.checked = draft.metaBox;
        if (typeof draft.subtitle === "boolean") checkSubtitle.checked = draft.subtitle;
        if (typeof draft.descricaoGeral === "boolean") checkDescricaoGeral.checked = draft.descricaoGeral;
        if (draft.logo) {
          currentLogoBase64 = draft.logo;
          logoThumb.src = currentLogoBase64;
          logoFileName.textContent = draft.logoName || "logo.png";
          logoPreviewContainer.style.display = "flex";
        }
        updateCounters();
        updateParamsActiveCount();
        if (rawInput.value.trim()) {
          formatReport(false); // formata sem loading obstrutivo na inicialização
        }
      }
    } catch (e) {
      console.error("Erro ao carregar rascunho:", e);
    }
  }

  const formatStatus = document.getElementById("formatStatus");
  let liveFormatTimeout = null;

  function triggerLiveFormat(delay = 600) {
    if (liveFormatTimeout) clearTimeout(liveFormatTimeout);
    if (!rawInput.value.trim()) return;

    if (formatStatus) {
      formatStatus.classList.add("syncing");
      formatStatus.textContent = "⚡ Atualizando prévia...";
    }

    liveFormatTimeout = setTimeout(() => {
      formatReport(false).then(() => {
        if (formatStatus) {
          formatStatus.classList.remove("syncing");
          formatStatus.textContent = "⚡ Atualização em tempo real ativa";
        }
      });
    }, delay);
  }

  // Monitora alterações para atualizar contadores, salvar rascunho e auto-formatar
  rawInput.addEventListener("input", () => {
    updateCounters();
    saveDraft();
    triggerLiveFormat(500); // formata 500ms após o usuário parar de digitar
  });

  [titleOverride, deptOverride, authorOverride].forEach(input => {
    input.addEventListener("input", () => {
      updateParamsActiveCount();
      saveDraft();
      triggerLiveFormat(400);
    });
  });

  // 3. Re-renderização Reativa nos Toggles e Selects
  const autoUpdateControls = [
    selectOrientation,
    selectSignature,
    checkMetaBox,
    checkSubtitle,
    checkDescricaoGeral
  ];

  autoUpdateControls.forEach(ctrl => {
    ctrl.addEventListener("change", () => {
      updateParamsActiveCount();
      saveDraft();
      triggerLiveFormat(50); // atualização imediata nas opções
    });
  });

  // 4. Logo Uploader
  btnUploadLogo.addEventListener("click", () => logoFileInput.click());

  logoFileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        currentLogoBase64 = event.target.result;
        logoThumb.src = currentLogoBase64;
        logoFileName.textContent = file.name;
        logoPreviewContainer.style.display = "flex";
        saveDraft();
        if (rawInput.value.trim()) {
          formatReport(false);
        }
      };
      reader.readAsDataURL(file);
    }
  });

  btnRemoveLogo.addEventListener("click", () => {
    currentLogoBase64 = "";
    logoFileInput.value = "";
    logoPreviewContainer.style.display = "none";
    saveDraft();
    if (rawInput.value.trim()) {
      formatReport(false);
    }
  });

  // Exemplo padrão
  const sampleText = `# Relatório Técnico de Fiscalização de Obras Públicas
Subtítulo: Vistoria In Loco - Reforma da Unidade Básica de Saúde Central
Órgão: Secretaria Municipal de Infraestrutura e Obras
Autor: Eng. Carlos Alberto Silveira
Data: 14/10/2026
Código: REL-OBRAS-2026-089

## 1. OBJETIVO DA VISTORIA
O presente relatório tem por objetivo registrar as condições estruturais e o andamento físico-financeiro da reforma geral da UBS Central, contratada sob o regime de empreitada por preço global.

## 2. METODOLOGIA APLICADA
A inspeção técnica foi realizada por meio de verificação visual, registro fotográfico e conferência do diário de obra. Foram analisados os seguintes pontos:
* Estabilidade das estruturas de alvenaria e cobertura;
* Adequação dos sistemas hidrossanitários e elétricos;
* Conformidade do cronograma com as medições apresentadas.

## 3. ANDAMENTO DAS ETAPAS (CRONOGRAMA)

| Etapa da Obra | Previsto (%) | Executado (%) | Situação |
|---|---|---|---|
| Demolições e Fundação | 100% | 100% | Concluído |
| Alvenaria e Paredes | 85% | 90% | Adiantado |
| Instalações Elétricas | 60% | 45% | Em Atraso |
| Pintura e Acabamento | 20% | 10% | Em Andamento |

## 4. CONCLUSÃO E ENCAMINHAMENTOS
Recomenda-se a notificação imediata da empresa executora para reforçar a equipe de instalações elétricas, evitando comprometimento do prazo de entrega final. A liberação da 4ª medição fica condicionada à regularização dos apontamentos de segurança.`;

  // Carregar Exemplo
  btnSample.addEventListener("click", () => {
    rawInput.value = sampleText;
    titleOverride.value = "";
    deptOverride.value = "";
    authorOverride.value = "";
    updateCounters();
    updateParamsActiveCount();
    saveDraft();
    formatReport();
  });

  // Limpar
  btnClear.addEventListener("click", () => {
    rawInput.value = "";
    titleOverride.value = "";
    authorOverride.value = "";
    deptOverride.value = "";
    currentLogoBase64 = "";
    logoFileInput.value = "";
    logoPreviewContainer.style.display = "none";
    updateCounters();
    updateParamsActiveCount();
    previewFrame.srcdoc = "";
    emptyState.style.display = "block";
    btnPrint.disabled = true;
    btnOpenNewTab.style.display = "none";
    if (btnDownloadDocx) btnDownloadDocx.style.display = "none";
    if (btnCopyHtml) btnCopyHtml.style.display = "none";
    metaBar.style.display = "none";
    localStorage.removeItem(STORAGE_KEY);
  });

  // Upload por botão
  btnUpload.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      readFile(file);
    }
  });

  // Drag and Drop
  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropOverlay.classList.add("active");
  });

  dropZone.addEventListener("dragleave", (e) => {
    if (e.relatedTarget && !dropZone.contains(e.relatedTarget)) {
      dropOverlay.classList.remove("active");
    }
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropOverlay.classList.remove("active");
    const file = e.dataTransfer.files[0];
    if (file) {
      readFile(file);
    }
  });

  function readFile(file) {
    if (file.name.toLowerCase().endsWith(".docx")) {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          if (formatStatus) {
            formatStatus.classList.add("syncing");
            formatStatus.textContent = "⏳ Importando e analisando documento DOCX...";
          }
          const res = await fetch("/api/parse-docx", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_base64: event.target.result })
          });
          const result = await res.json();
          if (result.success) {
            if (result.title) titleOverride.value = result.title;
            if (result.orgao) deptOverride.value = result.orgao;
            if (result.autor) authorOverride.value = result.autor;
            if (result.logo) {
              currentLogoBase64 = result.logo;
              logoThumb.src = currentLogoBase64;
              logoFileName.textContent = "brasao_docx.png";
              logoPreviewContainer.style.display = "flex";
            }
            rawInput.value = result.markdown || "";
            updateCounters();
            saveDraft();
            formatReport(false);
          } else {
            alert("Erro ao ler DOCX: " + (result.error || "Formato desconhecido"));
          }
        } catch (err) {
          alert("Falha ao comunicar com o servidor para converter DOCX.");
          console.error(err);
        } finally {
          if (formatStatus) {
            formatStatus.classList.remove("syncing");
            formatStatus.textContent = "⚡ Atualização em tempo real ativa";
          }
        }
      };
      reader.readAsDataURL(file);
      return;
    }

    if (file.name.toLowerCase().endsWith(".pdf")) {
      const reader = new FileReader();
      reader.onload = async (event) => {
        try {
          if (formatStatus) {
            formatStatus.classList.add("syncing");
            formatStatus.textContent = "⏳ Importando e analisando documento PDF...";
          }
          const res = await fetch("/api/parse-pdf", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_base64: event.target.result })
          });
          const result = await res.json();
          if (result.success) {
            if (result.title) titleOverride.value = result.title;
            if (result.orgao) deptOverride.value = result.orgao;
            if (result.autor) authorOverride.value = result.autor;
            if (result.logo) {
              currentLogoBase64 = result.logo;
              logoThumb.src = currentLogoBase64;
              logoFileName.textContent = "brasao_pdf.png";
              logoPreviewContainer.style.display = "flex";
            }
            rawInput.value = result.markdown || "";
            updateCounters();
            saveDraft();
            formatReport(false);
          } else {
            alert("Erro ao ler PDF: " + (result.error || "Formato desconhecido"));
          }
        } catch (err) {
          alert("Falha ao comunicar com o servidor para converter PDF.");
          console.error(err);
        } finally {
          if (formatStatus) {
            formatStatus.classList.remove("syncing");
            formatStatus.textContent = "⚡ Atualização em tempo real ativa";
          }
        }
      };
      reader.readAsDataURL(file);
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      rawInput.value = event.target.result;
      updateCounters();
      saveDraft();
      formatReport();
    };
    reader.readAsText(file);
  }

  // 5. Atalho de Teclado Global: Ctrl + Enter
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      formatReport();
    }
  });

  // Ação de Formatar Relatório
  btnGenerate.addEventListener("click", () => formatReport(true));

  async function formatReport(showButtonFeedback = true) {
    const text = rawInput.value.trim();
    if (!text) {
      if (showButtonFeedback) alert("Por favor, cole algum texto ou importe um arquivo primeiro.");
      return;
    }

    if (showButtonFeedback) {
      btnGenerate.disabled = true;
      btnGenerate.innerHTML = "<span>⏳ Formatando...</span>";
    }

    try {
      const response = await fetch("/api/format", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({
          text: text,
          title: titleOverride.value.trim(),
          author: authorOverride.value.trim(),
          orgao: deptOverride.value.trim(),
          logo: currentLogoBase64,
          include_signature: selectSignature.value === "sim",
          orientation: selectOrientation.value,
          include_meta_box: checkMetaBox.checked,
          include_subtitle: checkSubtitle ? checkSubtitle.checked : true,
          show_descricao_geral: checkDescricaoGeral ? checkDescricaoGeral.checked : false
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMsg = `Erro ${response.status}`;
        try {
          const errJson = JSON.parse(errorText);
          if (errJson.error) errorMsg = errJson.error;
        } catch (_) {
          if (errorText) errorMsg = errorText;
        }
        throw new Error(errorMsg);
      }

      const res = await response.json();

      if (res.success) {
        lastHtmlContent = res.html;
        previewFrame.srcdoc = res.html;
        emptyState.style.display = "none";
        btnPrint.disabled = false;
        
        currentReportUrl = `/outputs/${res.filename}`;
        btnOpenNewTab.href = currentReportUrl;
        btnOpenNewTab.style.display = "inline-flex";

        if (res.filename_docx && btnDownloadDocx) {
          btnDownloadDocx.href = `/outputs/${res.filename_docx}`;
          btnDownloadDocx.download = res.filename_docx;
          btnDownloadDocx.style.display = "inline-flex";
        }

        if (btnCopyHtml) {
          btnCopyHtml.style.display = "inline-flex";
        }

        // Exibe barra de metadados
        metaBar.style.display = "flex";
        document.getElementById("tagOrgao").textContent = `Órgão: ${res.data.orgao}`;
        document.getElementById("tagAutor").textContent = `Autor: ${res.data.autor}`;
        document.getElementById("tagData").textContent = `Data: ${res.data.data}`;
        document.getElementById("tagSecoes").textContent = `Seções: ${res.data.total_secoes}`;
      } else {
        if (showButtonFeedback) alert("Erro ao formatar relatório: " + (res.error || "Erro desconhecido"));
      }
    } catch (err) {
      console.error("Falha ao formatar:", err);
      if (showButtonFeedback) alert("Falha na comunicação com o servidor:\n" + (err.message || err));
    } finally {
      if (showButtonFeedback) {
        btnGenerate.disabled = false;
        btnGenerate.innerHTML = "<span>⚡ Formatar Relatório</span>";
      }
    }
  }

  function jsonBody(obj) {
    return JSON.stringify(obj);
  }

  // 6. Copiar Código HTML para Área de Transferência
  if (btnCopyHtml) {
    btnCopyHtml.addEventListener("click", async () => {
      if (!lastHtmlContent) return;
      try {
        await navigator.clipboard.writeText(lastHtmlContent);
        const originalText = btnCopyHtml.innerHTML;
        btnCopyHtml.innerHTML = "✅ Copiado!";
        setTimeout(() => {
          btnCopyHtml.innerHTML = originalText;
        }, 2000);
      } catch (err) {
        console.error("Erro ao copiar:", err);
      }
    });
  }

  // Imprimir via frame
  btnPrint.addEventListener("click", () => {
    if (previewFrame.contentWindow) {
      previewFrame.contentWindow.focus();
      previewFrame.contentWindow.print();
    }
  });

  // Inicializa carregando rascunho se existir
  loadDraft();
});

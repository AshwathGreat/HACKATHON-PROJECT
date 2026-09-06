/**
 * KisanGo - Frontend Controller
 * Handles WhatsApp simulation, image upload, AI Inspector updates, and presets.
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatStream = document.getElementById("chat-stream");
  const userInput = document.getElementById("user-input");
  const btnSend = document.getElementById("btn-send");
  const btnAttach = document.getElementById("btn-attach");
  const btnCamera = document.getElementById("btn-camera");
  const fileInput = document.getElementById("file-input");
  const typingIndicator = document.getElementById("typing-indicator");
  const imagePreviewPill = document.getElementById("image-preview-pill");
  const previewFileName = document.getElementById("preview-file-name");
  const btnRemoveFile = document.getElementById("btn-remove-file");
  const dragDropZone = document.getElementById("drag-drop-zone");
  const langSelect = document.getElementById("lang-select");
  const btnClearChat = document.getElementById("btn-clear-chat");
  const btnToggleInspector = document.getElementById("btn-toggle-inspector");
  const btnCloseInspector = document.getElementById("btn-close-inspector");
  const inspectorDrawer = document.getElementById("inspector-drawer");

  // Inspector Elements
  const inspectCondition = document.getElementById("inspect-condition");
  const inspectConfidence = document.getElementById("inspect-confidence");
  const inspectSeverity = document.getElementById("inspect-severity");
  const inspectSymptoms = document.getElementById("inspect-symptoms");
  const inspectOrganic = document.getElementById("inspect-organic");
  const inspectChemical = document.getElementById("inspect-chemical");
  const inspectJson = document.getElementById("inspect-json");

  // State
  let currentFile = null;
  let currentFileUrl = null;
  const sessionId = "farmer-" + Math.floor(Math.random() * 10000);

  // 1. Send Message Flow
  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text && !currentFile) return;

    const timeStr = getCurrentTime();

    // If an image is selected, send image diagnosis
    if (currentFile) {
      // Append user bubble with media preview
      appendUserBubble(text, currentFileUrl, timeStr);

      const fileToSend = currentFile;
      const captionToSend = text;
      clearInput();

      showTyping(true);

      try {
        const formData = new FormData();
        formData.append("file", fileToSend);
        formData.append("session_id", sessionId);
        formData.append("caption", captionToSend);
        formData.append("language", langSelect.value);

        const response = await fetch("/api/diagnose", {
          method: "POST",
          body: formData
        });

        const data = await response.json();
        showTyping(false);

        if (data.success && data.diagnosis) {
          appendBotBubble(data.diagnosis.farmer_friendly_summary, getCurrentTime());
          updateInspector(data.diagnosis);
        } else {
          appendBotBubble("⚠️ Unable to diagnose image. Please try again with a clearer photo.", getCurrentTime());
        }
      } catch (err) {
        console.error("Diagnosis error:", err);
        showTyping(false);
        appendBotBubble("⚠️ Server connection error. Make sure the backend is running!", getCurrentTime());
      }
    } else {
      // Text-only follow up question
      appendUserBubble(text, null, timeStr);
      clearInput();
      showTyping(true);

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            message: text,
            language: langSelect.value
          })
        });

        const data = await response.json();
        showTyping(false);

        if (data.reply) {
          appendBotBubble(data.reply, getCurrentTime());
        }
      } catch (err) {
        console.error("Chat error:", err);
        showTyping(false);
        appendBotBubble("⚠️ Failed to send message. Check server status.", getCurrentTime());
      }
    }
  }

  // 2. UI Helpers: Add Bubbles
  function appendUserBubble(text, imgUrl, timeStr) {
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble user-bubble";

    let contentHtml = "";
    if (imgUrl) {
      contentHtml += `<div class="bubble-media-preview"><img src="${imgUrl}" alt="Crop Photo"></div>`;
    }
    if (text) {
      contentHtml += `<div class="bubble-content">${escapeHtml(text)}</div>`;
    }
    contentHtml += `<span class="bubble-time">${timeStr}</span>`;

    bubble.innerHTML = contentHtml;
    chatStream.appendChild(bubble);
    scrollToBottom();
  }

  function appendBotBubble(text, timeStr) {
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble bot-bubble";

    const formattedText = formatWhatsAppMarkdown(text);
    bubble.innerHTML = `
      <div class="bubble-content">${formattedText}</div>
      <span class="bubble-time">${timeStr}</span>
    `;

    chatStream.appendChild(bubble);
    scrollToBottom();
  }

  function showTyping(isTyping) {
    typingIndicator.style.display = isTyping ? "flex" : "none";
    if (isTyping) scrollToBottom();
  }

  function scrollToBottom() {
    chatStream.scrollTop = chatStream.scrollHeight;
  }

  function getCurrentTime() {
    const now = new Date();
    let hours = now.getHours();
    const minutes = now.getMinutes().toString().padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;
    return `${hours}:${minutes} ${ampm}`;
  }

  function clearInput() {
    userInput.value = "";
    currentFile = null;
    currentFileUrl = null;
    imagePreviewPill.style.display = "none";
    fileInput.value = "";
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Format WhatsApp style markdown (*bold*, _italic_, ~strike~)
  function formatWhatsAppMarkdown(text) {
    let html = escapeHtml(text);
    // Bold: *text*
    html = html.replace(/\*([^\*]+)\*/g, "<strong>$1</strong>");
    // Italic: _text_
    html = html.replace(/_([^_]+)_/g, "<em>$1</em>");
    // Newlines to <br>
    html = html.replace(/\n/g, "<br>");
    return html;
  }

  // 3. File Input & Drag and Drop
  btnAttach.addEventListener("click", () => fileInput.click());
  btnCamera.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectedFile(e.target.files[0]);
    }
  });

  btnRemoveFile.addEventListener("click", () => {
    currentFile = null;
    currentFileUrl = null;
    imagePreviewPill.style.display = "none";
    fileInput.value = "";
  });

  function handleSelectedFile(file) {
    currentFile = file;
    currentFileUrl = URL.createObjectURL(file);
    previewFileName.textContent = file.name.length > 18 ? file.name.slice(0, 15) + "..." : file.name;
    imagePreviewPill.style.display = "inline-flex";
    userInput.focus();
  }

  // Drag and Drop
  ["dragenter", "dragover"].forEach(eventName => {
    chatStream.addEventListener(eventName, (e) => {
      e.preventDefault();
      dragDropZone.classList.add("active");
    });
  });

  ["dragleave", "drop"].forEach(eventName => {
    dragDropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dragDropZone.classList.remove("active");
    });
  });

  dragDropZone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectedFile(e.dataTransfer.files[0]);
    }
  });

  // Keyboard Enter
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  btnSend.addEventListener("click", sendMessage);

  // Clear Chat
  btnClearChat.addEventListener("click", () => {
    chatStream.innerHTML = `
      <div class="chat-bubble bot-bubble">
        <div class="bubble-content">
          🌾 <strong>KisanGo Session Reset.</strong><br>
          Send a new crop leaf or plant photo to diagnose diseases! 📸
        </div>
        <span class="bubble-time">${getCurrentTime()}</span>
      </div>
    `;
    resetInspector();
  });

  // 4. AI Inspector Updates
  function updateInspector(diag) {
    inspectCondition.textContent = diag.condition_name || "Unknown";
    inspectConfidence.textContent = Math.round((diag.confidence_score || 0.9) * 100) + "%";
    inspectSeverity.textContent = diag.severity || "N/A";

    // Symptoms
    inspectSymptoms.innerHTML = "";
    if (diag.symptoms_detected && diag.symptoms_detected.length > 0) {
      diag.symptoms_detected.forEach(s => {
        const li = document.createElement("li");
        li.textContent = s;
        inspectSymptoms.appendChild(li);
      });
    } else {
      inspectSymptoms.innerHTML = "<li>No specific symptoms noted</li>";
    }

    // Treatments
    inspectOrganic.innerHTML = "";
    if (diag.treatment && diag.treatment.organic && diag.treatment.organic.length > 0) {
      diag.treatment.organic.forEach(o => {
        const li = document.createElement("li");
        li.textContent = o;
        inspectOrganic.appendChild(li);
      });
    } else {
      inspectOrganic.innerHTML = "<li>None</li>";
    }

    inspectChemical.innerHTML = "";
    if (diag.treatment && diag.treatment.chemical && diag.treatment.chemical.length > 0) {
      diag.treatment.chemical.forEach(c => {
        const li = document.createElement("li");
        li.textContent = c;
        inspectChemical.appendChild(li);
      });
    } else {
      inspectChemical.innerHTML = "<li>None</li>";
    }

    // Raw JSON
    inspectJson.textContent = JSON.stringify(diag, null, 2);
  }

  function resetInspector() {
    inspectCondition.textContent = "Awaiting Photo";
    inspectConfidence.textContent = "--%";
    inspectSeverity.textContent = "--";
    inspectSymptoms.innerHTML = "<li>No photo analyzed yet</li>";
    inspectOrganic.innerHTML = "<li>Awaiting diagnosis</li>";
    inspectChemical.innerHTML = "<li>Awaiting diagnosis</li>";
    inspectJson.textContent = '{ "status": "idle" }';
  }

  // Toggle Inspector Drawer
  btnToggleInspector.addEventListener("click", () => {
    inspectorDrawer.classList.toggle("collapsed");
  });
  btnCloseInspector.addEventListener("click", () => {
    inspectorDrawer.classList.add("collapsed");
  });

  // 5. Preset Sample Buttons for Quick Demo
  document.querySelectorAll(".sample-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const preset = btn.getAttribute("data-preset");
      await triggerPresetDemo(preset);
    });
  });

  async function triggerPresetDemo(presetKey) {
    showTyping(true);

    // Generate synthetic crop leaf canvas preview
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 300;
    const ctx = canvas.getContext("2d");

    let promptCaption = "";
    let mockData = null;

    if (presetKey === "early_blight") {
      drawLeafCanvas(ctx, "#3b7a35", "#6b3e18", "Tomato Early Blight");
      promptCaption = "My tomato leaves have brown concentric spots";
      mockData = {
        is_crop: true,
        crop_name: "Tomato",
        is_healthy: false,
        condition_name: "Early Blight",
        scientific_name: "Alternaria solani",
        severity: "Moderate",
        confidence_score: 0.95,
        symptoms_detected: ["Concentric brown target-like rings", "Yellow chlorotic halo around lesions", "Lower foliage necrosis"],
        causes: ["Alternaria solani fungal spores", "High humidity & warm temperatures"],
        treatment: {
          organic: ["Spray Neem Oil (5ml/L) with mild surfactant every 7 days", "Soil drench with Trichoderma viride bio-fungicide"],
          chemical: ["Spray Mancozeb 75% WP @ 2.5g/L water", "Chlorothalonil @ 2g/L as protective spray"],
          cultural: ["Prune and bury affected lower leaves", "Switch to drip irrigation to prevent leaf splash"]
        },
        preventive_measures: ["Maintain 2-3 year crop rotation without nightshade crops", "Mulch bed to stop soil bounce"]
      };
    } else if (presetKey === "late_blight") {
      drawLeafCanvas(ctx, "#2e5a27", "#1f2937", "Potato Late Blight");
      promptCaption = "Potato leaves turned water-soaked and dark brown";
      mockData = {
        is_crop: true,
        crop_name: "Potato",
        is_healthy: false,
        condition_name: "Late Blight",
        scientific_name: "Phytophthora infestans",
        severity: "Severe",
        confidence_score: 0.96,
        symptoms_detected: ["Water-soaked dark lesions on leaf tips", "White fungal downy mold on underside in morning", "Rapid blight of stems"],
        causes: ["Phytophthora infestans oomycete", "Cool wet weather (15-20°C with rain/dew)"],
        treatment: {
          organic: ["Copper hydroxide / Bordeaux mixture spray", "Bio-fungicide Bacillus subtilis"],
          chemical: ["Metalaxyl + Mancozeb (Ridomil MZ) @ 2.5g/L", "Cymoxanil 8% + Mancozeb 64% WP"],
          cultural: ["Hill up potatoes to protect tubers", "Immediately destroy severely blighted plants"]
        },
        preventive_measures: ["Use certified disease-free seed tubers", "Ensure wide plant spacing for aeration"]
      };
    } else if (presetKey === "rice_blast") {
      drawLeafCanvas(ctx, "#4d7c0f", "#854d0e", "Rice Blast Disease");
      promptCaption = "Spindle shaped lesions on paddy leaves";
      mockData = {
        is_crop: true,
        crop_name: "Rice / Paddy",
        is_healthy: false,
        condition_name: "Rice Blast",
        scientific_name: "Magnaporthe oryzae",
        severity: "Moderate",
        confidence_score: 0.92,
        symptoms_detected: ["Spindle/diamond-shaped lesions with gray center and brown margin", "Lesions coalescing to dry entire leaf"],
        causes: ["Magnaporthe oryzae fungus", "Excessive nitrogen fertilizer application", "High cloudiness & relative humidity"],
        treatment: {
          organic: ["Pseudomonas fluorescens (0.2%) foliar spray", "Neem seed kernel extract (NSKE 5%)"],
          chemical: ["Tricyclazole 75% WP @ 0.6g/L water", "Isoprothiolane 40% EC @ 1.5ml/L"],
          cultural: ["Split nitrogen fertilizer application into 3-4 doses", "Avoid field drying/water stress"]
        },
        preventive_measures: ["Treat seeds with Carbendazim before sowing", "Plant blast-resistant paddy varieties"]
      };
    } else if (presetKey === "healthy_corn") {
      drawLeafCanvas(ctx, "#15803d", null, "Healthy Corn Plant");
      promptCaption = "Is my maize crop healthy?";
      mockData = {
        is_crop: true,
        crop_name: "Maize / Corn",
        is_healthy: true,
        condition_name: "Healthy Plant",
        scientific_name: "Zea mays",
        severity: "Healthy",
        confidence_score: 0.98,
        symptoms_detected: ["Vibrant deep green foliage", "Sturdy stem vascular structure", "No fungal sporulation or insect bores"],
        causes: ["Optimal nutrient balance and irrigation"],
        treatment: {
          organic: ["Apply well-decomposed farmyard manure at knee-high stage"],
          chemical: ["Follow recommended NPK 120:60:40 schedule"],
          cultural: ["Regular weeding during first 30 days"]
        },
        preventive_measures: ["Monitor regularly for Fall Armyworm egg clusters", "Ensure proper drainage during heavy rain"]
      };
    } else {
      // Non crop
      drawNonCropCanvas(ctx);
      promptCaption = "Can you diagnose this?";
      mockData = {
        is_crop: false,
        crop_name: "Non-plant object",
        is_healthy: false,
        condition_name: "Invalid Image",
        scientific_name: null,
        severity: "N/A",
        confidence_score: 0.99,
        symptoms_detected: ["No agricultural crop, plant, leaf, or fruit detected"],
        causes: ["Unrelated non-agricultural photo"],
        treatment: { organic: [], chemical: [], cultural: [] },
        preventive_measures: []
      };
    }

    // Convert canvas to blob
    canvas.toBlob(async (blob) => {
      const dataUrl = canvas.toDataURL("image/jpeg");
      appendUserBubble(promptCaption, dataUrl, getCurrentTime());

      // If backend is active and has Gemini key, send the actual blob
      try {
        const formData = new FormData();
        formData.append("file", blob, `${presetKey}.jpg`);
        formData.append("session_id", sessionId);
        formData.append("caption", promptCaption);
        formData.append("language", langSelect.value);

        const resp = await fetch("/api/diagnose", { method: "POST", body: formData });
        const resData = await resp.json();
        showTyping(false);

        if (resData.success && resData.diagnosis) {
          appendBotBubble(resData.diagnosis.farmer_friendly_summary, getCurrentTime());
          updateInspector(resData.diagnosis);
          return;
        }
      } catch (e) {
        console.warn("Falling back to local preset formatter:", e);
      }

      // Fallback mock representation
      showTyping(false);
      const formatted = generateSummaryFromMock(mockData, langSelect.value);
      mockData.farmer_friendly_summary = formatted;
      appendBotBubble(formatted, getCurrentTime());
      updateInspector(mockData);
    }, "image/jpeg");
  }

  function drawLeafCanvas(ctx, bgGreen, spotColor, title) {
    // Gradient Leaf background
    const grad = ctx.createLinearGradient(0, 0, 400, 300);
    grad.addColorStop(0, bgGreen);
    grad.addColorStop(1, "#14532d");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 400, 300);

    // Draw leaf veins
    ctx.strokeStyle = "rgba(255,255,255,0.2)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(200, 20);
    ctx.lineTo(200, 280);
    ctx.stroke();

    for (let y = 60; y < 260; y += 40) {
      ctx.beginPath();
      ctx.moveTo(200, y);
      ctx.lineTo(100, y - 20);
      ctx.moveTo(200, y);
      ctx.lineTo(300, y - 20);
      ctx.stroke();
    }

    // Draw disease spots if present
    if (spotColor) {
      for (let i = 0; i < 6; i++) {
        const x = 120 + (i * 35) % 180;
        const y = 80 + (i * 45) % 150;
        ctx.fillStyle = spotColor;
        ctx.beginPath();
        ctx.arc(x, y, 14 + (i % 3) * 4, 0, Math.PI * 2);
        ctx.fill();

        // Target concentric rings
        ctx.strokeStyle = "#eab308";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }

    // Label banner
    ctx.fillStyle = "rgba(0,0,0,0.7)";
    ctx.fillRect(0, 250, 400, 50);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 16px 'Plus Jakarta Sans', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`Sample: ${title}`, 200, 280);
  }

  function drawNonCropCanvas(ctx) {
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(0, 0, 400, 300);
    ctx.font = "48px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("🚗 🏢 📱", 200, 140);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "bold 16px 'Plus Jakarta Sans', sans-serif";
    ctx.fillText("Non-Agricultural Test Image", 200, 200);
  }

  function generateSummaryFromMock(m, lang) {
    if (!m.is_crop) {
      return (
        "⚠️ *No Plant or Crop Detected*\n" +
        "The photo does not appear to be an agricultural crop or plant leaf. Please send a clear close-up of the affected crop leaf, fruit, or stem! 📸🌾"
      );
    }
    if (m.is_healthy) {
      return (
        `🌿 *KisanGo Crop Health Report* 🌿\n` +
        `━━━━━━━━━━━━━━━━━━━━\n` +
        `🌱 *Crop:* ${m.crop_name}\n` +
        `🩺 *Status:* ✅ *Healthy Crop*\n` +
        `🎯 *Confidence:* ${Math.round(m.confidence_score * 100)}%\n\n` +
        `✨ *Observations:*\n` +
        m.symptoms_detected.map(s => `• ${s}`).join("\n") +
        `\n\n🛡️ *Maintenance Advice:*\n` +
        `• Maintain optimal watering schedule.\n` +
        `• Keep monitoring weekly for any pest invasion!\n` +
        `━━━━━━━━━━━━━━━━━━━━\n` +
        `💬 *Have questions?* Ask anytime!`
      );
    }

    const orgList = m.treatment.organic.map(o => `• ${o}`).join("\n");
    const chemList = m.treatment.chemical.map(c => `• ${c}`).join("\n");
    const prevList = m.preventive_measures.map(p => `• ${p}`).join("\n");

    return (
      `🌿 *KisanGo Crop Health Report* 🌿\n` +
      `━━━━━━━━━━━━━━━━━━━━\n` +
      `🌱 *Crop Identified:* ${m.crop_name}\n` +
      `🩺 *Diagnosis:* ${m.condition_name} (_${m.scientific_name || ""}_)\n` +
      `⚠️ *Severity:* ${m.severity}\n` +
      `🎯 *Confidence:* ${Math.round(m.confidence_score * 100)}%\n\n` +
      `🔍 *Observed Symptoms:*\n` +
      m.symptoms_detected.map(s => `• ${s}`).join("\n") +
      `\n\n💊 *Immediate Treatment Plan:*\n` +
      `🌿 *Organic / Bio Control:*\n` + orgList + `\n\n` +
      `🧪 *Chemical Control (Dosage):*\n` + chemList + `\n\n` +
      `🛡️ *Preventive Measures:*\n` + prevList + `\n` +
      `━━━━━━━━━━━━━━━━━━━━\n` +
      `💬 *Have questions?* Reply with your question!`
    );
  }

  // 6. Navigation Modals
  document.getElementById("tab-architecture").addEventListener("click", () => {
    document.getElementById("modal-architecture").style.display = "flex";
  });
  document.getElementById("tab-pitch").addEventListener("click", () => {
    document.getElementById("modal-pitch").style.display = "flex";
  });

  document.querySelectorAll(".modal-close, [data-close]").forEach(el => {
    el.addEventListener("click", () => {
      document.querySelectorAll(".modal").forEach(m => m.style.display = "none");
    });
  });
});

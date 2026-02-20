/**
 * YouTube Auto Dub — Frontend Application Logic
 *
 * Handles: theme toggle, language toggle (EN/AR), language loading,
 * form submission, SSE progress streaming, toast notifications.
 */

(function () {
    "use strict";

    // ── DOM refs ────────────────────────────────────────────────
    const $ = (s) => document.querySelector(s);
    const $$ = (s) => document.querySelectorAll(s);

    const form = $("#dub-form");
    const urlInput = $("#video-url");
    const langSelect = $("#target-lang");
    const genderSel = $("#voice-gender");
    const subCheck = $("#subtitle-check");
    const submitBtn = $("#submit-btn");
    const btnLabel = $(".btn-label");
    const btnLoader = $(".btn-loader");

    const progressSec = $("#progress-section");
    const progressBar = $("#progress-bar");
    const progressPct = $("#progress-pct");
    const logBox = $("#log-box");

    const resultSec = $("#result-section");
    const resultMeta = $("#result-meta");
    const downloadLink = $("#download-link");

    const toast = $("#toast");
    const themeToggle = $("#theme-toggle");

    const STEP_ORDER = ["init", "download", "transcribe", "translate", "synthesize", "render"];

    // ── i18n Translations ────────────────────────────────────────
    const TRANSLATIONS = {
        en: {
            langToggle: "عربي",
            heroBadge: "AI-Powered",
            heroTitle: 'Dub Any YouTube Video<br/><span class="gradient-text">Into Any Language</span>',
            heroSubtitle: "Automatically transcribe, translate, and re-voice YouTube videos using state-of-the-art AI. Just paste a link and choose your language.",
            labelUrl: "YouTube URL",
            labelLang: "Target Language",
            loadingLangs: "Loading languages…",
            labelGender: "Voice Gender",
            female: "Female",
            male: "Male",
            subtitleToggle: "Burn subtitles into the video",
            startBtn: "Start Dubbing",
            processing: "Processing…",
            progressTitle: "Pipeline Progress",
            stepInit: "Init",
            stepDownload: "Download",
            stepTranscribe: "Transcribe",
            stepTranslate: "Translate",
            stepSynthesize: "Synthesize",
            stepRender: "Render",
            resultTitle: "Dubbing Complete!",
            downloadBtn: "Download Video",
            footer: "&copy; 2026 YouTube Auto Dub &middot; Built with FastAPI &amp; Whisper",
            toastNoUrl: "Please enter a YouTube URL.",
            toastComplete: "Dubbing complete! 🎉",
            toastDisconnect: "Lost connection to server.",
            toastLangFail: "Could not load languages — using default (Spanish).",
            tabDub: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg> Dubbing',
            tabDownload: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Download Only',
            dlLabelUrl: "YouTube URL",
            fetchBtn: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Search',
            fetchingInfo: "Searching…",
            dlVideo: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/><line x1="17" y1="17" x2="22" y2="17"/></svg> Video',
            dlAudio: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg> Audio Only',
            dlQuality: "Quality",
            dlStartBtn: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Download',
            dlDownloading: "Downloading…",
            dlComplete: "Download ready!",
            dlSaveFile: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> Save File',
        },
        ar: {
            langToggle: "EN",
            heroBadge: "بتقنية الذكاء الاصطناعي",
            heroTitle: 'حوّل أي فيديو يوتيوب<br/><span class="gradient-text">لأي لغة في العالم</span>',
            heroSubtitle: "",
            labelUrl: "لينك الفيديو",
            labelLang: "اللغة المطلوبة",
            loadingLangs: "جاري تحميل اللغات…",
            labelGender: "نوع الصوت",
            female: "صوت أنثوي",
            male: "صوت ذكوري",
            subtitleToggle: "إضافة ترجمة مكتوبة على الفيديو",
            startBtn: "ابدأ الدبلجة",
            processing: "جاري التنفيذ…",
            progressTitle: "مراحل التنفيذ",
            stepInit: "تجهيز",
            stepDownload: "تحميل",
            stepTranscribe: "تفريغ",
            stepTranslate: "ترجمة",
            stepSynthesize: "توليد صوت",
            stepRender: "إنتاج",
            resultTitle: "تمّ بنجاح! 🎬",
            downloadBtn: "حمّل الفيديو",
            footer: "&copy; 2026 YouTube Auto Dub &middot; مبني بـ FastAPI و Whisper",
            toastNoUrl: "من فضلك حط لينك فيديو يوتيوب الأول.",
            toastComplete: "الدبلجة خلصت بنجاح! 🎉",
            toastDisconnect: "الاتصال بالسيرفر اتقطع، حاول تاني.",
            toastLangFail: "مقدرناش نحمّل اللغات — هنستخدم الإسبانية كبداية.",
            tabDub: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg> دبلجة',
            tabDownload: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> تحميل فقط',
            dlLabelUrl: "رابط الفيديو",
            fetchBtn: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> بحث',
            fetchingInfo: "جاري البحث…",
            dlVideo: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/><line x1="17" y1="17" x2="22" y2="17"/></svg> فيديو',
            dlAudio: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg> صوت فقط',
            dlQuality: "الجودة",
            dlStartBtn: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> تحميل',
            dlDownloading: "جاري التحميل…",
            dlComplete: "التحميل جاهز!",
            dlSaveFile: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg> حفظ الملف',
        },
    };

    let currentLang = localStorage.getItem("autodub-lang") || "en";

    function applyTranslations(lang) {
        const strings = TRANSLATIONS[lang] || TRANSLATIONS.en;
        document.querySelectorAll("[data-i18n]").forEach((el) => {
            const key = el.getAttribute("data-i18n");
            if (strings[key] != null) el.innerHTML = strings[key];
        });
    }

    function setUILang(lang) {
        currentLang = lang;
        const html = document.documentElement;
        html.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
        html.setAttribute("lang", lang);
        localStorage.setItem("autodub-lang", lang);
        applyTranslations(lang);
    }

    function tr(key) {
        return (TRANSLATIONS[currentLang] || TRANSLATIONS.en)[key] || key;
    }

    // ── Language Switcher ─────────────────────────────────────────
    const langToggle = $("#lang-toggle");
    langToggle.addEventListener("click", () => {
        setUILang(currentLang === "en" ? "ar" : "en");
    });

    // ── Theme ───────────────────────────────────────────────────
    function initTheme() {
        const saved = localStorage.getItem("autodub-theme") || "dark";
        document.documentElement.setAttribute("data-theme", saved);
    }

    themeToggle.addEventListener("click", () => {
        const html = document.documentElement;
        const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
        html.setAttribute("data-theme", next);
        localStorage.setItem("autodub-theme", next);
    });

    initTheme();
    setUILang(currentLang);

    // ── Toast ───────────────────────────────────────────────────
    let toastTimer = null;
    function showToast(msg, type = "error", duration = 5000) {
        toast.textContent = msg;
        toast.className = "toast" + (type === "success" ? " success" : "");
        toast.hidden = false;
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => { toast.hidden = true; }, duration);
    }

    // ── Load Languages ──────────────────────────────────────────
    async function loadLanguages() {
        try {
            const res = await fetch("/api/languages");
            const data = await res.json();
            langSelect.innerHTML = "";

            // Build a name map for common languages
            const nameMap = {
                en: "English", es: "Spanish", fr: "French", de: "German", it: "Italian",
                pt: "Portuguese", ru: "Russian", ja: "Japanese", ko: "Korean", zh: "Chinese",
                ar: "Arabic", hi: "Hindi", tr: "Turkish", nl: "Dutch", pl: "Polish",
                sv: "Swedish", da: "Danish", fi: "Finnish", nb: "Norwegian", cs: "Czech",
                el: "Greek", he: "Hebrew", hu: "Hungarian", id: "Indonesian", ms: "Malay",
                ro: "Romanian", sk: "Slovak", th: "Thai", uk: "Ukrainian", vi: "Vietnamese",
                bg: "Bulgarian", hr: "Croatian", lt: "Lithuanian", lv: "Latvian",
                sr: "Serbian", sl: "Slovenian", et: "Estonian", fil: "Filipino",
                bn: "Bengali", gu: "Gujarati", kn: "Kannada", ml: "Malayalam",
                mr: "Marathi", ta: "Tamil", te: "Telugu", ur: "Urdu", ne: "Nepali",
                si: "Sinhala", km: "Khmer", lo: "Lao", my: "Myanmar", ka: "Georgian",
                az: "Azerbaijani", kk: "Kazakh", mn: "Mongolian", ps: "Pashto",
                fa: "Persian", af: "Afrikaans", sq: "Albanian", am: "Amharic",
                bs: "Bosnian", ca: "Catalan", gl: "Galician", ga: "Irish",
                is: "Icelandic", jv: "Javanese", mk: "Macedonian", mt: "Maltese",
                so: "Somali", sw: "Swahili", cy: "Welsh", zu: "Zulu",
            };

            const options = data.languages.map((l) => {
                const label = nameMap[l.code] || l.name || l.code;
                return { code: l.code, label: `${label} (${l.code})` };
            });

            options.sort((a, b) => a.label.localeCompare(b.label));

            for (const opt of options) {
                const el = document.createElement("option");
                el.value = opt.code;
                el.textContent = opt.label;
                if (opt.code === "es") el.selected = true;
                langSelect.appendChild(el);
            }
        } catch (e) {
            console.error("Failed to load languages", e);
            langSelect.innerHTML = '<option value="es">Spanish (es)</option>';
            showToast(tr("toastLangFail"), "error");
        }
    }

    loadLanguages();

    // ── Form Submit ─────────────────────────────────────────────
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const url = urlInput.value.trim();
        const lang = langSelect.value;
        const gender = genderSel.value;
        const sub = subCheck.checked;

        if (!url) { showToast(tr("toastNoUrl")); return; }

        // Lock UI
        submitBtn.disabled = true;
        btnLabel.hidden = true;
        btnLoader.hidden = false;
        resultSec.hidden = true;

        // Reset progress UI
        resetProgress();
        progressSec.hidden = false;
        progressSec.scrollIntoView({ behavior: "smooth", block: "start" });

        try {
            const res = await fetch("/api/dub", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url, lang, gender, subtitle: sub }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Server error ${res.status}`);
            }
            const { job_id } = await res.json();
            connectSSE(job_id);
        } catch (err) {
            showToast(err.message);
            unlockForm();
        }
    });

    // ── SSE Progress ────────────────────────────────────────────
    function connectSSE(jobId) {
        const evtSource = new EventSource(`/api/progress/${jobId}`);

        evtSource.onmessage = (e) => {
            try {
                const ev = JSON.parse(e.data);
                handleProgressEvent(ev, jobId);
                if (ev.status === "complete" || ev.status === "error") {
                    evtSource.close();
                    unlockForm();
                }
            } catch (err) {
                console.error("SSE parse error", err);
            }
        };

        evtSource.onerror = () => {
            evtSource.close();
            showToast(tr("toastDisconnect"));
            unlockForm();
        };
    }

    function handleProgressEvent(ev, jobId) {
        const { step, progress, message, status } = ev;

        // Update progress bar
        if (progress >= 0) {
            progressBar.style.width = progress + "%";
            progressPct.textContent = progress + "%";
        }

        // Update step indicators
        const idx = STEP_ORDER.indexOf(step);
        if (idx >= 0) {
            STEP_ORDER.forEach((s, i) => {
                const el = $(`.step[data-step="${s}"]`);
                if (!el) return;
                el.classList.remove("active", "done");
                if (i < idx) el.classList.add("done");
                else if (i === idx) el.classList.add(status === "complete" ? "done" : "active");
            });
            // Lines
            $$(".step-line").forEach((line, i) => {
                line.classList.toggle("done", i < idx);
            });
        }

        // Append log
        if (message && step !== "heartbeat") {
            appendLog(message);
        }

        // Completion
        if (status === "complete") {
            markAllStepsDone();
            resultMeta.textContent = message;
            downloadLink.href = `/api/download/${jobId}`;
            resultSec.hidden = false;
            resultSec.scrollIntoView({ behavior: "smooth", block: "center" });
            showToast(tr("toastComplete"), "success");
        }

        // Error
        if (status === "error") {
            showToast(message || "An error occurred during processing.");
        }
    }

    // ── Helpers ─────────────────────────────────────────────────
    function appendLog(msg) {
        const div = document.createElement("div");
        div.className = "log-entry";
        const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
        div.textContent = `[${time}] ${msg}`;
        logBox.appendChild(div);
        logBox.scrollTop = logBox.scrollHeight;
    }

    function resetProgress() {
        progressBar.style.width = "0%";
        progressPct.textContent = "0%";
        logBox.innerHTML = "";
        $$(".step").forEach((el) => el.classList.remove("active", "done"));
        $$(".step-line").forEach((el) => el.classList.remove("done"));
    }

    function markAllStepsDone() {
        $$(".step").forEach((el) => { el.classList.remove("active"); el.classList.add("done"); });
        $$(".step-line").forEach((el) => el.classList.add("done"));
        progressBar.style.width = "100%";
        progressPct.textContent = "100%";
    }

    function unlockForm() {
        submitBtn.disabled = false;
        btnLabel.hidden = false;
        btnLoader.hidden = true;
    }

    // ── Mode Tabs (Dub / Download) ──────────────────────────────
    const modeTabs = $$(".mode-tab");
    const dubForm = $(".form-section");
    const downloadPanel = $("#download-panel");

    modeTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            modeTabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            const mode = tab.getAttribute("data-mode");
            if (mode === "download") {
                dubForm.hidden = true;
                progressSec.hidden = true;
                resultSec.hidden = true;
                downloadPanel.hidden = false;
            } else {
                dubForm.hidden = false;
                downloadPanel.hidden = true;
            }
        });
    });

    // ── Download-Only Feature ────────────────────────────────────
    const dlUrl = $("#dl-url");
    const fetchInfoBtn = $("#fetch-info-btn");
    const videoInfoCard = $("#video-info-card");
    const viThumb = $("#vi-thumb");
    const viTitle = $("#vi-title");
    const viChannel = $("#vi-channel");
    const viDuration = $("#vi-duration");
    const formatSection = $("#format-section");
    const formatSelect = $("#format-select");
    const dlStartBtn = $("#dl-start-btn");
    const dlBtnLabel = dlStartBtn.querySelector(".btn-label");
    const dlBtnLoader = dlStartBtn.querySelector(".btn-loader");
    const dlTypeBtns = $$(".dl-type-btn");

    let videoData = null;
    let dlMediaType = "video";

    // Format duration (seconds → mm:ss or hh:mm:ss)
    function fmtDuration(s) {
        if (!s) return "0:00";
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = Math.floor(s % 60);
        if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
        return `${m}:${String(sec).padStart(2, "0")}`;
    }

    // Type toggle (Video / Audio)
    dlTypeBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            dlTypeBtns.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
            dlMediaType = btn.getAttribute("data-type");
            populateFormats();
        });
    });

    function populateFormats() {
        if (!videoData) return;
        resetDlUI(); // Clear previous download state when formats change
        formatSelect.innerHTML = "";
        const list = dlMediaType === "audio" ? videoData.audio_formats : videoData.video_formats;
        if (!list || list.length === 0) {
            const o = document.createElement("option");
            o.textContent = dlMediaType === "audio" ? "No audio formats" : "No video formats";
            formatSelect.appendChild(o);
            return;
        }
        for (const f of list) {
            const o = document.createElement("option");
            o.value = f.format_id;
            const size = f.filesize_mb ? ` — ${f.filesize_mb} MB` : "";
            o.textContent = `${f.quality} (${f.ext})${size}`;
            formatSelect.appendChild(o);
        }
    }

    // Fetch Info
    fetchInfoBtn.addEventListener("click", async () => {
        const url = dlUrl.value.trim();
        if (!url) { showToast(tr("toastNoUrl")); return; }

        fetchInfoBtn.disabled = true;
        fetchInfoBtn.textContent = tr("fetchingInfo");

        try {
            const res = await fetch("/api/video-info", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Error ${res.status}`);
            }
            videoData = await res.json();

            // Show info card
            viThumb.src = videoData.thumbnail || "";
            viTitle.textContent = videoData.title;
            viChannel.textContent = videoData.channel;
            viDuration.textContent = fmtDuration(videoData.duration);
            videoInfoCard.hidden = false;

            // Show format selection
            populateFormats();
            formatSection.hidden = false;
            formatSection.scrollIntoView({ behavior: "smooth", block: "center" });

        } catch (err) {
            showToast(err.message);
        } finally {
            fetchInfoBtn.disabled = false;
            // Restore button text using i18n
            applyTranslations(currentLang);
        }
    });

    // ── Download progress elements ────────────────────────────────
    const dlProgress = $("#dl-progress");
    const dlProgressBar = $("#dl-progress-bar");
    const dlProgressPct = $("#dl-progress-pct");
    const dlProgressMsg = $("#dl-progress-msg");

    function resetDlUI() {
        dlProgress.hidden = true;
        dlProgressBar.style.width = "0%";
        dlProgressPct.textContent = "0%";
        dlProgressMsg.textContent = "";
        dlProgress.querySelectorAll(".dl-save-btn").forEach(el => el.remove());
    }

    formatSelect.addEventListener("change", resetDlUI);

    // Start download with progress tracking
    dlStartBtn.addEventListener("click", async () => {
        const url = dlUrl.value.trim();
        const formatId = formatSelect.value;
        if (!url || !formatId) return;

        resetDlUI(); // Ensure fresh state before starting new download


        // Lock button & show progress
        dlStartBtn.disabled = true;
        dlBtnLabel.hidden = true;
        dlBtnLoader.hidden = false;
        dlProgress.hidden = false;
        dlProgressBar.style.width = "0%";
        dlProgressPct.textContent = "0%";
        dlProgressMsg.textContent = tr("dlDownloading");

        try {
            const res = await fetch("/api/download-start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url, format_id: formatId, media_type: dlMediaType }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `Error ${res.status}`);
            }
            const { job_id } = await res.json();

            // Connect to SSE for live progress
            const evtSource = new EventSource(`/api/progress/${job_id}`);
            evtSource.onmessage = (e) => {
                try {
                    const ev = JSON.parse(e.data);

                    // Update progress bar
                    if (ev.progress >= 0 && ev.progress <= 100) {
                        dlProgressBar.style.width = ev.progress + "%";
                        dlProgressPct.textContent = ev.progress + "%";
                    }
                    if (ev.message) {
                        dlProgressMsg.textContent = ev.message;
                    }

                    if (ev.status === "complete") {
                        evtSource.close();
                        dlProgressMsg.textContent = ev.message || tr("dlComplete");

                        // Remove any previous save buttons
                        dlProgress.querySelectorAll(".dl-save-btn").forEach(el => el.remove());

                        // Show "Save File" link (styled as a button)
                        const saveBtn = document.createElement("button");
                        saveBtn.className = "btn-primary dl-save-btn";
                        saveBtn.style.cssText = "display:flex;align-items:center;justify-content:center;gap:.5rem;margin-top:.75rem;cursor:pointer;background:#22c55e;width:100%;color:white;font-weight:600;padding:.8rem;border:none;border-radius:14px";
                        saveBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> ${tr("dlSaveFile")}`;

                        saveBtn.onclick = async () => {
                            try {
                                const originalText = saveBtn.innerHTML;
                                saveBtn.disabled = true;
                                saveBtn.textContent = "⌛ Getting file...";

                                const res = await fetch(`/api/download/${job_id}`);
                                if (!res.ok) throw new Error("Download failed");

                                // Build filename from video title + correct extension
                                const ext = dlMediaType === "audio" ? ".mp3" : ".mp4";
                                const title = (videoData && videoData.title) ? videoData.title.replace(/[\\/:*?"<>|]/g, "_") : "download";
                                const saveName = title + ext;

                                const blob = await res.blob();
                                const url = window.URL.createObjectURL(blob);
                                const a = document.createElement("a");
                                a.href = url;
                                a.download = saveName;
                                document.body.appendChild(a);
                                a.click();

                                setTimeout(() => {
                                    window.URL.revokeObjectURL(url);
                                    document.body.removeChild(a);
                                }, 100);

                                saveBtn.disabled = false;
                                saveBtn.innerHTML = originalText;
                            } catch (err) {
                                console.error(err);
                                showToast("Failed to save file");
                                saveBtn.disabled = false;
                            }
                        };
                        dlProgress.appendChild(saveBtn);
                        unlockDlBtn();
                    } else if (ev.status === "error") {
                        evtSource.close();
                        showToast(ev.message || "Download failed");
                        unlockDlBtn();
                    }
                } catch (err) {
                    console.error("SSE parse error", err);
                }
            };
            evtSource.onerror = () => {
                evtSource.close();
                showToast(tr("toastDisconnect"));
                unlockDlBtn();
            };

        } catch (err) {
            showToast(err.message);
            unlockDlBtn();
        }
    });

    function unlockDlBtn() {
        dlStartBtn.disabled = false;
        dlBtnLabel.hidden = false;
        dlBtnLoader.hidden = true;
    }

})();

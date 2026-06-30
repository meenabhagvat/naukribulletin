/* NaukriBulletin Quiz Engine — v1
   Reusable across all mock test pages.
   Each test page must define a global `QUIZ_DATA` object (or load it via fetch
   from /mock-test/data/<set-id>.json) with this shape:

   {
     "id": "ssc-cgl-tier1-set1",
     "title": "SSC CGL Tier 1 — Mock Test 1",
     "exam": "SSC CGL",
     "durationMinutes": 20,
     "sections": [
       { "name": "General Intelligence & Reasoning", "questions": [ ...Q ] },
       { "name": "General Awareness", "questions": [ ...Q ] }
     ]
   }

   Question shape:
   {
     "q": "Question text",
     "options": ["A", "B", "C", "D"],
     "answer": 0,           // index into options
     "explanation": "Why this is correct (optional)"
   }
*/

(function () {
  "use strict";

  function flattenQuestions(data) {
    const all = [];
    data.sections.forEach((section, sIdx) => {
      section.questions.forEach((q, qIdx) => {
        all.push({ ...q, _section: section.name, _sectionIdx: sIdx, _qIdx: qIdx });
      });
    });
    return all;
  }

  function el(tag, attrs = {}, ...children) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === "class") e.className = v;
      else if (k === "html") e.innerHTML = v;
      else e.setAttribute(k, v);
    });
    children.forEach((c) => {
      if (typeof c === "string") e.appendChild(document.createTextNode(c));
      else if (c) e.appendChild(c);
    });
    return e;
  }

  function initQuiz(rootId, data) {
    const root = document.getElementById(rootId);
    if (!root) return;

    const questions = flattenQuestions(data);
    const total = questions.length;
    let current = 0;
    const userAnswers = new Array(total).fill(null);
    let timeLeft = data.durationMinutes ? data.durationMinutes * 60 : (data.totalTime || 1200); // accept durationMinutes (min) or totalTime (sec)
    let timerInterval = null;
    let submitted = false;

    root.innerHTML = "";

    // ---- Header / progress bar ----
    const header = el("div", { class: "qe-header" },
      el("div", { class: "qe-title" }, data.title),
      el("div", { class: "qe-meta" },
        el("span", { class: "qe-timer", id: "qe-timer" }, formatTime(timeLeft)),
        el("span", { class: "qe-progress-text", id: "qe-progress-text" }, `Question 1 of ${total}`)
      )
    );
    const progressBarOuter = el("div", { class: "qe-progress-outer" });
    const progressBarInner = el("div", { class: "qe-progress-inner", id: "qe-progress-inner" });
    progressBarOuter.appendChild(progressBarInner);

    root.appendChild(header);
    root.appendChild(progressBarOuter);

    // ---- Question area ----
    const qArea = el("div", { class: "qe-question-area", id: "qe-question-area" });
    root.appendChild(qArea);

    // ---- Question palette (jump nav) ----
    const palette = el("div", { class: "qe-palette", id: "qe-palette" });
    root.appendChild(el("div", { class: "qe-palette-wrap" },
      el("div", { class: "qe-palette-label" }, "Question Palette"),
      palette
    ));

    // ---- Nav buttons ----
    const navRow = el("div", { class: "qe-nav-row" },
      el("button", { class: "qe-btn qe-btn-secondary", id: "qe-prev" }, "← Previous"),
      el("button", { class: "qe-btn qe-btn-clear", id: "qe-clear" }, "Clear Response"),
      el("button", { class: "qe-btn qe-btn-secondary", id: "qe-next" }, "Next →"),
      el("button", { class: "qe-btn qe-btn-submit", id: "qe-submit" }, "Submit Test")
    );
    root.appendChild(navRow);

    // ---- Result area (hidden initially) ----
    const resultArea = el("div", { class: "qe-result-area", id: "qe-result-area", style: "display:none;" });
    root.appendChild(resultArea);

    function formatTime(sec) {
      const m = Math.floor(sec / 60).toString().padStart(2, "0");
      const s = (sec % 60).toString().padStart(2, "0");
      return `${m}:${s}`;
    }

    function renderPalette() {
      palette.innerHTML = "";
      questions.forEach((q, i) => {
        const status = userAnswers[i] === null ? "unanswered" : "answered";
        const cls = "qe-pal-btn" + (i === current ? " qe-pal-current" : "") + " qe-pal-" + status;
        const btn = el("button", { class: cls, "data-idx": i }, String(i + 1));
        btn.addEventListener("click", () => { current = i; render(); });
        palette.appendChild(btn);
      });
    }

    function renderQuestion() {
      qArea.innerHTML = "";
      const q = questions[current];
      const card = el("div", { class: "qe-card" });
      card.appendChild(el("div", { class: "qe-section-tag" }, q._section));
      card.appendChild(el("div", { class: "qe-q-text" }, `${current + 1}. ${q.q}`));

      const optsWrap = el("div", { class: "qe-options" });
      q.options.forEach((opt, i) => {
        const selected = userAnswers[current] === i;
        const optBtn = el("button", {
          class: "qe-option" + (selected ? " qe-option-selected" : ""),
          "data-i": i
        },
          el("span", { class: "qe-option-letter" }, String.fromCharCode(65 + i)),
          el("span", { class: "qe-option-text" }, opt)
        );
        optBtn.addEventListener("click", () => {
          userAnswers[current] = i;
          render();
        });
        optsWrap.appendChild(optBtn);
      });
      card.appendChild(optsWrap);
      qArea.appendChild(card);
    }

    function render() {
      document.getElementById("qe-progress-text").textContent = `Question ${current + 1} of ${total}`;
      const pct = ((current + 1) / total) * 100;
      progressBarInner.style.width = pct + "%";
      renderQuestion();
      renderPalette();
      document.getElementById("qe-prev").disabled = current === 0;
      document.getElementById("qe-next").style.display = current === total - 1 ? "none" : "inline-block";
    }

    document.getElementById("qe-prev").addEventListener("click", () => {
      if (current > 0) { current--; render(); }
    });
    document.getElementById("qe-next").addEventListener("click", () => {
      if (current < total - 1) { current++; render(); }
    });
    document.getElementById("qe-clear").addEventListener("click", () => {
      userAnswers[current] = null;
      render();
    });
    document.getElementById("qe-submit").addEventListener("click", () => {
      if (submitted) return;
      const unanswered = userAnswers.filter((a) => a === null).length;
      if (unanswered > 0) {
        if (!confirm(`You have ${unanswered} unanswered question(s). Submit anyway?`)) return;
      }
      finishQuiz();
    });

    function startTimer() {
      timerInterval = setInterval(() => {
        timeLeft--;
        document.getElementById("qe-timer").textContent = formatTime(timeLeft);
        if (timeLeft <= 60) document.getElementById("qe-timer").classList.add("qe-timer-warn");
        if (timeLeft <= 0) {
          clearInterval(timerInterval);
          finishQuiz();
        }
      }, 1000);
    }

    function finishQuiz() {
      if (submitted) return;
      submitted = true;
      clearInterval(timerInterval);

      let correct = 0, wrong = 0, skipped = 0;
      const sectionStats = {};
      questions.forEach((q, i) => {
        sectionStats[q._section] = sectionStats[q._section] || { correct: 0, wrong: 0, skipped: 0, total: 0 };
        sectionStats[q._section].total++;
        if (userAnswers[i] === null) { skipped++; sectionStats[q._section].skipped++; }
        else if (userAnswers[i] === q.answer) { correct++; sectionStats[q._section].correct++; }
        else { wrong++; sectionStats[q._section].wrong++; }
      });

      const score = correct * 2 - wrong * 0.5; // SSC-style +2 / -0.5
      const maxScore = total * 2;
      const pct = ((correct / total) * 100).toFixed(1);

      qArea.style.display = "none";
      palette.parentElement.style.display = "none";
      navRow.style.display = "none";
      progressBarOuter.style.display = "none";
      header.style.display = "none";

      resultArea.style.display = "block";
      resultArea.innerHTML = "";

      resultArea.appendChild(el("div", { class: "qe-result-title" }, "🎯 Test Completed!"));
      const scoreGrid = el("div", { class: "qe-score-grid" },
        el("div", { class: "qe-score-box qe-score-total" },
          el("div", { class: "qe-score-num" }, score.toFixed(1) + " / " + maxScore),
          el("div", { class: "qe-score-label" }, "Your Score")),
        el("div", { class: "qe-score-box qe-score-correct" },
          el("div", { class: "qe-score-num" }, String(correct)),
          el("div", { class: "qe-score-label" }, "Correct")),
        el("div", { class: "qe-score-box qe-score-wrong" },
          el("div", { class: "qe-score-num" }, String(wrong)),
          el("div", { class: "qe-score-label" }, "Wrong")),
        el("div", { class: "qe-score-box qe-score-skipped" },
          el("div", { class: "qe-score-num" }, String(skipped)),
          el("div", { class: "qe-score-label" }, "Skipped")),
        el("div", { class: "qe-score-box qe-score-pct" },
          el("div", { class: "qe-score-num" }, pct + "%"),
          el("div", { class: "qe-score-label" }, "Accuracy"))
      );
      resultArea.appendChild(scoreGrid);

      // Section-wise breakdown
      const sectionTable = el("div", { class: "qe-section-breakdown" },
        el("div", { class: "qe-breakdown-title" }, "Section-wise Performance")
      );
      Object.entries(sectionStats).forEach(([name, s]) => {
        sectionTable.appendChild(el("div", { class: "qe-breakdown-row" },
          el("span", { class: "qe-breakdown-name" }, name),
          el("span", { class: "qe-breakdown-stat" }, `${s.correct}/${s.total} correct`)
        ));
      });
      resultArea.appendChild(sectionTable);

      // Review answers
      const reviewBtn = el("button", { class: "qe-btn qe-btn-submit", id: "qe-review-btn" }, "📋 Review Answers");
      resultArea.appendChild(reviewBtn);

      const reviewArea = el("div", { id: "qe-review-area", style: "display:none;margin-top:20px;" });
      resultArea.appendChild(reviewArea);

      reviewBtn.addEventListener("click", () => {
        if (reviewArea.style.display === "none") {
          reviewArea.style.display = "block";
          reviewArea.innerHTML = "";
          questions.forEach((q, i) => {
            const ua = userAnswers[i];
            const isCorrect = ua === q.answer;
            const card = el("div", { class: "qe-review-card" });
            card.appendChild(el("div", { class: "qe-section-tag" }, q._section));
            card.appendChild(el("div", { class: "qe-q-text" }, `${i + 1}. ${q.q}`));
            q.options.forEach((opt, oi) => {
              let cls = "qe-review-option";
              if (oi === q.answer) cls += " qe-review-correct";
              if (oi === ua && ua !== q.answer) cls += " qe-review-wrong-selected";
              card.appendChild(el("div", { class: cls },
                el("span", { class: "qe-option-letter" }, String.fromCharCode(65 + oi)),
                el("span", { class: "qe-option-text" }, opt),
                oi === q.answer ? el("span", { class: "qe-tag-correct" }, "✓ Correct") : null,
                (oi === ua && ua !== q.answer) ? el("span", { class: "qe-tag-wrong" }, "✗ Your answer") : null
              ));
            });
            if (q.explanation) {
              card.appendChild(el("div", { class: "qe-explanation" }, "💡 " + q.explanation));
            }
            if (ua === null) {
              card.appendChild(el("div", { class: "qe-explanation qe-skipped-note" }, "⚠️ You did not attempt this question."));
            }
            reviewArea.appendChild(card);
          });
          reviewBtn.textContent = "📋 Hide Review";
        } else {
          reviewArea.style.display = "none";
          reviewBtn.textContent = "📋 Review Answers";
        }
      });

      // Retake button
      resultArea.appendChild(el("button", {
        class: "qe-btn qe-btn-secondary", id: "qe-retake",
        style: "margin-top:16px;"
      }, "🔄 Retake Test"));
      document.getElementById("qe-retake").addEventListener("click", () => {
        location.reload();
      });
    }

    // init
    render();
    startTimer();
  }

  window.NBQuiz = { init: initQuiz };
})();

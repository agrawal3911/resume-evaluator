/* ================================================================
   Resume Evaluator — Application Logic
   ================================================================ */

// --- Constants ---
const SCORE_MAX = {
  required_skills_score: 60,
  preferred_skills_score: 15,
  experience_score: 15,
  education_score: 10,
};

const SCORE_LABELS = {
  required_skills_score: 'Required Skills',
  preferred_skills_score: 'Preferred Skills',
  experience_score: 'Experience',
  education_score: 'Education',
};

const GAUGE_RADIUS = 70;
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * GAUGE_RADIUS;

// --- DOM References ---
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
  inputSection:   $('#input-section'),
  loadingSection: $('#loading-section'),
  errorSection:   $('#error-section'),
  resultsSection: $('#results-section'),

  dropZone:    $('#drop-zone'),
  fileInput:   $('#file-input'),
  fileInfo:    $('#file-info'),
  fileName:    $('#file-name'),
  removeFile:  $('#remove-file'),
  jdText:      $('#jd-text'),
  evaluateBtn: $('#evaluate-btn'),

  errorMessage: $('#error-message'),
  retryBtn:     $('#retry-btn'),

  gaugeFill:    $('#gauge-fill'),
  scoreText:    $('#score-text'),
  verdictBadge: $('#verdict-badge'),
  summaryText:  $('#summary-text'),

  breakdownBars:    $('#breakdown-bars'),
  requiredSkills:   $('#required-skills'),
  preferredSkills:  $('#preferred-skills'),
  strengthsList:    $('#strengths-list'),
  gapsList:         $('#gaps-list'),
  experienceMatch:  $('#experience-match'),
  experienceReason: $('#experience-reasoning'),
  educationMatch:   $('#education-match'),
  educationReason:  $('#education-reasoning'),
  finalReasoning:   $('#final-reasoning'),

  newEvalBtn: $('#new-eval-btn'),
};

let selectedFile = null;

// --- Initialization ---
function init() {
  // Drag & drop
  dom.dropZone.addEventListener('dragover', handleDragOver);
  dom.dropZone.addEventListener('dragleave', handleDragLeave);
  dom.dropZone.addEventListener('drop', handleDrop);
  dom.dropZone.addEventListener('click', () => dom.fileInput.click());

  // File input
  dom.fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) handleFileSelect(e.target.files[0]);
  });

  // Remove file
  dom.removeFile.addEventListener('click', (e) => {
    e.stopPropagation();
    removeFile();
  });

  // JD text change
  dom.jdText.addEventListener('input', updateSubmitButton);

  // Submit
  dom.evaluateBtn.addEventListener('click', handleSubmit);

  // Error retry
  dom.retryBtn.addEventListener('click', resetToInput);

  // New evaluation
  dom.newEvalBtn.addEventListener('click', resetToInput);

  // Initialize gauge
  dom.gaugeFill.setAttribute('stroke-dasharray', GAUGE_CIRCUMFERENCE);
  dom.gaugeFill.setAttribute('stroke-dashoffset', GAUGE_CIRCUMFERENCE);
}

// --- Drag & Drop ---
function handleDragOver(e) {
  e.preventDefault();
  e.stopPropagation();
  dom.dropZone.classList.add('drag-over');
}

function handleDragLeave(e) {
  e.preventDefault();
  e.stopPropagation();
  dom.dropZone.classList.remove('drag-over');
}

function handleDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  dom.dropZone.classList.remove('drag-over');
  const files = e.dataTransfer.files;
  if (files.length) handleFileSelect(files[0]);
}

// --- File Handling ---
function handleFileSelect(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'docx'].includes(ext)) {
    showError('Please upload a .pdf or .docx file.');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showError('File size exceeds 10 MB limit.');
    return;
  }
  selectedFile = file;
  dom.fileName.textContent = file.name;
  dom.fileInfo.classList.remove('hidden');
  dom.dropZone.style.display = 'none';
  updateSubmitButton();
}

function removeFile() {
  selectedFile = null;
  dom.fileInput.value = '';
  dom.fileInfo.classList.add('hidden');
  dom.dropZone.style.display = '';
  updateSubmitButton();
}

function updateSubmitButton() {
  const hasFile = selectedFile !== null;
  const hasJD = dom.jdText.value.trim().length > 0;
  dom.evaluateBtn.disabled = !(hasFile && hasJD);
}

// --- Section Management ---
function showSection(sectionId) {
  ['input-section', 'loading-section', 'error-section', 'results-section'].forEach((id) => {
    const el = document.getElementById(id);
    if (id === sectionId) {
      el.classList.remove('hidden');
      el.classList.add('fade-in');
    } else {
      el.classList.add('hidden');
      el.classList.remove('fade-in');
    }
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// --- Loading Steps Animation ---
function animateLoadingSteps() {
  const steps = $$('.loading-step');
  const delays = [0, 1200, 3000, 5000];
  steps.forEach((step, i) => {
    setTimeout(() => {
      // Mark previous steps as done
      for (let j = 0; j < i; j++) {
        steps[j].classList.remove('active');
        steps[j].classList.add('done');
      }
      step.classList.add('active');
    }, delays[i]);
  });
}

// --- Submit ---
async function handleSubmit() {
  if (!selectedFile || !dom.jdText.value.trim()) return;

  showSection('loading-section');
  animateLoadingSteps();

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('jd_text', dom.jdText.value.trim());

  try {
    const response = await fetch('/evaluate', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => null);
      const message = err?.detail || `Server returned ${response.status}. Please try again.`;
      throw new Error(message);
    }

    const data = await response.json();
    renderResults(data);
  } catch (error) {
    showError(error.message || 'An unexpected error occurred. Please try again.');
  }
}

// --- Error Display ---
function showError(message) {
  dom.errorMessage.textContent = message;
  showSection('error-section');
}

// --- Reset ---
function resetToInput() {
  showSection('input-section');
}

// --- Score Color ---
function getScoreColor(score) {
  if (score >= 80) return '#22c55e';
  if (score >= 60) return '#f59e0b';
  if (score >= 40) return '#fb923c';
  return '#ef4444';
}

function getVerdictClass(verdict) {
  const v = verdict.toLowerCase();
  if (v.includes('strong')) return 'verdict-strong';
  if (v.includes('moderate')) return 'verdict-moderate';
  if (v.includes('weak')) return 'verdict-weak';
  return 'verdict-poor';
}

// --- Render Results ---
function renderResults(data) {
  const { score, verdict, match_result, reasoning } = data;

  // Animate gauge
  animateGauge(score);

  // Verdict badge
  dom.verdictBadge.textContent = verdict;
  dom.verdictBadge.className = 'verdict-badge ' + getVerdictClass(verdict);

  // Summary
  dom.summaryText.textContent = reasoning.summary || '';

  // Score breakdown
  renderBreakdownBars(match_result.score_breakdown);

  // Skills
  renderSkills(
    match_result.matched_required_skills,
    match_result.missing_required_skills,
    dom.requiredSkills
  );
  renderSkills(
    match_result.matched_preferred_skills,
    match_result.missing_preferred_skills,
    dom.preferredSkills
  );

  // Strengths & Gaps
  renderList(reasoning.strengths, dom.strengthsList);
  renderList(reasoning.gaps, dom.gapsList);

  // Experience
  dom.experienceMatch.textContent = match_result.experience_match || '';
  dom.experienceReason.textContent = reasoning.experience_reasoning || '';

  // Education
  dom.educationMatch.textContent = match_result.education_match || '';
  dom.educationReason.textContent = reasoning.education_reasoning || '';

  // Final reasoning
  dom.finalReasoning.textContent = reasoning.final_reasoning || '';

  showSection('results-section');
}

// --- Gauge Animation ---
function animateGauge(score) {
  const color = getScoreColor(score);
  const offset = GAUGE_CIRCUMFERENCE - (score / 100) * GAUGE_CIRCUMFERENCE;

  // Reset first
  dom.gaugeFill.setAttribute('stroke-dashoffset', GAUGE_CIRCUMFERENCE);
  dom.scoreText.textContent = '0';

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      dom.gaugeFill.style.stroke = color;
      dom.gaugeFill.setAttribute('stroke-dashoffset', offset);

      // Animate the number
      animateCounter(dom.scoreText, 0, score, 1200);
    });
  });
}

function animateCounter(element, start, end, duration) {
  const startTime = performance.now();
  const hasDecimal = end % 1 !== 0;

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = start + (end - start) * eased;

    element.textContent = hasDecimal ? current.toFixed(1) : Math.round(current);

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

// --- Breakdown Bars ---
function renderBreakdownBars(breakdown) {
  dom.breakdownBars.innerHTML = '';

  const entries = [
    'required_skills_score',
    'preferred_skills_score',
    'experience_score',
    'education_score',
  ];

  entries.forEach((key, i) => {
    const value = breakdown[key];
    const max = SCORE_MAX[key];
    const pct = max > 0 ? (value / max) * 100 : 0;
    const color = getScoreColor((value / max) * 100);

    const row = document.createElement('div');
    row.className = 'breakdown-row';
    row.innerHTML = `
      <span class="breakdown-label">${SCORE_LABELS[key]}</span>
      <div class="breakdown-track">
        <div class="breakdown-fill" id="bar-${i}" style="background:${color}"></div>
      </div>
      <span class="breakdown-value">${value} / ${max}</span>
    `;
    dom.breakdownBars.appendChild(row);

    // Animate the bar after a small delay
    setTimeout(() => {
      document.getElementById(`bar-${i}`).style.width = `${pct}%`;
    }, 200 + i * 120);
  });
}

// --- Skills ---
function renderSkills(matched, missing, container) {
  container.innerHTML = '';

  if (matched.length === 0 && missing.length === 0) {
    container.innerHTML = '<p class="no-skills-msg">No skills specified</p>';
    return;
  }

  if (matched.length > 0) {
    const label = document.createElement('div');
    label.className = 'skills-subsection-label matched';
    label.textContent = `Matched (${matched.length})`;
    container.appendChild(label);

    const list = document.createElement('div');
    list.className = 'skills-list';
    matched.forEach((skill) => {
      const pill = document.createElement('span');
      pill.className = 'skill-pill matched';
      pill.innerHTML = `<span class="pill-icon">✓</span> ${escapeHtml(skill)}`;
      list.appendChild(pill);
    });
    container.appendChild(list);
  }

  if (missing.length > 0) {
    const label = document.createElement('div');
    label.className = 'skills-subsection-label missing';
    label.textContent = `Missing (${missing.length})`;
    container.appendChild(label);

    const list = document.createElement('div');
    list.className = 'skills-list';
    missing.forEach((skill) => {
      const pill = document.createElement('span');
      pill.className = 'skill-pill missing';
      pill.innerHTML = `<span class="pill-icon">✗</span> ${escapeHtml(skill)}`;
      list.appendChild(pill);
    });
    container.appendChild(list);
  }
}

// --- Reasoning Lists ---
function renderList(items, listElement) {
  listElement.innerHTML = '';
  if (!items || items.length === 0) {
    const li = document.createElement('li');
    li.textContent = 'None identified.';
    li.style.opacity = '0.5';
    listElement.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    listElement.appendChild(li);
  });
}

// --- Utility ---
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// --- Boot ---
document.addEventListener('DOMContentLoaded', init);

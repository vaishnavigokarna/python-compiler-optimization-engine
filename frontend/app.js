const $ = (id) => document.getElementById(id);

let optimizedCode = "";

// Render backend URL
const API_URL = "https://python-compiler-optimization-engine.onrender.com";

const sample = `def calculate(n):
    x = 10 * 20
    unused = 100
    total = 0
    for i in range(n):
        total = total + x + i
    return total

print(calculate(10000))
`;

$("sampleBtn").onclick = () => {
  $("code").value = sample;
};

async function api(path, body) {
  const response = await fetch(API_URL + path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }

  return data;
}


// =========================
// ANALYZE CODE
// =========================

$("analyzeBtn").onclick = async () => {
  try {
    const data = await api("/api/analyze", {
      code: $("code").value
    });

    if (!data.valid) {
      $("analysis").innerHTML = `
        <p class="warn">
          Syntax error: ${escapeHtml(data.syntax_error)}
        </p>
      `;
      return;
    }

    const s = data.summary;

    $("analysis").innerHTML = `
      <div class="metric">
        <span>Syntax</span>
        <span class="good">Valid</span>
      </div>

      <div class="metric">
        <span>Functions</span>
        <b>${s.functions}</b>
      </div>

      <div class="metric">
        <span>Loops</span>
        <b>${s.loops}</b>
      </div>

      <div class="metric">
        <span>Branches</span>
        <b>${s.branches}</b>
      </div>

      <div class="metric">
        <span>Max loop depth</span>
        <b>${s.max_loop_depth}</b>
      </div>

      <div class="metric">
        <span>Cyclomatic complexity</span>
        <b>${s.cyclomatic_complexity}</b>
      </div>

      <div class="metric">
        <span>Dead assignments</span>
        <b>${s.dead_assignments}</b>
      </div>

      <h3>Dead Code</h3>

      ${
        data.dead_code.length
          ? data.dead_code
              .map(
                x =>
                  `<div class="warn">
                    Variable '${escapeHtml(x.variable)}' is never loaded.
                  </div>`
              )
              .join("")
          : `<p class="good">
               No simple dead assignments detected.
             </p>`
      }
    `;

    $("dependencies").innerHTML = data.dependencies.length
      ? data.dependencies
          .map(
            d =>
              `<div>
                ${escapeHtml(d.from)} → ${escapeHtml(d.to)}
              </div>`
          )
          .join("")
      : "No simple variable dependencies detected.";

  } catch (e) {
    alert(e.message);
  }
};


// =========================
// OPTIMIZE CODE
// =========================

$("optimizeBtn").onclick = async () => {
  try {
    const data = await api("/api/optimize", {
      code: $("code").value
    });

    optimizedCode = data.optimized_code;

    $("originalCode").textContent = $("code").value;
    $("optimizedCode").textContent = optimizedCode;

    $("benchmarkBtn").disabled = false;

    const o = data.optimizations;

    $("optimizations").innerHTML = `
      <div class="metric">
        <span>Constant folding</span>
        <b>${o.constant_folding}</b>
      </div>

      <div class="metric">
        <span>Dead assignments removed</span>
        <b>${o.dead_assignments_removed}</b>
      </div>

      <div>
        <b>Removed:</b>
        ${
          o.dead_assignment_names.length
            ? o.dead_assignment_names.join(", ")
            : "None"
        }
      </div>

      <h3>Loop suggestions</h3>

      ${
        data.suggestions.length
          ? data.suggestions
              .map(
                x =>
                  `<p class="warn">
                    Line ${x.line}: ${escapeHtml(x.message)}
                  </p>`
              )
              .join("")
          : `<p class="good">
               No simple loop candidates detected.
             </p>`
      }
    `;

  } catch (e) {
    alert(e.message);
  }
};


// =========================
// BENCHMARK
// =========================

$("benchmarkBtn").onclick = async () => {
  try {
    $("benchmark").textContent = "Running...";

    const data = await api("/api/benchmark", {
      original_code: $("code").value,
      optimized_code: optimizedCode,
      runs: 3
    });

    if (!data.success) {
      $("benchmark").innerHTML = `
        <p class="warn">
          ${escapeHtml(data.error || "Benchmark failed")}
        </p>
      `;
      return;
    }

    const a = data.original.average_time;
    const b = data.optimized.average_time;
    const improvement = data.improvement_percent;

    $("benchmark").innerHTML = `
      <div class="metric">
        <span>Same output</span>

        <span class="${
          data.same_output ? "good" : "warn"
        }">
          ${data.same_output ? "YES ✓" : "NO ✗"}
        </span>
      </div>

      <div class="metric">
        <span>Original average time</span>
        <b>${a.toFixed(6)} s</b>
      </div>

      <div class="metric">
        <span>Optimized average time</span>
        <b>${b.toFixed(6)} s</b>
      </div>

      <div class="metric">
        <span>Performance change</span>
        <b>${improvement.toFixed(2)}%</b>
      </div>
    `;

    const max = Math.max(a, b, 0.000001);

    $("barOriginal").style.width =
      `${Math.max(5, (a / max) * 100)}%`;

    $("barOptimized").style.width =
      `${Math.max(5, (b / max) * 100)}%`;

  } catch (e) {
    alert(e.message);
  }
};


// =========================
// HTML ESCAPING
// =========================

function escapeHtml(s) {
  return String(s).replace(
    /[&<>"']/g,
    c =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[c])
  );
}


// =========================
// API STATUS
// =========================

fetch(API_URL + "/api/health")
  .then(response => {
    if (!response.ok) {
      throw new Error("API is offline");
    }

    return response.json();
  })
  .then(() => {
    $("status").textContent = "API Online";
  })
  .catch(() => {
    $("status").textContent = "API Offline";
  });
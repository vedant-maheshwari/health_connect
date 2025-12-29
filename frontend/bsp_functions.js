// --------------------------------------------------------------------------
// BSP TOOLKIT LIBRARY CONFIGURATION
// --------------------------------------------------------------------------

const bspTools = [
  {
    id: 'afib-detector',
    title: 'Atrial Fibrillation Detector',
    description: 'Deep learning model to detect Atrial Fibrillation from PPG and ECG signals.',
    category: 'cardiology',
    icon: 'fa-heart-pulse',
    color: '#d32f2f',
    tags: ['ECG', 'PPG', 'Deep Learning'],
    templateId: 'tool-afib-detector'
  }
  // Future tools like 'Sleep Apnea Detector', 'HRV Analyzer' can be added here easily
];


// --------------------------------------------------------------------------
// LIBRARY MANAGEMENT FUNCTIONS
// --------------------------------------------------------------------------

function renderBSPToolkit() {
  console.log("Rendering BSP Toolkit...", bspTools);
  const grid = document.getElementById('bspToolsGrid');
  if (!grid) {
    console.error("BSP Tools Grid element not found!");
    return;
  }
  const noResults = document.getElementById('bspNoResults');

  // Safety check for search inputs in case they are missing
  const searchInput = document.getElementById('bspSearchInput');
  const filterInput = document.getElementById('bspCategoryFilter');

  const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
  const filterCategory = filterInput ? filterInput.value : 'all';

  grid.innerHTML = '';
  let matchCount = 0;

  bspTools.forEach(tool => {
    // Filter Logic
    const matchesSearch = tool.title.toLowerCase().includes(searchTerm) ||
      tool.description.toLowerCase().includes(searchTerm) ||
      tool.tags.some(tag => tag.toLowerCase().includes(searchTerm));

    const matchesCategory = filterCategory === 'all' || tool.category === filterCategory;

    if (matchesSearch && matchesCategory) {
      matchCount++;
      const card = document.createElement('div');
      card.className = 'card';
      card.style.cursor = 'pointer';
      card.style.transition = 'transform 0.2s';
      card.onmouseover = () => card.style.transform = 'translateY(-5px)';
      card.onmouseout = () => card.style.transform = 'translateY(0)';
      card.onclick = () => openBSPTool(tool.id);

      card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:start; margin-bottom:15px;">
                    <div style="background:${tool.color}15; color:${tool.color}; width:50px; height:50px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:24px;">
                        <i class="fa-solid ${tool.icon}"></i>
                    </div>
                    <span style="background:#f0f0f0; color:#666; padding:4px 8px; border-radius:4px; font-size:11px; text-transform:uppercase; font-weight:600;">
                        ${tool.category}
                    </span>
                </div>
                <h4 style="margin-bottom:8px; color:#333;">${tool.title}</h4>
                <p style="color:#666; font-size:13px; line-height:1.5; margin-bottom:15px;">${tool.description}</p>
                <div style="display:flex; flex-wrap:wrap; gap:5px;">
                    ${tool.tags.map(tag => `<span style="font-size:11px; color:#555; background:#f8f9fa; padding:2px 6px; border:1px solid #eee; border-radius:4px;">#${tag}</span>`).join('')}
                </div>
            `;
      grid.appendChild(card);
    }
  });

  if (matchCount === 0) {
    noResults.style.display = 'block';
  } else {
    noResults.style.display = 'none';
  }
}

function filterBSPTools() {
  renderBSPToolkit();
}

function openBSPTool(toolId) {
  const tool = bspTools.find(t => t.id === toolId);
  if (!tool) return;

  // Switch Views
  document.getElementById('bspLibrary').style.display = 'none';
  document.getElementById('bspToolView').style.display = 'block';

  // Set Title
  document.getElementById('activeToolTitle').innerHTML = `<i class="fa-solid ${tool.icon}" style="color:${tool.color}; margin-right:10px;"></i> ${tool.title}`;

  // Inject Content from Template
  const template = document.getElementById(tool.templateId);
  const container = document.getElementById('activeToolContent');

  if (template) {
    // Be careful moving elements to avoid losing event listeners or state if simpler cloning isn't creating issues.
    // For simplicity, we just clone content nicely or manage display. 
    // Better approach for unique IDs: just copy HTML string.
    container.innerHTML = template.innerHTML;

    // Re-attach specific dynamic logic if needed, but for simple forms innerHTML is fine.
    // NOTE: Input file listeners are reset, but that's okay as they are new inputs.
  } else {
    container.innerHTML = '<p>Tool template not found.</p>';
  }
}

function closeBSPTool() {
  document.getElementById('bspLibrary').style.display = 'block';
  document.getElementById('bspToolView').style.display = 'none';
  document.getElementById('activeToolContent').innerHTML = ''; // Clean up
}


// --------------------------------------------------------------------------
// SIGNAL PROCESSING LOGIC (EXISTING)
// --------------------------------------------------------------------------

async function processSignals() {
  // Note: Since we are cloning HTML, we must select elements from the generated active content
  const container = document.getElementById('activeToolContent');
  const headerFile = container.querySelector('#headerFile').files[0];
  const datFile = container.querySelector('#datFile').files[0];

  if (!headerFile || !datFile) {
    alert('Please upload both the header (.hea) and signal data (.dat) files.');
    return;
  }

  // Show loading
  // Since IDs might be duplicated if we are not careful, scoping to container is safer
  const resultsDiv = container.querySelector('#bspResults');
  const resultContent = container.querySelector('#classificationResult');
  resultsDiv.style.display = 'block';
  resultContent.innerHTML = '<p style="text-align:center;"><i class="fa-solid fa-spinner fa-spin"></i> Analyzing signals...</p>';

  try {
    // Create form data for API
    const formData = new FormData();
    formData.append('header_file', headerFile);
    formData.append('dat_file', datFile);

    // Get token
    const token = localStorage.getItem('token');

    // Use the API_BASE_URL defined in doctor_dashboard.html
    const response = await fetch(`${API_BASE_URL}/bsp/analyze`, {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + token
      },
      body: formData
    });

    if (!response.ok) {
      let errorMsg = 'Analysis failed';
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errorMsg;
      } catch (e) { }
      throw new Error(errorMsg);
    }

    const result = await response.json();

    // Use a scoped display function or pass the container
    displayBSPResultsInContainer(result, container);

  } catch (error) {
    console.error('BSP Analysis error:', error);
    resultContent.innerHTML = `<p style="color:#dc3545;">Error processing signals: ${error.message}</p>`;
  }
}

function displayBSPResultsInContainer(result, container) {
  const resultContent = container.querySelector('#classificationResult');
  const isAF = result.classification.includes('Atrial Fibrillation');
  const confidencePercent = (parseFloat(result.confidence) * 100).toFixed(1);

  resultContent.innerHTML = `
    <div style="text-align:center; padding:20px;">
      <div style="margin-bottom:20px;">
        <i class="fa-solid fa-heartbeat" style="font-size:48px; color:${isAF ? '#dc3545' : '#28a745'};"></i>
      </div>
      <h3 style="color: ${isAF ? '#dc3545' : '#28a745'}; margin-bottom:10px;">
        ${result.classification}
      </h3>
      <p style="font-size:18px; margin-bottom:20px;">
        Confidence: <strong>${confidencePercent}%</strong>
      </p>
      <div style="background:white; padding:15px; border-radius:8px; margin-top:20px; border:1px solid #eee;">
        <table style="width:100%; text-align:left;">
          <tr><td style="padding:4px 0;"><strong>Segments Processed:</strong></td><td>${result.segments_processed}</td></tr>
          <tr><td style="padding:4px 0;"><strong>AF Segments Detected:</strong></td><td>${result.af_segments_count || 0}</td></tr>
          <tr><td style="padding:4px 0;"><strong>AF Probability:</strong></td><td>${(result.af_probability * 100).toFixed(1)}%</td></tr>
        </table>
      </div>
      ${isAF ? '<p style="margin-top:15px; color:#dc3545; font-weight:500;"></p>' : ''}
    </div>
  `;
}

(function () {
  const passwordInput = document.getElementById('password');
  const questionInput = document.getElementById('question');
  const aqlInput = document.getElementById('aql');
  const limitInput = document.getElementById('limit');
  const pageInput = document.getElementById('page');
  const generateButton = document.getElementById('generate');
  const runButton = document.getElementById('run');
  const generateStatus = document.getElementById('generate-status');
  const runStatus = document.getElementById('run-status');
  const resultsMeta = document.getElementById('results-meta');
  const resultsError = document.getElementById('results-error');
  const tableHead = document.querySelector('#results-table thead');
  const tableBody = document.querySelector('#results-table tbody');
  const tableEmpty = document.getElementById('table-empty');
  const tableWrap = document.getElementById('table-wrap');
  const jsonWrap = document.getElementById('json-wrap');
  const resultsJson = document.getElementById('results-json');
  const graphWrap = document.getElementById('graph-wrap');
  const graphEmpty = document.getElementById('graph-empty');
  const graphHover = document.getElementById('graph-hover');
  const viewTable = document.getElementById('view-table');
  const viewJson = document.getElementById('view-json');
  const viewGraph = document.getElementById('view-graph');

  const maxLimit = Number(window.MAX_AQL_LIMIT || 100);
  let lastRows = [];
  let currentView = 'table';
  let graph = null;

  passwordInput.value = sessionStorage.getItem('catalogPassword') || '';
  passwordInput.addEventListener('change', function () {
    sessionStorage.setItem('catalogPassword', passwordInput.value);
  });

  function setStatus(el, text) {
    el.textContent = text || '';
  }

  function showError(message) {
    if (!message) {
      resultsError.hidden = true;
      resultsError.textContent = '';
      return;
    }
    resultsError.hidden = false;
    resultsError.textContent = message;
    resultsError.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function pagination() {
    const limit = Number(limitInput.value);
    const page = Number(pageInput.value);
    if (!Number.isInteger(limit) || limit < 1 || limit > maxLimit) {
      throw new Error('Limit must be an integer from 1 to ' + maxLimit);
    }
    if (!Number.isInteger(page) || page < 0) {
      throw new Error('Page must be a non-negative integer');
    }
    return { limit: limit, page: page };
  }

  async function postJson(path, body) {
    const response = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(function () {
      return { error: 'Request failed with status ' + response.status };
    });
    if (!response.ok) {
      throw new Error(data.error || 'Request failed with status ' + response.status);
    }
    return data;
  }

  function cellValue(value) {
    if (value === null || value === undefined) {
      return '';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return String(value);
  }

  function renderTable(rows) {
    tableHead.innerHTML = '';
    tableBody.innerHTML = '';
    if (!rows.length) {
      tableEmpty.hidden = false;
      return;
    }
    tableEmpty.hidden = true;
    const columns = [];
    rows.forEach(function (row) {
      if (row && typeof row === 'object' && !Array.isArray(row)) {
        Object.keys(row).forEach(function (key) {
          if (columns.indexOf(key) === -1) {
            columns.push(key);
          }
        });
      }
    });
    if (!columns.length) {
      columns.push('value');
    }
    const headerRow = document.createElement('tr');
    columns.forEach(function (column) {
      const th = document.createElement('th');
      th.textContent = column;
      headerRow.appendChild(th);
    });
    tableHead.appendChild(headerRow);
    rows.forEach(function (row) {
      const tr = document.createElement('tr');
      columns.forEach(function (column) {
        const td = document.createElement('td');
        td.textContent = row && typeof row === 'object' && !Array.isArray(row)
          ? cellValue(row[column])
          : cellValue(row);
        tr.appendChild(td);
      });
      tableBody.appendChild(tr);
    });
  }

  function renderJson(rows) {
    resultsJson.textContent = JSON.stringify(rows, null, 2);
  }

  const COLLECTION_COLORS = [
    '#0b6e99', '#2a9d8f', '#c9a227', '#e76f51', '#6d597a',
    '#355070', '#4a7c59', '#b56576', '#3d5a80', '#9c6644',
  ];

  function collectionOf(id) {
    if (!id || typeof id !== 'string') {
      return '';
    }
    const slash = id.indexOf('/');
    return slash > 0 ? id.slice(0, slash) : '';
  }

  function colorForCollection(collection) {
    if (!collection) {
      return COLLECTION_COLORS[0];
    }
    let hash = 0;
    for (let i = 0; i < collection.length; i += 1) {
      hash = ((hash << 5) - hash) + collection.charCodeAt(i);
      hash |= 0;
    }
    return COLLECTION_COLORS[Math.abs(hash) % COLLECTION_COLORS.length];
  }

  function shortId(id) {
    if (!id || typeof id !== 'string') {
      return '';
    }
    const slash = id.lastIndexOf('/');
    return slash >= 0 ? id.slice(slash + 1) : id;
  }

  function nodeLabel(id, doc) {
    if (doc && typeof doc === 'object') {
      if (doc.name) {
        return String(doc.name);
      }
      if (doc._key) {
        return String(doc._key);
      }
    }
    return shortId(id);
  }

  function ensureNode(nodes, id, doc) {
    if (!id) {
      return;
    }
    const collection = collectionOf(id);
    const existing = nodes[id];
    const label = nodeLabel(id, doc);
    if (!existing || (doc && (doc.name || doc._key))) {
      nodes[id] = {
        data: {
          id: id,
          label: label,
          collection: collection,
          color: colorForCollection(collection),
        },
      };
    }
  }

  function graphElements(rows) {
    const nodes = {};
    const edges = [];
    rows.forEach(function (row, index) {
      if (!row || typeof row !== 'object') {
        return;
      }
      if (row._from && row._to) {
        ensureNode(nodes, row._from);
        ensureNode(nodes, row._to);
        edges.push({
          data: {
            id: row._id || ('edge-' + index),
            source: row._from,
            target: row._to,
            label: row.name || row.label || '',
            collection: collectionOf(row._id),
          },
        });
        return;
      }
      if (row._id) {
        ensureNode(nodes, row._id, row);
      }
    });
    return Object.keys(nodes).map(function (id) {
      return nodes[id];
    }).concat(edges);
  }

  const LABEL_NODE_LIMIT = 40;

  function packComponents(cy) {
    const components = cy.elements().components();
    if (components.length < 2) {
      return;
    }
    const gap = 56;
    const boxes = components.map(function (comp) {
      const bb = comp.boundingBox({ includeLabels: false });
      return {
        comp: comp,
        w: Math.max(bb.w, 1),
        h: Math.max(bb.h, 1),
      };
    });
    boxes.sort(function (a, b) {
      return (b.w * b.h) - (a.w * a.h);
    });
    const widest = boxes.reduce(function (max, box) {
      return Math.max(max, box.w);
    }, 0);
    const totalArea = boxes.reduce(function (sum, box) {
      return sum + box.w * box.h;
    }, 0);
    const targetWidth = Math.max(widest, Math.sqrt(totalArea) * 1.15);
    let x = 0;
    let y = 0;
    let rowHeight = 0;
    boxes.forEach(function (box) {
      if (x > 0 && x + box.w > targetWidth) {
        x = 0;
        y += rowHeight + gap;
        rowHeight = 0;
      }
      const bb = box.comp.boundingBox({ includeLabels: false });
      box.comp.shift({ x: x - bb.x1, y: y - bb.y1 });
      x += box.w + gap;
      rowHeight = Math.max(rowHeight, box.h);
    });
  }

  function updateNodeLabels(cy, fitZoom) {
    if (!cy) {
      return;
    }
    const zoom = cy.zoom() || 1;
    const sparse = cy.nodes().length <= LABEL_NODE_LIMIT;
    const zoomedIn = fitZoom != null && zoom > fitZoom * 1.25;
    const show = sparse || zoomedIn;
    cy.batch(function () {
      cy.nodes().style({
        'font-size': Math.max(6, 9 / zoom),
      });
      if (show) {
        cy.nodes().addClass('labeled');
      } else {
        cy.nodes().removeClass('labeled');
      }
    });
  }

  function renderGraph(rows) {
    const elements = graphElements(rows);
    const hasEdges = elements.some(function (el) {
      return el.data && el.data.source;
    });
    if (graphHover) {
      graphHover.textContent = '';
    }
    if (!hasEdges) {
      if (graph) {
        graph.destroy();
        graph = null;
      }
      document.getElementById('graph').innerHTML = '';
      graphEmpty.hidden = false;
      return;
    }
    graphEmpty.hidden = true;
    if (graph) {
      graph.destroy();
    }
    graph = cytoscape({
      container: document.getElementById('graph'),
      elements: elements,
      minZoom: 0.05,
      maxZoom: 4,
      wheelSensitivity: 0.25,
      style: [
        {
          selector: 'node',
          style: {
            label: '',
            'font-size': 9,
            'background-color': 'data(color)',
            color: '#1c2430',
            'text-outline-width': 2,
            'text-outline-color': '#fafcfd',
            'text-wrap': 'none',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'text-margin-y': 4,
            width: 16,
            height: 16,
          },
        },
        {
          selector: 'node.labeled',
          style: {
            label: 'data(label)',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.25,
            'line-color': '#b7c5ce',
            'target-arrow-color': '#b7c5ce',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'arrow-scale': 0.7,
            label: '',
          },
        },
      ],
      layout: {
        name: 'preset',
      },
    });
    let fitZoom = null;
    let fitting = false;
    function fitGraph() {
      if (!graph || graph.destroyed()) {
        return;
      }
      graph.resize();
      fitting = true;
      if (graph.nodes().length <= LABEL_NODE_LIMIT) {
        graph.nodes().addClass('labeled');
      } else {
        graph.nodes().removeClass('labeled');
      }
      graph.fit(graph.elements(), 40);
      fitZoom = graph.zoom();
      fitting = false;
      updateNodeLabels(graph, fitZoom);
    }
    graph.one('layoutstop', function () {
      packComponents(graph);
      requestAnimationFrame(function () {
        fitGraph();
        requestAnimationFrame(fitGraph);
      });
    });
    graph.layout({
      name: 'cose',
      animate: false,
      fit: false,
      padding: 40,
      randomize: true,
      componentSpacing: 100,
      nodeRepulsion: function () {
        return 4500;
      },
      nodeOverlap: 12,
      idealEdgeLength: function () {
        return 48;
      },
      edgeElasticity: function () {
        return 100;
      },
      nestingFactor: 1.2,
      gravity: 0.15,
      numIter: 800,
      initialTemp: 200,
      coolingFactor: 0.95,
      minTemp: 1.0,
    }).run();
    graph.on('zoom', function () {
      if (fitting) {
        return;
      }
      updateNodeLabels(graph, fitZoom);
    });
    graph.on('mouseover', 'node, edge', function (event) {
      const data = event.target.data();
      if (!graphHover) {
        return;
      }
      if (data.source) {
        graphHover.textContent = (data.collection || 'edge') + ': ' +
          data.source + ' → ' + data.target;
      } else {
        graphHover.textContent = (data.collection ? data.collection + ': ' : '') +
          data.id;
      }
    });
    graph.on('mouseout', 'node, edge', function () {
      if (graphHover) {
        graphHover.textContent = '';
      }
    });
  }

  function hasGraphRows(rows) {
    return (rows || []).some(function (row) {
      return row && typeof row === 'object' && row._from && row._to;
    });
  }

  function setView(view) {
    if (view === 'graph' && !hasGraphRows(lastRows)) {
      view = 'table';
    }
    currentView = view;
    viewTable.classList.toggle('active', view === 'table');
    viewJson.classList.toggle('active', view === 'json');
    viewGraph.classList.toggle('active', view === 'graph');
    tableWrap.hidden = view !== 'table';
    jsonWrap.hidden = view !== 'json';
    graphWrap.hidden = view !== 'graph';
    if (view === 'graph') {
      renderGraph(lastRows);
    }
  }

  function renderResults(rows) {
    lastRows = Array.isArray(rows) ? rows : [];
    resultsMeta.textContent = lastRows.length
      ? lastRows.length + ' row' + (lastRows.length === 1 ? '' : 's')
      : '';
    const graphable = hasGraphRows(lastRows);
    viewGraph.hidden = !graphable;
    renderTable(lastRows);
    renderJson(lastRows);
    if (currentView === 'graph') {
      if (graphable) {
        renderGraph(lastRows);
      } else {
        setView('table');
      }
    }
  }

  generateButton.addEventListener('click', async function () {
    showError('');
    setStatus(generateStatus, '');
    try {
      const page = pagination();
      if (!passwordInput.value) {
        throw new Error('Password is required');
      }
      if (!questionInput.value.trim()) {
        throw new Error('Enter a question first');
      }
      generateButton.disabled = true;
      setStatus(generateStatus, 'Generating…');
      const data = await postJson('/graph-query-generator', {
        password: passwordInput.value,
        query: questionInput.value.trim(),
        limit: page.limit,
        page: page.page,
      });
      if (data.error && !data.aql_query) {
        throw new Error(data.error);
      }
      aqlInput.value = data.aql_query || '';
      setStatus(generateStatus, data.aql_query ? 'AQL ready' : '');
    } catch (error) {
      setStatus(generateStatus, '');
      showError(error.message);
    } finally {
      generateButton.disabled = false;
    }
  });

  runButton.addEventListener('click', async function () {
    showError('');
    setStatus(runStatus, '');
    try {
      const page = pagination();
      if (!passwordInput.value) {
        throw new Error('Password is required');
      }
      if (!aqlInput.value.trim()) {
        throw new Error('Generate or enter an AQL query first');
      }
      runButton.disabled = true;
      setStatus(runStatus, 'Running…');
      const data = await postJson('/graph-query-generator/execute', {
        password: passwordInput.value,
        aql: aqlInput.value,
        limit: page.limit,
        page: page.page,
      });
      if (data.aql_query) {
        aqlInput.value = data.aql_query;
      }
      renderResults(data.aql_result || []);
      setStatus(runStatus, 'Done');
    } catch (error) {
      setStatus(runStatus, '');
      showError(error.message);
      renderResults([]);
    } finally {
      runButton.disabled = false;
    }
  });

  viewTable.addEventListener('click', function () {
    setView('table');
  });
  viewJson.addEventListener('click', function () {
    setView('json');
  });
  viewGraph.addEventListener('click', function () {
    setView('graph');
  });
  renderJson(lastRows);
})();

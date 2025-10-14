// Global state
let allIssues = [];
let activeIssues = [];
let currentIssues = []; // Currently displayed issues
let hierarchy = {};
let selectedIssue = null;
let showAllDependencies = false;
let showClosedIssues = false;
let currentView = 'graph';

// Helper functions
function getIssueTypeIcon(issueType) {
    const icons = {
        'bug': '🐛',
        'feature': '✨',
        'task': '📋',
        'epic': '🎯',
        'chore': '🔧'
    };
    return icons[issueType] || '📄';
}

function getIssueTypeSymbol(issueType) {
    const symbols = {
        'bug': 'B',
        'feature': 'F', 
        'task': 'T',
        'epic': 'E',
        'chore': 'C'
    };
    return symbols[issueType] || '?';
}

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    // Load data from embedded JSON
    const allIssuesData = document.getElementById('all-issues-data');
    const activeIssuesData = document.getElementById('active-issues-data');
    const hierarchyData = document.getElementById('hierarchy-data');
    
    if (allIssuesData) {
        allIssues = JSON.parse(allIssuesData.textContent);
    }
    
    if (activeIssuesData) {
        activeIssues = JSON.parse(activeIssuesData.textContent);
    }
    
    if (hierarchyData) {
        hierarchy = JSON.parse(hierarchyData.textContent);
    }
    
    // Initialize with active issues
    currentIssues = activeIssues;
    
    // Build initial hierarchy from active issues
    hierarchy = buildHierarchy(currentIssues);
    
    initializeEventListeners();
    initializeGraph();
    renderHierarchy();
});

function initializeEventListeners() {
    // View toggle
    document.getElementById('toggle-view').addEventListener('click', toggleView);
    
    // Show closed issues toggle
    document.getElementById('show-closed').addEventListener('change', function(e) {
        showClosedIssues = e.target.checked;
        updateCurrentIssues();
    });
    
    // Show all dependencies toggle
    document.getElementById('show-all-deps').addEventListener('change', function(e) {
        showAllDependencies = e.target.checked;
        updateGraphVisibility();
    });
    
    // Search functionality
    document.getElementById('search').addEventListener('input', function(e) {
        const query = e.target.value.toLowerCase();
        filterIssues(query);
    });
    
    // Queue item clicks
    document.querySelectorAll('.queue-item').forEach(item => {
        item.addEventListener('click', function() {
            const issueId = this.dataset.issueId;
            selectIssue(issueId);
        });
    });
}

function updateCurrentIssues() {
    // Update the current issues based on filters
    currentIssues = showClosedIssues ? allIssues : activeIssues;
    
    // Rebuild hierarchy for current issues
    hierarchy = buildHierarchy(currentIssues);
    
    // Re-render the graph and hierarchy
    renderGraph();
    renderHierarchy();
}

function buildHierarchy(issues) {
    const issueMap = {};
    for (const issue of issues) {
        issueMap[issue.id] = issue;
    }
    
    const hierarchy = { roots: [], children: {} };
    
    // Initialize children for all issues
    for (const issue of issues) {
        hierarchy.children[issue.id] = [];
    }
    
    // Build dependency tree using "blocks" relationships
    // If A blocks B, then B depends on A, so B should show A as its child (dependency)
    for (const issue of issues) {
        for (const dep of issue.dependencies || []) {
            if (dep.type === 'blocks') {
                const blockingIssue = dep.depends_on_id;
                // The current issue should be the parent (what we want to accomplish)
                // The blocking issue should be the child (what we need to do first)
                if (issue.id in hierarchy.children) {
                    hierarchy.children[issue.id].push(blockingIssue);
                }
            }
        }
    }
    
    // Find root issues (issues that no other issue depends on - these are end goals)
    for (const issue of issues) {
        let isRoot = true;
        
        // Check if any other issue depends on this issue
        for (const otherIssue of issues) {
            for (const dep of otherIssue.dependencies || []) {
                if (dep.type === 'blocks' && dep.depends_on_id === issue.id) {
                    isRoot = false;
                    break;
                }
            }
            if (!isRoot) break;
        }
        
        if (isRoot) {
            hierarchy.roots.push(issue.id);
        }
    }
    
    return hierarchy;
}

function toggleView() {
    const graphView = document.getElementById('graph-view');
    const hierarchyView = document.getElementById('hierarchy-view');
    const toggleBtn = document.getElementById('toggle-view');
    
    if (currentView === 'graph') {
        graphView.style.display = 'none';
        hierarchyView.style.display = 'flex';
        toggleBtn.textContent = 'Switch to Graph';
        currentView = 'hierarchy';
    } else {
        graphView.style.display = 'flex';
        hierarchyView.style.display = 'none';
        toggleBtn.textContent = 'Switch to Hierarchy';
        currentView = 'graph';
    }
}

// Graph visualization
function initializeGraph() {
    const svg = d3.select('#network-graph');
    const container = document.querySelector('.graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    svg.attr('width', width).attr('height', height);
    
    // Create arrow markers for dependencies
    svg.append('defs').selectAll('marker')
        .data(['blocks', 'related', 'parent-child', 'discovered-from'])
        .join('marker')
        .attr('id', d => `arrow-${d}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', d => {
            switch(d) {
                case 'blocks': return '#ef4444';
                case 'related': return '#3b82f6';
                case 'parent-child': return '#16a34a';
                case 'discovered-from': return '#8b5cf6';
                default: return '#6b7280';
            }
        });
    
    renderGraph();
}

function renderGraph() {
    const svg = d3.select('#network-graph');
    const container = document.querySelector('.graph-container');
    const width = container.clientWidth;
    const height = container.clientHeight;
    
    // Clear existing content
    svg.selectAll('g').remove();
    
    // Create graph data
    const nodes = currentIssues.map(issue => ({
        id: issue.id,
        title: issue.title,
        status: issue.status,
        priority: issue.priority || 0,
        ...issue
    }));
    
    const links = [];
    const nodeIds = new Set(nodes.map(n => n.id));
    
    currentIssues.forEach(issue => {
        issue.dependencies?.forEach(dep => {
            // Only create links between nodes that exist in the current view
            if (nodeIds.has(dep.depends_on_id) && nodeIds.has(issue.id)) {
                links.push({
                    source: dep.depends_on_id,
                    target: issue.id,
                    type: dep.type
                });
            }
        });
    });
    
    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));
    
    // Create groups for links and nodes
    const g = svg.append('g');
    const linkGroup = g.append('g').attr('class', 'links');
    const nodeGroup = g.append('g').attr('class', 'nodes');
    
    // Add zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });
    
    svg.call(zoom);
    
    // Create links
    const link = linkGroup.selectAll('.link')
        .data(links)
        .join('line')
        .attr('class', d => `link ${d.type}`)
        .attr('marker-end', d => `url(#arrow-${d.type})`);
    
    // Create nodes
    const node = nodeGroup.selectAll('.node')
        .data(nodes)
        .join('circle')
        .attr('class', d => `node ${d.status} ${d.issue_type}`)
        .attr('r', d => 8 + (4 - d.priority) * 2)
        .on('click', function(event, d) {
            selectIssue(d.id);
        })
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // Add issue type symbols inside nodes
    const typeSymbol = nodeGroup.selectAll('.node-type-icon')
        .data(nodes)
        .join('text')
        .attr('class', 'node-type-icon')
        .text(d => getIssueTypeSymbol(d.issue_type))
        .attr('dy', 4);
    
    // Add labels below nodes
    const label = nodeGroup.selectAll('.node-label')
        .data(nodes)
        .join('text')
        .attr('class', 'node-label')
        .text(d => d.id)
        .attr('dy', 25);
    
    // Update positions on simulation tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
        
        typeSymbol
            .attr('x', d => d.x)
            .attr('y', d => d.y);
        
        label
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    });
    
    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
    
    // Initial visibility update
    updateGraphVisibility();
}

function updateGraphVisibility() {
    const svg = d3.select('#network-graph');
    
    svg.selectAll('.link').classed('hidden', function(d) {
        if (showAllDependencies) return false;
        return d.type !== 'blocks';
    });
}

function selectIssue(issueId) {
    selectedIssue = issueId;
    const issue = allIssues.find(i => i.id === issueId);
    
    if (!issue) return;
    
    // Update UI
    document.querySelectorAll('.queue-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.issueId === issueId);
    });
    
    // Update graph selection
    d3.selectAll('.node').classed('selected', d => d.id === issueId);
    
    // Update details panel
    updateIssueDetails(issue);
    
    // Highlight dependency chain
    highlightDependencyChain(issueId);
}

function updateIssueDetails(issue) {
    const detailsPanel = document.getElementById('issue-details');
    
    const html = `
        <h3>Issue Details</h3>
        <div class="issue-detail-content">
            <h4>${issue.title}</h4>
            <div class="detail-row">
                <span class="label">ID:</span>
                <span class="value">${issue.id}</span>
            </div>
            <div class="detail-row">
                <span class="label">Status:</span>
                <span class="value status-badge ${issue.status}">${issue.status.replace('_', ' ')}</span>
            </div>
            <div class="detail-row">
                <span class="label">Priority:</span>
                <span class="value priority priority-${issue.priority || 0}">P${issue.priority || 0}</span>
            </div>
            ${issue.description ? `
            <div class="detail-row">
                <span class="label">Description:</span>
                <span class="value">${issue.description}</span>
            </div>` : ''}
            ${issue.design ? `
            <div class="detail-row">
                <span class="label">Design:</span>
                <span class="value">${issue.design}</span>
            </div>` : ''}
            ${issue.dependencies && issue.dependencies.length > 0 ? `
            <div class="detail-row">
                <span class="label">Dependencies:</span>
                <div class="dependencies">
                    ${issue.dependencies.map(dep => `
                        <div class="dependency ${dep.type}">
                            ${dep.type}: ${dep.depends_on_id}
                        </div>
                    `).join('')}
                </div>
            </div>` : ''}
        </div>
    `;
    
    detailsPanel.innerHTML = html;
}

function highlightDependencyChain(issueId) {
    // Reset all highlights
    d3.selectAll('.node').classed('highlighted', false);
    d3.selectAll('.link').classed('highlighted', false);
    
    // Find all related nodes and links (only among visible nodes)
    const visibleNodeIds = new Set();
    d3.selectAll('.node').each(d => visibleNodeIds.add(d.id));
    
    const relatedNodes = new Set([issueId]);
    const relatedLinks = new Set();
    
    // Find dependencies (what this issue depends on)
    const issue = allIssues.find(i => i.id === issueId);
    if (issue && issue.dependencies) {
        issue.dependencies.forEach(dep => {
            if (visibleNodeIds.has(dep.depends_on_id)) {
                relatedNodes.add(dep.depends_on_id);
                relatedLinks.add(`${dep.depends_on_id}-${issueId}`);
            }
        });
    }
    
    // Find dependents (what depends on this issue)
    allIssues.forEach(otherIssue => {
        if (otherIssue.dependencies && visibleNodeIds.has(otherIssue.id)) {
            otherIssue.dependencies.forEach(dep => {
                if (dep.depends_on_id === issueId && visibleNodeIds.has(issueId)) {
                    relatedNodes.add(otherIssue.id);
                    relatedLinks.add(`${issueId}-${otherIssue.id}`);
                }
            });
        }
    });
    
    // Apply highlights only to visible nodes
    d3.selectAll('.node').classed('highlighted', d => relatedNodes.has(d.id));
    d3.selectAll('.link').classed('highlighted', d => 
        relatedLinks.has(`${d.source.id}-${d.target.id}`) ||
        relatedLinks.has(`${d.target.id}-${d.source.id}`)
    );
}

// Hierarchy view
function renderHierarchy() {
    const container = document.getElementById('hierarchy-tree');
    
    if (!hierarchy.roots || hierarchy.roots.length === 0) {
        container.innerHTML = '<p class="placeholder">No hierarchy found. Issues may not have parent-child relationships.</p>';
        return;
    }
    
    const html = hierarchy.roots.map(rootId => renderTreeNode(rootId, 0)).join('');
    container.innerHTML = html;
    
    // Add click handlers
    container.querySelectorAll('.tree-node-content').forEach(node => {
        node.addEventListener('click', function() {
            const issueId = this.dataset.issueId;
            selectIssue(issueId);
        });
    });
}

function renderTreeNode(issueId, depth) {
    const issue = allIssues.find(i => i.id === issueId);
    if (!issue) return '';
    
    const children = hierarchy.children[issueId] || [];
    const childrenHtml = children.map(childId => renderTreeNode(childId, depth + 1)).join('');
    
    // Find the relationship type for non-root nodes
    let relationshipType = '';
    if (depth > 0) {
        // Look for dependency that brings this issue as a child
        for (const dep of issue.dependencies || []) {
            if (dep.type) {
                relationshipType = dep.type;
                break;
            }
        }
    }
    
    const relationshipTag = relationshipType ? 
        `<div class="relationship-tag ${relationshipType}">${relationshipType}</div>` : '';
    
    return `
        <div class="tree-node" style="margin-left: ${depth * 1.5}rem;">
            <div class="tree-node-content status-${issue.status}" data-issue-id="${issueId}">
                ${relationshipTag}
                <div class="tree-node-title">
                    <span class="issue-type-icon ${issue.issue_type}">${getIssueTypeIcon(issue.issue_type)}</span>
                    ${issue.title}
                </div>
                <div class="tree-node-meta">
                    <span class="status-badge ${issue.status}">${issue.status.replace('_', ' ')}</span>
                    <span class="priority priority-${issue.priority || 0}">P${issue.priority || 0}</span>
                    <span class="issue-id">${issueId}</span>
                </div>
            </div>
            ${childrenHtml}
        </div>
    `;
}

function filterIssues(query) {
    if (!query) {
        // Show all nodes and queue items
        d3.selectAll('.node').style('opacity', 1);
        document.querySelectorAll('.queue-item').forEach(item => {
            item.style.display = 'block';
        });
        return;
    }
    
    // Filter graph nodes
    d3.selectAll('.node').style('opacity', d => 
        d.title.toLowerCase().includes(query) || d.id.toLowerCase().includes(query) ? 1 : 0.2
    );
    
    // Filter queue items
    document.querySelectorAll('.queue-item').forEach(item => {
        const issueId = item.dataset.issueId;
        const issue = allIssues.find(i => i.id === issueId);
        const matches = issue && (
            issue.title.toLowerCase().includes(query) || 
            issue.id.toLowerCase().includes(query)
        );
        item.style.display = matches ? 'block' : 'none';
    });
}

// Handle window resize
window.addEventListener('resize', function() {
    if (currentView === 'graph') {
        setTimeout(initializeGraph, 100);
    }
});
import re
import os

# We will apply specific replacements for each known vulnerable pattern

def fix_index():
    with open("dashboard/templates/index.html", "r") as f:
        c = f.read()

    # 1. btn-record
    c = c.replace("document.getElementById('btn-record').insertAdjacentHTML('beforeend', '🛑 Stop Recording');", "document.getElementById('btn-record').textContent = '🛑 Stop Recording';")
    c = c.replace("document.getElementById('btn-record').insertAdjacentHTML('beforeend', '🎙️ Record Voice');", "document.getElementById('btn-record').textContent = '🎙️ Record Voice';")
    
    # 2. Extract feedback
    c = c.replace("btn.insertAdjacentHTML('beforeend', 'Processing...');", "btn.textContent = 'Processing...';")
    c = c.replace("feedback.insertAdjacentHTML('beforeend', `<span style=\"color: var(--accent-green);\">Extracted ${data.extracted.length} facts!</span>`;", "feedback.appendChild(el('span', {style: 'color: var(--accent-green);'}, `Extracted ${data.extracted.length} facts!`));")
    c = c.replace("feedback.insertAdjacentHTML('beforeend', `<span style=\"color: var(--accent-red);\">Error: ${err.message}</span>`);", "feedback.appendChild(el('span', {style: 'color: var(--accent-red);'}, `Error: ${err.message}`));")
    c = c.replace("btn.insertAdjacentHTML('beforeend', 'Extract & Populate Graph');", "btn.textContent = 'Extract & Populate Graph';")
    
    # 3. Alerts list
    c = c.replace("alertsList.insertAdjacentHTML('beforeend', '<span style=\"color: var(--text-muted)\">No alerts.</span>');", "alertsList.appendChild(el('span', {style: 'color: var(--text-muted)'}, 'No alerts.'));")
    alert_loop = """alertsList.insertAdjacentHTML('beforeend', `
                            <div class="alert-item alert-unhandled">
                                <div>
                                    <strong>[${escapeHTML(a.group.toUpperCase())}]</strong> ${escapeHTML(a.label)}
                                </div>
                                <button class="btn" onclick="resolveAlarm('${a.id}')">Mark as handled</button>
                            </div>
                        `);"""
    alert_safe = """const item = el('div', {className: 'alert-item alert-unhandled'}, [
                            el('div', {}, [
                                el('strong', {}, `[${a.group.toUpperCase()}]`),
                                ` ${a.label}`
                            ]),
                            el('button', {className: 'btn', 'data-id': a.id, onclick: function() { resolveAlarm(this.dataset.id); }}, 'Mark as handled')
                        ]);
                        alertsList.appendChild(item);"""
    c = c.replace(alert_loop, alert_safe)

    # 4. Meds
    c = c.replace("tbody.insertAdjacentHTML('beforeend', '<tr><td colspan=\"5\" style=\"color: var(--text-muted)\">No medications configured.</td></tr>');", 
                  "tbody.appendChild(el('tr', {}, el('td', {colSpan: '5', style: 'color: var(--text-muted)'}, 'No medications configured.')));")
    med_loop = """tbody.insertAdjacentHTML('beforeend', `
                            <tr>
                                <td>${escapeHTML(m.content)}</td>
                                <td>${escapeHTML(m.schedule || 'N/A')}</td>
                                <td><span class="status-badge status-${m.last_status || 'pending'}">${escapeHTML(m.last_status || 'pending')}</span></td>
                                <td>${m.last_confirmation ? new Date(m.last_confirmation * 1000).toLocaleTimeString() : '-'}</td>
                                <td>
                                    <button class="btn btn-sm" onclick="setMedStatus('${m.id}', 'confirmed')">Confirm</button>
                                    <button class="btn btn-sm" onclick="setMedStatus('${m.id}', 'snoozed')">Snooze</button>
                                </td>
                            </tr>
                        `);"""
    med_safe = """
                        const tr = el('tr', {}, [
                            el('td', {}, m.content),
                            el('td', {}, m.schedule || 'N/A'),
                            el('td', {}, el('span', {className: `status-badge status-${m.last_status || 'pending'}`}, m.last_status || 'pending')),
                            el('td', {}, m.last_confirmation ? new Date(m.last_confirmation * 1000).toLocaleTimeString() : '-'),
                            el('td', {}, [
                                el('button', {className: 'btn btn-sm', 'data-id': m.id, onclick: function() { setMedStatus(this.dataset.id, 'confirmed'); }}, 'Confirm'),
                                document.createTextNode(' '),
                                el('button', {className: 'btn btn-sm', 'data-id': m.id, onclick: function() { setMedStatus(this.dataset.id, 'snoozed'); }}, 'Snooze')
                            ])
                        ]);
                        tbody.appendChild(tr);"""
    c = c.replace(med_loop, med_safe)

    # 5. Report
    c = c.replace("btn.insertAdjacentHTML('beforeend', 'Generating...');", "btn.textContent = 'Generating...';")
    c = c.replace("content.insertAdjacentHTML('beforeend', marked.parse(data.report));", "content.style.whiteSpace = 'pre-wrap'; content.textContent = data.report;")
    c = c.replace("content.insertAdjacentHTML('beforeend', \"Error during generation.\");", "content.textContent = 'Error during generation.';")
    c = c.replace("btn.insertAdjacentHTML('beforeend', \"✨ Generate AI Report\");", "btn.textContent = '✨ Generate AI Report';")

    # 6. Pending
    c = c.replace("list.insertAdjacentHTML('beforeend', '<span style=\"color: var(--text-muted)\">No stories to review.</span>');", "list.appendChild(el('span', {style: 'color: var(--text-muted)'}, 'No stories to review.'));")
    pending_loop = """list.insertAdjacentHTML('beforeend', `
                        <div class="alert-item" style="border-left: 4px solid var(--accent-blue);">
                            <div style="width: 100%;">
                                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                                    <span class="status-badge" style="background: var(--accent-blue); color: white;">PROPOSED: ${escapeHTML(p.meta.proposed_type)}</span>
                                    <span style="color: var(--text-muted); font-size: 0.8rem;">Source: ${escapeHTML(p.meta.source || 'llm')}</span>
                                </div>
                                <div style="margin-bottom: 15px; font-size: 1.1rem;">
                                    ${escapeHTML(p.content)}
                                </div>
                                <div style="display: flex; gap: 10px;">
                                    <button class="btn" onclick="approveFact('${p.id}', true)" style="background: var(--accent-green); color: white; border: none;">Approve</button>
                                    <button class="btn" onclick="approveFact('${p.id}', false)" style="background: var(--bg-light);">Reject</button>
                                </div>
                            </div>
                        </div>
                    `);"""
    pending_safe = """
                    const item = el('div', {className: 'alert-item', style: 'border-left: 4px solid var(--accent-blue);'}, [
                        el('div', {style: 'width: 100%;'}, [
                            el('div', {style: 'display: flex; gap: 10px; margin-bottom: 10px;'}, [
                                el('span', {className: 'status-badge', style: 'background: var(--accent-blue); color: white;'}, `PROPOSED: ${p.meta.proposed_type}`),
                                el('span', {style: 'color: var(--text-muted); font-size: 0.8rem;'}, `Source: ${p.meta.source || 'llm'}`)
                            ]),
                            el('div', {style: 'margin-bottom: 15px; font-size: 1.1rem;'}, p.content),
                            el('div', {style: 'display: flex; gap: 10px;'}, [
                                el('button', {className: 'btn', style: 'background: var(--accent-green); color: white; border: none;', 'data-id': p.id, onclick: function() { approveFact(this.dataset.id, true); }}, 'Approve'),
                                el('button', {className: 'btn', style: 'background: var(--bg-light);', 'data-id': p.id, onclick: function() { approveFact(this.dataset.id, false); }}, 'Reject')
                            ])
                        ])
                    ]);
                    list.appendChild(item);"""
    c = c.replace(pending_loop, pending_safe)

    # 7. Timeline
    c = c.replace("list.insertAdjacentHTML('beforeend', '<span style=\"color: var(--text-muted)\">No timeline events yet.</span>');", "list.appendChild(el('span', {style: 'color: var(--text-muted)'}, 'No timeline events yet.'));")
    timeline_loop = """list.insertAdjacentHTML('beforeend', `
                        <div style="padding: 10px; border-bottom: 1px solid var(--border-light); display: flex; gap: 15px;">
                            <div style="font-weight: bold; width: 100px; color: var(--accent-blue); flex-shrink: 0;">${t.event_date || 'Past'}</div>
                            <div>${t.content}</div>
                        </div>
                    `);"""
    timeline_safe = """
                    const titem = el('div', {style: 'padding: 10px; border-bottom: 1px solid var(--border-light); display: flex; gap: 15px;'}, [
                        el('div', {style: 'font-weight: bold; width: 100px; color: var(--accent-blue); flex-shrink: 0;'}, t.event_date || 'Past'),
                        el('div', {}, t.content)
                    ]);
                    list.appendChild(titem);"""
    c = c.replace(timeline_loop, timeline_safe)

    with open("dashboard/templates/index.html", "w") as f:
        f.write(c)

def fix_patient():
    with open("dashboard/templates/patient.html", "r") as f:
        c = f.read()

    # diary btn
    c = c.replace("document.getElementById('btn-diary').insertAdjacentHTML('beforeend', '📖 Raccontami');", "document.getElementById('btn-diary').textContent = '📖 Raccontami';")
    
    # today list empty
    c = c.replace("itemsContainer.insertAdjacentHTML('beforeend', '<div style=\"text-align: center; color: #595959; font-size: 1.2rem; padding: 20px;\">' + \n                        (currentLang === 'it' ? 'Nessun evento per oggi.' : 'No events for today.') + \n                        '</div>');", 
                  "itemsContainer.appendChild(el('div', {style: 'text-align: center; color: #595959; font-size: 1.2rem; padding: 20px;'}, currentLang === 'it' ? 'Nessun evento per oggi.' : 'No events for today.'));")
    
    # today item loop
    today_loop = """div.insertAdjacentHTML('beforeend', `
                        <div style="display:flex; align-items:center;">
                            <span class="today-time">${item.time}</span> 
                            <span style="margin: 0 10px;">${icon}</span> 
                            <strong>${escapeHTML(item.title)}</strong>
                        </div>
                        <div style="margin-left: 70px; font-size: 0.9rem; color: #666;">
                            ${escapeHTML(item.description)}
                        </div>
                    `);"""
    today_safe = """
                    const itemRow = el('div', {style: 'display:flex; align-items:center;'}, [
                        el('span', {className: 'today-time'}, item.time),
                        el('span', {style: 'margin: 0 10px;'}, icon),
                        el('strong', {}, item.title)
                    ]);
                    const itemDesc = el('div', {style: 'margin-left: 70px; font-size: 0.9rem; color: #666;'}, item.description);
                    div.appendChild(itemRow);
                    div.appendChild(itemDesc);"""
    c = c.replace(today_loop, today_safe)

    with open("dashboard/templates/patient.html", "w") as f:
        f.write(c)

def fix_judges():
    with open("dashboard/templates/judges.html", "r") as f:
        c = f.read()
    
    c = c.replace("tbody.insertAdjacentHTML('beforeend', '<tr><td colspan=\"5\" style=\"text-align: center; color: var(--text-muted);\">not measured yet</td></tr>');", 
                  "tbody.appendChild(el('tr', {}, el('td', {colSpan: '5', style: 'text-align: center; color: var(--text-muted);'}, 'not measured yet')));")
    c = c.replace("document.getElementById('metrics-body').insertAdjacentHTML('beforeend', '<tr><td colspan=\"5\" style=\"text-align: center; color: var(--danger);\">Failed to load metrics</td></tr>');",
                  "document.getElementById('metrics-body').appendChild(el('tr', {}, el('td', {colSpan: '5', style: 'text-align: center; color: var(--danger);'}, 'Failed to load metrics')));")
    
    metrics_loop1 = """tbody.insertAdjacentHTML('beforeend', `
                            <tr>
                                <td style="font-weight: 500;">${model}</td>
                                <td>${stats.calls}</td>
                                <td>${stats.avg_latency.toFixed(2)}ms</td>
                                <td>$${stats.cost.toFixed(4)}</td>
                                <td style="color: var(--accent-green)">100%</td>
                            </tr>
                        `);"""
    metrics_safe1 = """
                        const tr = el('tr', {}, [
                            el('td', {style: 'font-weight: 500;'}, model),
                            el('td', {}, stats.calls),
                            el('td', {}, `${stats.avg_latency.toFixed(2)}ms`),
                            el('td', {}, `$${stats.cost.toFixed(4)}`),
                            el('td', {style: 'color: var(--accent-green);'}, '100%')
                        ]);
                        tbody.appendChild(tr);"""
    c = c.replace(metrics_loop1, metrics_safe1)

    metrics_loop2 = """tbody.insertAdjacentHTML('beforeend', `
                        <tr style="background-color: #f8fafc; font-weight: bold;">
                            <td>Total Cost (Session)</td>
                            <td colspan="3"></td>
                            <td>$${d.total_cost.toFixed(4)}</td>
                        </tr>
                    `);"""
    metrics_safe2 = """
                    const trT = el('tr', {style: 'background-color: #f8fafc; font-weight: bold;'}, [
                        el('td', {}, 'Total Cost (Session)'),
                        el('td', {colSpan: '3'}),
                        el('td', {}, `$${d.total_cost.toFixed(4)}`)
                    ]);
                    tbody.appendChild(trT);"""
    c = c.replace(metrics_loop2, metrics_safe2)

    with open("dashboard/templates/judges.html", "w") as f:
        f.write(c)

def fix_story():
    with open("dashboard/templates/story.html", "r") as f:
        c = f.read()

    story_loop = """container.insertAdjacentHTML("beforeend", `
                        <div class="story-event">
                            <div class="story-date">${escapeHTML(item.event_date)}</div>
                            <div class="story-content">
                                ${escapeHTML(item.content)}
                            </div>
                        </div>
                    `);"""
    story_safe = """
                    const evt = el('div', {className: 'story-event'}, [
                        el('div', {className: 'story-date'}, item.event_date),
                        el('div', {className: 'story-content'}, item.content)
                    ]);
                    container.appendChild(evt);"""
    c = c.replace(story_loop, story_safe)

    with open("dashboard/templates/story.html", "w") as f:
        f.write(c)

def fix_graph_js():
    with open("dashboard/static/graph.js", "r") as f:
        c = f.read()
    
    # vis.js uses 'title' which can render HTML. 
    # To fix it, we provide title as a DOM element!
    # "title come elemento DOM con textContent"
    # we need to intercept where nodes are mapped.
    # In index.html or graph.js? Let's check graph.js
    
    c = c.replace("title: `<b>${escapeHTML(n.group)}</b><br>${escapeHTML(n.label)}`", 
                  "title: el('div', {}, [el('b', {}, n.group), el('br'), document.createTextNode(n.label)])")
                  
    with open("dashboard/static/graph.js", "w") as f:
        f.write(c)

fix_index()
fix_patient()
fix_judges()
fix_story()
fix_graph_js()


let allResources = [], allFunds = [], organizations = [];
let currentResourceId = null, editingResourceId = null, editingFundId = null, editingOrgId = null;
let currentSort = 'custom', draggedElement = null;

// ===== VIEW SWITCHING =====
function showView(view) {
    document.getElementById('viewResources').style.display = view === 'resources' ? 'flex' : 'none';
    document.getElementById('viewOrgs').style.display = view === 'orgs' ? 'flex' : 'none';
    document.getElementById('navResources').classList.toggle('active', view === 'resources');
    document.getElementById('navOrgs').classList.toggle('active', view === 'orgs');
    if (view === 'orgs') renderOrgsTable();
}

// ===== ORGS TABLE =====
function renderOrgsTable() {
    const tbody = document.getElementById('orgsTableBody');
    const sorted = [...organizations].sort((a, b) => a.name.localeCompare(b.name, 'uk'));

    if (!sorted.length) {
        tbody.innerHTML = '<tr><td colspan="3" class="orgs-empty">📋 Організації відсутні — натисніть "Додати організацію"</td></tr>';
        return;
    }

    tbody.innerHTML = sorted.map(org => {
        const realIdx = organizations.indexOf(org);
        const statusClass = { active: 'status-active', inactive: 'status-inactive', unknown: 'status-unknown' }[org.status || 'unknown'];
        return `
        <tr>
            <td>
                <div class="org-name-cell">${org.icon || '🏛️'} ${org.name}</div>
                ${org.description ? `<div class="org-sub">${org.description}</div>` : ''}
                ${org.contact ? `<div class="org-sub">📞 ${org.contact.replace(/\n/g,' | ')}</div>` : ''}
            </td>
            <td class="col-status-td">
                <select class="status-select ${statusClass}" onchange="updateOrgStatus(${realIdx}, this.value)">
                    <option value="active" ${(org.status||'unknown')==='active'?'selected':''}>✅ Активна</option>
                    <option value="inactive" ${(org.status||'unknown')==='inactive'?'selected':''}>❌ Неактивна</option>
                    <option value="unknown" ${(org.status||'unknown')==='unknown'?'selected':''}>❓ Невідомо</option>
                </select>
            </td>
            <td class="col-actions-td">
                <button class="icon-btn" onclick="openEditOrgModal(${realIdx})" title="Редагувати">✏️</button>
                <button class="icon-btn" onclick="deleteOrg(${realIdx})" title="Видалити">🗑️</button>
            </td>
        </tr>`;
    }).join('');
}

function updateOrgStatus(idx, status) {
    organizations[idx].status = status;
    saveOrganizationsToLocalStorage();
    document.querySelectorAll('.status-select').forEach(s => {
        s.className = 'status-select status-' + s.value;
    });
}

// ===== ORG MODALS =====
function openAddOrgModal() {
    editingOrgId = null;
    document.getElementById('orgModalTitle').textContent = 'Додати організацію';
    ['orgName','orgDescription','orgContact','orgIcon'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('orgStatus').value = 'active';
    document.getElementById('orgModal').classList.add('active');
}

function openEditOrgModal(idx) {
    const org = organizations[idx];
    editingOrgId = idx;
    document.getElementById('orgModalTitle').textContent = 'Редагувати організацію';
    document.getElementById('orgName').value = org.name;
    document.getElementById('orgDescription').value = org.description;
    document.getElementById('orgContact').value = org.contact || '';
    document.getElementById('orgIcon').value = org.icon || '';
    document.getElementById('orgStatus').value = org.status || 'unknown';
    document.getElementById('orgModal').classList.add('active');
}

function closeOrgModal() { document.getElementById('orgModal').classList.remove('active'); }

document.getElementById('orgForm').onsubmit = function(e) {
    e.preventDefault();
    const name = document.getElementById('orgName').value;
    const description = document.getElementById('orgDescription').value;
    const contact = document.getElementById('orgContact').value;
    const icon = document.getElementById('orgIcon').value || '🏛️';
    const status = document.getElementById('orgStatus').value;

    if (editingOrgId !== null) {
        organizations[editingOrgId] = { ...organizations[editingOrgId], name, description, contact, icon, status };
    } else {
        organizations.push({ id: Date.now(), name, description, contact, icon, status });
    }
    saveOrganizationsToLocalStorage();
    renderOrgsTable();
    closeOrgModal();
};

function deleteOrg(idx) {
    if (confirm('Видалити організацію?')) {
        organizations.splice(idx, 1);
        saveOrganizationsToLocalStorage();
        renderOrgsTable();
    }
}

function saveOrganizationsToLocalStorage() { localStorage.setItem('charity_organizations', JSON.stringify(organizations)); }
function loadOrganizationsFromLocalStorage() {
    const s = localStorage.getItem('charity_organizations');
    if (s) organizations = JSON.parse(s);
}

// ===== DATA =====
async function loadData() {
    try {
        const savedR = localStorage.getItem('charity_resources');
        const savedF = localStorage.getItem('charity_funds');
        if (savedR && savedF) {
            allResources = JSON.parse(savedR);
            allFunds = JSON.parse(savedF);
        } else {
            const backup = await loadBackupFromIndexedDB();
            if (backup) {
                allResources = backup.resources; allFunds = backup.funds;
                if (backup.resourceOrder) localStorage.setItem('resourceOrder', JSON.stringify(backup.resourceOrder));
                localStorage.setItem('charity_resources', JSON.stringify(allResources));
                localStorage.setItem('charity_funds', JSON.stringify(allFunds));
            } else {
                try {
                    const [rr, fr] = await Promise.all([fetch('/content/resources.json'), fetch('/content/funds.json')]);
                    allResources = (await rr.json()).resources || [];
                    allFunds = (await fr.json()).funds || [];
                    saveToLocalStorage();
                } catch { allResources = []; allFunds = []; }
            }
        }
        loadCustomOrder();
        renderResources();
    } catch (err) { console.error(err); }
}

async function saveToLocalStorage() {
    localStorage.setItem('charity_resources', JSON.stringify(allResources));
    localStorage.setItem('charity_funds', JSON.stringify(allFunds));
    await saveBackupToIndexedDB();
}

// ===== INDEXEDDB =====
const DB_NAME = 'CharityBackupDB', STORE_NAME = 'backups', MAX_BACKUPS = 10;

function openDB() {
    return new Promise((res, rej) => {
        const r = indexedDB.open(DB_NAME, 1);
        r.onupgradeneeded = e => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME))
                db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true }).createIndex('timestamp','timestamp',{unique:false});
        };
        r.onsuccess = () => res(r.result);
        r.onerror = () => rej(r.error);
    });
}

async function saveBackupToIndexedDB() {
    try {
        const db = await openDB();
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        store.add({ resources: allResources, funds: allFunds, resourceOrder: JSON.parse(localStorage.getItem('resourceOrder')||'{}'), timestamp: new Date().toISOString(), date: new Date().toLocaleString('uk-UA') });
        const all = await new Promise(res => { const r = store.getAll(); r.onsuccess = () => res(r.result); });
        if (all.length > MAX_BACKUPS) all.slice(0, all.length - MAX_BACKUPS).forEach(b => store.delete(b.id));
    } catch {}
}

async function loadBackupFromIndexedDB() {
    try {
        const db = await openDB();
        return new Promise(res => {
            const r = db.transaction(STORE_NAME,'readonly').objectStore(STORE_NAME).getAll();
            r.onsuccess = () => { const b = r.result; res(b.length ? b[b.length-1] : null); };
            r.onerror = () => res(null);
        });
    } catch { return null; }
}

async function getAllBackups() {
    try {
        const db = await openDB();
        return new Promise(res => {
            const r = db.transaction(STORE_NAME,'readonly').objectStore(STORE_NAME).getAll();
            r.onsuccess = () => res(r.result); r.onerror = () => res([]);
        });
    } catch { return []; }
}

async function restoreFromBackup(id) {
    try {
        const db = await openDB();
        return new Promise(res => {
            const r = db.transaction(STORE_NAME,'readonly').objectStore(STORE_NAME).get(id);
            r.onsuccess = () => {
                const b = r.result;
                if (b) {
                    allResources = b.resources; allFunds = b.funds;
                    if (b.resourceOrder) localStorage.setItem('resourceOrder', JSON.stringify(b.resourceOrder));
                    saveToLocalStorage(); loadCustomOrder(); renderResources();
                    currentResourceId = null;
                    document.getElementById('contentTitle').textContent = 'Оберіть ресурс';
                    document.getElementById('addFundBtn').style.display = 'none';
                    document.getElementById('fundsGrid').innerHTML = '<div class="empty-state"><div class="empty-state-icon">👈</div><div class="empty-state-text">Оберіть ресурс зі списку</div></div>';
                    alert('✅ Відновлено: ' + b.date); res(true);
                } else { alert('❌ Бекап не знайдено'); res(false); }
            };
            r.onerror = () => { alert('❌ Помилка'); res(false); };
        });
    } catch { return false; }
}

async function showBackupHistory() {
    const backups = await getAllBackups();
    if (!backups.length) { alert('📋 Немає бекапів'); return; }
    let msg = '📋 Бекапи:\n\n';
    backups.forEach((b,i) => { msg += `${i+1}. ${b.date}\n   Ресурсів: ${b.resources.length}, Фондів: ${b.funds.length}\n\n`; });
    const ch = prompt(msg + '\nНомер для відновлення (або 0):');
    if (ch && ch !== '0') {
        const idx = parseInt(ch)-1;
        if (idx >= 0 && idx < backups.length) { if (confirm('Замінити поточні дані?')) await restoreFromBackup(backups[idx].id); }
        else alert('❌ Невірний номер');
    }
}

setInterval(() => saveBackupToIndexedDB(), 30 * 60 * 1000);
window.addEventListener('beforeunload', () => saveBackupToIndexedDB());

// ===== SORTING =====
function applySorting() {
    currentSort = document.getElementById('sortSelect').value;
    let sorted = [...allResources];
    if (currentSort === 'az') sorted.sort((a,b) => a.name.localeCompare(b.name,'uk'));
    else if (currentSort === 'za') sorted.sort((a,b) => b.name.localeCompare(a.name,'uk'));
    else sorted.sort((a,b) => (a.order||0)-(b.order||0));
    displayResources(sorted);
}

function displayResources(resources) {
    const list = document.getElementById('resourcesList');
    list.innerHTML = '';
    resources.forEach((res, idx) => {
        const item = document.createElement('div');
        item.className = 'resource-item' + (currentResourceId === res.id ? ' active' : '');
        item.draggable = currentSort === 'custom';
        item.dataset.resourceId = res.id;
        item.dataset.index = idx;
        item.innerHTML = `
            <div class="resource-info">
                <div class="resource-name">${res.icon} ${res.name}</div>
                <div class="resource-desc">${res.description}</div>
            </div>
            <div class="resource-actions">
                <button class="icon-btn" onclick="event.stopPropagation(); openEditResourceModal('${res.id}')">✏️</button>
                <button class="icon-btn" onclick="event.stopPropagation(); deleteResource('${res.id}')">🗑️</button>
            </div>`;
        if (currentSort === 'custom') {
            item.addEventListener('dragstart', handleDragStart);
            item.addEventListener('dragover', handleDragOver);
            item.addEventListener('drop', handleDrop);
            item.addEventListener('dragend', handleDragEnd);
        }
        item.onclick = e => { if (!e.target.closest('.icon-btn')) showFunds(res); };
        list.appendChild(item);
    });
}

function renderResources() { applySorting(); }

// ===== DRAG =====
function handleDragStart(e) { draggedElement = this; this.classList.add('dragging'); e.dataTransfer.effectAllowed = 'move'; }
function handleDragOver(e) { e.preventDefault(); const t = e.target.closest('.resource-item'); if (t && t !== draggedElement) t.classList.add('drag-over'); return false; }
function handleDrop(e) {
    e.stopPropagation();
    const target = e.target.closest('.resource-item');
    if (draggedElement !== target && target) {
        const di = parseInt(draggedElement.dataset.index), ti = parseInt(target.dataset.index);
        const temp = allResources[di]; allResources.splice(di,1); allResources.splice(ti,0,temp);
        allResources.forEach((r,i) => r.order=i);
        saveCustomOrder(); displayResources(allResources);
    }
    return false;
}
function handleDragEnd() { this.classList.remove('dragging'); document.querySelectorAll('.resource-item').forEach(i => i.classList.remove('drag-over')); }
function saveCustomOrder() { const o={}; allResources.forEach((r,i)=>o[r.id]=i); localStorage.setItem('resourceOrder',JSON.stringify(o)); }
function loadCustomOrder() { const s=localStorage.getItem('resourceOrder'); if(s){try{const o=JSON.parse(s);allResources.forEach(r=>{if(o[r.id]!==undefined)r.order=o[r.id];});}catch{}} }

// ===== FUNDS =====
function showFunds(resource) {
    currentResourceId = resource.id;
    document.getElementById('contentTitle').textContent = `${resource.icon} ${resource.name}`;
    document.getElementById('addFundBtn').style.display = 'block';
    renderResources(); renderFunds();
}

function renderFunds() {
    const grid = document.getElementById('fundsGrid');
    const funds = allFunds.filter(f => f.resource_id === currentResourceId);
    if (!funds.length) {
        grid.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📋</div><div class="empty-state-text">Немає фондів</div><p>Натисніть "➕ Додати фонд"</p></div>`;
        return;
    }
    grid.innerHTML = funds.map((fund, i) => `
        <div class="fund-card">
            <div class="fund-header">
                <div class="fund-name">${fund.name}</div>
                <div class="fund-actions">
                    <button class="icon-btn" onclick="openEditFundModal(${i})">✏️</button>
                    <button class="icon-btn" onclick="deleteFund(${i})">🗑️</button>
                </div>
            </div>
            <div class="fund-contact">📞 ${fund.contact.replace(/\n/g,'<br>')}</div>
            <div class="fund-conditions">${fund.conditions}</div>
        </div>`).join('');
}

// ===== RESOURCE MODALS =====
function openAddResourceModal() {
    editingResourceId = null;
    document.getElementById('resourceModalTitle').textContent = 'Додати ресурс';
    ['resourceName','resourceDescription','resourceIcon'].forEach(id => document.getElementById(id).value='');
    document.getElementById('resourceModal').classList.add('active');
}

function openEditResourceModal(id) {
    editingResourceId = id;
    const r = allResources.find(x => x.id === id);
    document.getElementById('resourceModalTitle').textContent = 'Редагувати ресурс';
    document.getElementById('resourceName').value = r.name;
    document.getElementById('resourceDescription').value = r.description;
    document.getElementById('resourceIcon').value = r.icon;
    document.getElementById('resourceModal').classList.add('active');
}

function closeResourceModal() { document.getElementById('resourceModal').classList.remove('active'); }

document.getElementById('resourceForm').onsubmit = function(e) {
    e.preventDefault();
    const name = document.getElementById('resourceName').value;
    const description = document.getElementById('resourceDescription').value;
    const icon = document.getElementById('resourceIcon').value || '📦';
    if (editingResourceId) {
        const r = allResources.find(x => x.id === editingResourceId);
        r.name=name; r.description=description; r.icon=icon;
    } else {
        allResources.push({ id: Date.now().toString(), name, description, icon, order: allResources.length });
    }
    saveToLocalStorage(); renderResources(); closeResourceModal();
};

function deleteResource(id) {
    if (confirm('Видалити ресурс та всі його фонди?')) {
        allResources = allResources.filter(r => r.id !== id);
        allFunds = allFunds.filter(f => f.resource_id !== id);
        if (currentResourceId === id) {
            currentResourceId = null;
            document.getElementById('contentTitle').textContent = 'Оберіть ресурс';
            document.getElementById('addFundBtn').style.display = 'none';
            document.getElementById('fundsGrid').innerHTML = '<div class="empty-state"><div class="empty-state-icon">👈</div><div class="empty-state-text">Оберіть ресурс зі списку</div></div>';
        }
        saveToLocalStorage(); renderResources();
    }
}

// ===== FUND MODALS =====
function openAddFundModal() {
    if (!currentResourceId) { alert('Спочатку оберіть ресурс'); return; }
    editingFundId = null;
    document.getElementById('fundModalTitle').textContent = 'Додати фонд';
    ['fundName','fundContact','fundConditions'].forEach(id => document.getElementById(id).value='');
    document.getElementById('fundModal').classList.add('active');
}

function openEditFundModal(idx) {
    const funds = allFunds.filter(f => f.resource_id === currentResourceId);
    const fund = funds[idx];
    editingFundId = idx;
    document.getElementById('fundModalTitle').textContent = 'Редагувати фонд';
    document.getElementById('fundName').value = fund.name;
    document.getElementById('fundContact').value = fund.contact;
    document.getElementById('fundConditions').value = fund.conditions;
    document.getElementById('fundModal').classList.add('active');
}

function closeFundModal() { document.getElementById('fundModal').classList.remove('active'); }

document.getElementById('fundForm').onsubmit = function(e) {
    e.preventDefault();
    const name = document.getElementById('fundName').value;
    const contact = document.getElementById('fundContact').value;
    const conditions = document.getElementById('fundConditions').value;
    if (editingFundId !== null) {
        const funds = allFunds.filter(f => f.resource_id === currentResourceId);
        const fund = funds[editingFundId];
        fund.name=name; fund.contact=contact; fund.conditions=conditions;
    } else {
        allFunds.push({ resource_id: currentResourceId, name, contact, conditions });
    }
    saveToLocalStorage(); renderFunds(); closeFundModal();
};

function deleteFund(idx) {
    if (confirm('Видалити фонд?')) {
        const funds = allFunds.filter(f => f.resource_id === currentResourceId);
        allFunds.splice(allFunds.indexOf(funds[idx]), 1);
        saveToLocalStorage(); renderFunds();
    }
}

// ===== EXPORT / IMPORT =====
function exportData() {
    const blob = new Blob([JSON.stringify({ resources: allResources, funds: allFunds, organizations },null,2)],{type:'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href=url; a.download=`charity_backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click(); URL.revokeObjectURL(url);
}

function importData() {
    const input = document.createElement('input');
    input.type='file'; input.accept='.json';
    input.onchange = e => {
        const file = e.target.files[0]; if (!file) return;
        const reader = new FileReader();
        reader.onload = ev => {
            try {
                const data = JSON.parse(ev.target.result);
                if (data.resources && data.funds) {
                    if (confirm('Замінити всі поточні дані?')) {
                        allResources=data.resources; allFunds=data.funds;
                        if (data.organizations) { organizations=data.organizations; saveOrganizationsToLocalStorage(); }
                        saveToLocalStorage(); renderResources();
                        currentResourceId=null;
                        document.getElementById('contentTitle').textContent='Оберіть ресурс';
                        document.getElementById('addFundBtn').style.display='none';
                        document.getElementById('fundsGrid').innerHTML='<div class="empty-state"><div class="empty-state-icon">👈</div><div class="empty-state-text">Оберіть ресурс зі списку</div></div>';
                        alert('✅ Дані імпортовано!');
                    }
                } else alert('❌ Невірний формат');
            } catch(err) { alert('❌ Помилка: ' + err.message); }
        };
        reader.readAsText(file);
    };
    input.click();
}

window.onclick = e => { if (e.target.classList.contains('modal')) e.target.classList.remove('active'); };

// ===== INIT =====
loadData();
loadOrganizationsFromLocalStorage();

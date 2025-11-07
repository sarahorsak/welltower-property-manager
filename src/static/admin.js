async function loadProps(){
  const res = await fetch('/properties');
  const props = await res.json();
  const sel = document.getElementById('unit-property-id');
  const rrsel = document.getElementById('rr-prop');
  const urProp = document.getElementById('ur-prop');
  const kpiProp = document.getElementById('kpi-prop');
  const kpiMoveProp = document.getElementById('kpi-move-prop');
  const kpiOccProp = document.getElementById('kpi-occ-prop');
  const usProp = document.getElementById('us-prop');
  sel.innerHTML = '';
  rrsel.innerHTML = '';
  if(urProp) urProp.innerHTML = '';
  if(usProp) usProp.innerHTML = '';
  if(kpiProp) kpiProp.innerHTML = '';
  if(kpiMoveProp) kpiMoveProp.innerHTML = '';
  if(kpiOccProp) kpiOccProp.innerHTML = '';
  // Add a placeholder option
  const placeholder = document.createElement('option');
  placeholder.value = '';
  placeholder.textContent = '-- select property --';
  placeholder.disabled = true;
  placeholder.selected = true;
  sel.appendChild(placeholder);
  props.forEach(p=>{
    const o = document.createElement('option'); o.value = p.id; o.textContent = `${p.id} - ${p.name}`;
    sel.appendChild(o);
    const o2 = o.cloneNode(true);
    rrsel.appendChild(o2);
    if(urProp) urProp.appendChild(o.cloneNode(true));
    if(usProp) usProp.appendChild(o.cloneNode(true));
    if(kpiProp) kpiProp.appendChild(o.cloneNode(true));
    if(kpiMoveProp) kpiMoveProp.appendChild(o.cloneNode(true));
    if(kpiOccProp) kpiOccProp.appendChild(o.cloneNode(true));
  });

  // If only one property, auto-select it and trigger change to show units
  if (sel && sel.options.length === 2) { // 1 placeholder + 1 property
    sel.selectedIndex = 1;
    sel.dispatchEvent(new Event('change'));
  }
  // If more than one property, keep previous logic
  if (sel && sel.options.length > 2 && sel.selectedIndex === 0) {
    sel.selectedIndex = 1;
    sel.dispatchEvent(new Event('change'));
  }
}

// Fetch move-in/move-out counts for a property and date range
async function viewKpiMoveCounts() {
  const propSel = document.getElementById('kpi-move-prop');
  const start = document.getElementById('kpi-move-start').value;
  const end = document.getElementById('kpi-move-end').value;
  const pid = propSel && propSel.value;
  if (!pid || !start || !end) return alert('property, start, and end are required');
  const url = `/reports/kpi-move?property_id=${encodeURIComponent(pid)}&start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`;
  const res = await fetch(url);
  const pre = document.getElementById('kpi-move-output');
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    pre.textContent = `Error: ${err.error || res.statusText}`;
    return;
  }
  const j = await res.json();
  pre.textContent = JSON.stringify(j, null, 2);
}

// Fetch occupancy rate for a property and month (YYYY-MM)
async function viewKpiOccupancyRate() {
  const propSel = document.getElementById('kpi-occ-prop');
  const month = document.getElementById('kpi-occ-month').value;
  const pid = propSel && propSel.value;
  if (!pid || !month) return alert('property and month are required');
  // month input is YYYY-MM, convert to year and month
  const [year, mon] = month.split('-');
  if (!year || !mon) return alert('Invalid month');
  const url = `/reports/kpi-occupancy?property_id=${encodeURIComponent(pid)}&year=${encodeURIComponent(year)}&month=${encodeURIComponent(mon)}`;
  const res = await fetch(url);
  const pre = document.getElementById('kpi-occ-output');
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    pre.textContent = `Error: ${err.error || res.statusText}`;
    return;
  }
  const j = await res.json();

  pre.textContent = JSON.stringify(j, null, 2);
}

// Wrap top-level await code in an async function
async function initializeAdminPage() {
  // populate move-in related selects
  const miUnitSel = document.getElementById('mi-unit-id');
  const miResidentSel = document.getElementById('mi-resident-id');
  miUnitSel.innerHTML = '';
  miResidentSel.innerHTML = '';
  // If a property is selected in the unit-property-id select, fetch units for that property
  const propSel = document.getElementById('unit-property-id');
  let unitsUrl = '/units';
  if(propSel && propSel.value) unitsUrl = `/units?property_id=${encodeURIComponent(propSel.value)}`;
  const unitsRes = await fetch(unitsUrl);
  const units = await unitsRes.json();
  // Show property-prefixed unit label (e.g. P1-U01) so property id + unit number are visible
  units.forEach(u=>{ const o = document.createElement('option'); o.value = u.id; const propId = u.property_id || propSel && propSel.value || ''; o.textContent = `P${propId}-${u.unit_number}`; miUnitSel.appendChild(o); });
  const residentsRes = await fetch('/residents');
  const residents = await residentsRes.json();
  residents.forEach(r=>{ const o = document.createElement('option'); o.value = r.id; o.textContent = `${r.id} - ${r.first_name} ${r.last_name}`; miResidentSel.appendChild(o); });

  // Auto-select first property and trigger change to populate units
  if (propSel && propSel.options.length > 1) {
    propSel.selectedIndex = 1; // skip placeholder
    propSel.dispatchEvent(new Event('change'));
  }

  // when the property selection changes, reload units for move-in
  if(propSel) {
    propSel.addEventListener('change', async ()=>{
      const miUnitSel = document.getElementById('mi-unit-id');
      miUnitSel.innerHTML = '';
      const selected = propSel.value;
      if(!selected) return;
      const unitsRes = await fetch(`/units?property_id=${encodeURIComponent(selected)}`);
      const units = await unitsRes.json();
      units.forEach(u=>{ const o = document.createElement('option'); o.value = u.id; const propId = u.property_id || selected; o.textContent = `P${propId}-${u.unit_number}`; miUnitSel.appendChild(o); });
      // Also populate the unit selector used by Unit Rent History (if present)
      const urUnit = document.getElementById('ur-unit-id');
      if(urUnit){ urUnit.innerHTML = ''; units.forEach(u=>{ const o = document.createElement('option'); o.value = u.id; const propId = u.property_id || selected; o.textContent = `P${propId}-${u.unit_number}`; urUnit.appendChild(o); }); }
      // Also populate the unit selector used by Unit Status (if present)
      const usUnit = document.getElementById('us-unit-id');
      if(usUnit){ usUnit.innerHTML = ''; units.forEach(u=>{ const o = document.createElement('option'); o.value = u.id; const propId = u.property_id || selected; o.textContent = `P${propId}-${u.unit_number}`; usUnit.appendChild(o); }); }
    });
  }

  // after loading props/units/residents, also load occupancies
  await loadOccupancies();
}

// Call the initializer on page load
window.addEventListener('DOMContentLoaded', initializeAdminPage);

// Load occupancies and populate selects used for move-out, rent-change, and history
async function loadOccupancies(){
  const res = await fetch('/occupancies');
  if(!res.ok) return;
  const occs = await res.json();
  const moSel = document.getElementById('mo-occupancy-id');
  const rcSel = document.getElementById('rc-occupancy-id');
  if(moSel) moSel.innerHTML = '';
  if(rcSel) rcSel.innerHTML = '';
  occs.forEach(o=>{
    const text = `${o.id} | unit:${o.unit_number || o.unit_id} | ${o.resident_name || o.resident_id} | in:${o.move_in_date}`;
    const opt = document.createElement('option'); opt.value = o.id; opt.textContent = text;
    if(moSel) moSel.appendChild(opt.cloneNode(true));
    if(rcSel) rcSel.appendChild(opt.cloneNode(true));
  });
}

async function addProperty(e){
  e.preventDefault();
  const name = document.getElementById('property-name').value.trim();
  if(!name) return alert('name required');
  const res = await fetch('/properties', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({name}) });
  const j = await res.json();
  document.getElementById('property-msg').textContent = res.ok ? `Created property ${j.id}` : `Error: ${j.error||'failed'}`;
  if(res.ok){
    document.getElementById('property-name').value='';
    await loadProps();
    await initializeAdminPage();
  }
}

async function createUnit(){
  const pid = document.getElementById('unit-property-id').value.trim();
  const num = document.getElementById('unit-number').value.trim();
  if(!pid || !num) return alert('property id and unit number required');
  const res = await fetch('/units', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({property_id: parseInt(pid), unit_number: num}) });
  const j = await res.json();
  document.getElementById('unit-msg').textContent = res.ok ? `Created unit ${j.id}` : `Error: ${j.error || 'failed'}`;
  if(res.ok){
    document.getElementById('unit-number').value='';
    await loadProps();
    await initializeAdminPage();
  }
}

async function createResident(){
  const first = document.getElementById('resident-first').value.trim();
  const last = document.getElementById('resident-last').value.trim();
  if(!first || !last) return alert('first and last required');
  const res = await fetch('/residents', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({first_name:first, last_name:last}) });
  const j = await res.json();
  document.getElementById('resident-msg').textContent = res.ok ? `Created resident ${j.id}` : `Error: ${j.error || 'failed'}`;
  if(res.ok){
    document.getElementById('resident-first').value='';
    document.getElementById('resident-last').value='';
    await loadProps();
    await initializeAdminPage();
  }
}

async function moveIn(){
  const resident_id = parseInt(document.getElementById('mi-resident-id').value);
  const unit_id = parseInt(document.getElementById('mi-unit-id').value);
  const move_in_date = document.getElementById('mi-date').value;
  const initial_rent = parseFloat(document.getElementById('mi-rent').value);
  if(!resident_id || !unit_id || !move_in_date || !initial_rent) return alert('all move-in fields required');
  const res = await fetch('/occupancy/move-in', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({resident_id, unit_id, move_in_date, initial_rent}) });
  const j = await res.json();
  document.getElementById('mi-msg').textContent = res.ok ? `Move-in created occ ${j.occupancy_id}` : `Error: ${j.error || 'failed'}`;
}

async function moveOut(){
  const occ_id = parseInt(document.getElementById('mo-occupancy-id').value);
  const move_out_date = document.getElementById('mo-date').value;
  if(!occ_id || !move_out_date) return alert('occupancy id and date required');
  const res = await fetch(`/occupancy/${occ_id}/move-out`, { method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({move_out_date}) });
  const j = await res.json();
  document.getElementById('mo-msg').textContent = res.ok ? `Moved out` : `Error: ${j.error || 'failed'}`;
  if(res.ok){ await loadOccupancies(); }
}

async function rentChange(){
  const occ_id = parseInt(document.getElementById('rc-occupancy-id').value);
  const effective_date = document.getElementById('rc-date').value;
  const new_rent = parseFloat(document.getElementById('rc-new-rent').value);
  if(!occ_id || !effective_date || !new_rent) return alert('occupancy, date and new rent required');
  const res = await fetch(`/occupancy/${occ_id}/rent-change`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({new_rent, effective_date}) });
  const j = await res.json();
  document.getElementById('rc-msg').textContent = res.ok ? `Rent change logged ${j.rent_id}` : `Error: ${j.error || 'failed'}`;
  if(res.ok){ await loadOccupancies(); }
}

async function viewRentRoll(){
  const pid = document.getElementById('rr-prop').value.trim();
  const start = document.getElementById('rr-start').value;
  const end = document.getElementById('rr-end').value;
  if(!pid || !start || !end) return alert('property, start and end are required');
  const res = await fetch(`/reports/rent-roll?property_id=${encodeURIComponent(pid)}&start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`);
  const j = await res.json();
  document.getElementById('rr-output').textContent = JSON.stringify(j, null, 2);
}

// KPIs: fetch and render KPI JSON for a property + date range
async function viewKpis(){
  const pid = document.getElementById('kpi-prop').value.trim() || document.getElementById('rr-prop').value.trim();
  const start = document.getElementById('kpi-start').value;
  const end = document.getElementById('kpi-end').value;
  if(!pid || !start || !end) return alert('property, start and end are required for KPIs');
  const url = `/reports/kpi?property_id=${encodeURIComponent(pid)}&start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`;
  const res = await fetch(url);
  if(!res.ok){
    const err = await res.json().catch(()=>({error: res.statusText}));
    document.getElementById('kpi-output').textContent = `Error: ${err.error||res.statusText}`;
    return;
  }
  const j = await res.json();
  // Pretty-print JSON and also provide a simple table-like output for readability
  const pre = document.getElementById('kpi-output');
  pre.textContent = JSON.stringify(j, null, 2);
}

function downloadCSV(){
  const pid = document.getElementById('rr-prop').value.trim();
  const start = document.getElementById('rr-start').value;
  const end = document.getElementById('rr-end').value;
  if(!pid || !start || !end) return alert('property, start and end are required');
  const url = `/reports/rent-roll?property_id=${encodeURIComponent(pid)}&start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}&format=csv`;
  window.open(url, '_blank');
}

async function viewHistory(){
  // occupancy history view removed; use Unit Rent History instead
  alert('Occupancy rent history UI has been removed. Use Unit Rent History to view rents across occupancies.');
}

// View aggregated unit rents (new)
async function viewUnitRents(){
  const unitSel = document.getElementById('ur-unit-id');
  const unitId = unitSel && unitSel.value;
  if(!unitId) return alert('Select a unit');
  const res = await fetch(`/units/${encodeURIComponent(unitId)}/rents`);
  if(!res.ok){ const err = await res.json().catch(()=>({error:res.statusText})); document.getElementById('ur-output').textContent = `Error: ${err.error||res.statusText}`; return; }
  const j = await res.json();
  document.getElementById('ur-output').textContent = JSON.stringify(j, null, 2);
}

// Set a unit status (POST to /units/<id>/status)
async function setUnitStatus(){
  const unitId = document.getElementById('us-unit-id').value;
  const status = document.getElementById('us-status').value;
  const start_date = document.getElementById('us-date').value;
  if(!unitId || !status || !start_date) return alert('unit, status and start date are required');
  const res = await fetch(`/units/${encodeURIComponent(unitId)}/status`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({status, start_date}) });
  const j = await res.json().catch(()=>({error: 'unexpected'}));
  document.getElementById('us-output').textContent = res.ok ? `Status set` : `Error: ${j.error||'failed'}`;
  if(res.ok){
    // refresh status display
    await viewUnitStatus();
  }
}

// View unit status (GET /units/<id>/status?date=...)
async function viewUnitStatus(){
  const unitId = document.getElementById('us-unit-id').value;
  const qdate = document.getElementById('us-date').value; // optional
  if(!unitId) return alert('Select a unit');
  let url = `/units/${encodeURIComponent(unitId)}/status`;
  if(qdate) url += `?date=${encodeURIComponent(qdate)}`;
  const res = await fetch(url);
  if(!res.ok){ const err = await res.json().catch(()=>({error:res.statusText})); document.getElementById('us-output').textContent = `Error: ${err.error||res.statusText}`; return; }
  const j = await res.json();
  document.getElementById('us-output').textContent = JSON.stringify(j, null, 2);
}

document.addEventListener('DOMContentLoaded', ()=>{
  loadProps();
  document.getElementById('property-form').addEventListener('submit', addProperty);
  document.getElementById('refresh').addEventListener('click', loadProps);
  document.getElementById('create-unit-btn').addEventListener('click', createUnit);
  document.getElementById('create-resident-btn').addEventListener('click', createResident);
  document.getElementById('move-in-btn').addEventListener('click', moveIn);
  document.getElementById('move-out-btn').addEventListener('click', moveOut);
  document.getElementById('rent-change-btn').addEventListener('click', rentChange);
  document.getElementById('rr-view-json').addEventListener('click', viewRentRoll);
  document.getElementById('rr-download-csv').addEventListener('click', downloadCSV);
  // KPI move-in/out counts button
  const kpiMoveBtn = document.getElementById('kpi-move-btn');
  if(kpiMoveBtn) kpiMoveBtn.addEventListener('click', viewKpiMoveCounts);
  // KPI occupancy rate button
  const kpiOccBtn = document.getElementById('kpi-occ-btn');
  if(kpiOccBtn) kpiOccBtn.addEventListener('click', viewKpiOccupancyRate);
  // (Legacy) KPIs button (if present)
  const kpiBtn = document.getElementById('kpi-view-btn');
  if(kpiBtn) kpiBtn.addEventListener('click', viewKpis);
  const urBtn = document.getElementById('ur-view-btn');
  if(urBtn) urBtn.addEventListener('click', viewUnitRents);
  const usSetBtn = document.getElementById('us-set-btn');
  if(usSetBtn) usSetBtn.addEventListener('click', setUnitStatus);
  const usGetBtn = document.getElementById('us-get-btn');
  if(usGetBtn) usGetBtn.addEventListener('click', viewUnitStatus);
  // occupancy history UI removed; no binding for hist-view-btn
  // when the Unit-Rent property selector changes, populate its unit list as well
  const urProp = document.getElementById('ur-prop');
  if(urProp){
    urProp.addEventListener('change', async ()=>{
      const pid = urProp.value;
      const urUnit = document.getElementById('ur-unit-id');
      if(!pid || !urUnit) return;
      urUnit.innerHTML = '';
      const unitsRes = await fetch(`/units?property_id=${encodeURIComponent(pid)}`);
      const units = await unitsRes.json();
      units.forEach(u=>{ const o = document.createElement('option'); o.value = u.id; o.textContent = `P${u.property_id || pid}-${u.unit_number}`; urUnit.appendChild(o); });
    });
  }
  // Also wire up us-prop to update us-unit-id
  const usProp = document.getElementById('us-prop');
  if(usProp){
    usProp.addEventListener('change', async ()=>{
      const pid = usProp.value;
      const usUnit = document.getElementById('us-unit-id');
      if(!pid || !usUnit) return;
      usUnit.innerHTML = '';
      const unitsRes = await fetch(`/units?property_id=${encodeURIComponent(pid)}`);
      const units = await unitsRes.json();
      units.forEach(u=>{ const o = document.createElement('option'); o.value = u.id; o.textContent = `P${u.property_id || pid}-${u.unit_number}`; usUnit.appendChild(o); });
    });
  }
});

"use strict";
const $ = s => document.querySelector(s);
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeURL = value => { try { const u = new URL(value); return u.protocol === "https:" ? escapeHTML(u.href) : ""; } catch { return ""; } };
const state = {index:null, day:null, selected:null, hidden:false, team:"", request:0};
const scheduleState = {data:null, pending:null, selected:null};
const standingsState = {data:null,pending:null,view:"conference",groups:{conference:null,division:null}};
let floatingBox = null;
const playerCache = new Map();
const playerSizes = new ResizeObserver(entries=>{
  for (const {target} of entries) sizePlayerPanels(target);
});
const dateFormat = (date, options) => new Intl.DateTimeFormat("en-IE",options).format(new Date(`${date}T12:00:00Z`));
const formatFull = date => dateFormat(date,{weekday:"long",day:"numeric",month:"long",year:"numeric"});
const outbound = (url,text,cls="") => `<a class="${cls}" href="${safeURL(url)}" target="_blank" rel="noopener noreferrer">${text}</a>`;

async function readJSON(path) {
  const response = await fetch(path, {cache:"no-cache"});
  if (!response.ok) throw new Error(`Unable to load archive (${response.status}).`);
  return response.json();
}
function notify(text) { $("#notice").textContent=text; $("#notice").hidden=!text; }

function renderDates() {
  const recent = state.index.days.slice(0,7);
  $("#dates").innerHTML = recent.map(d => `<button type="button" class="date-button" data-date="${d.date}" aria-pressed="${d.date===state.selected}"><small>${dateFormat(d.date,{weekday:"short"})}</small>${dateFormat(d.date,{day:"numeric",month:"short"})}</button>`).join("");
  $("#dates").querySelectorAll("button").forEach(b => b.onclick=()=>selectDate(b.dataset.date));
  const all = state.index.days;
  if (all.length) { $("#calendar").min=all.at(-1).date; $("#calendar").max=all[0].date; }
  $("#calendar").value=state.selected;
}

function videoCard(kind, video) {
  const title = kind==="recap" ? "NBA Nightly Recap" : video?.title.match(/Top\s*(10|5)/i)?.[0] + " Plays";
  const label = kind==="recap" ? "NIGHTLY RECAP" : "TOP PLAYS";
  if (!video) return `<article class="video-card"><div class="video-frame"><div class="empty-video"><h3>${kind==="recap"?"NBA Nightly Recap":"Top 10 / Top 5 Plays"}</h3><p>Not available for this date yet.</p></div></div><div class="video-caption"><div><h3>${kind==="recap"?"NBA Nightly Recap":"Top Plays"}</h3><p>Checked on each daily update</p></div></div></article>`;
  return `<article class="video-card"><div class="video-frame" id="player-${kind}"><button type="button" class="video-trigger" data-play="${kind}" aria-label="Play ${escapeHTML(title)}"><img src="https://i.ytimg.com/vi/${escapeHTML(video.id)}/hqdefault.jpg" alt="${escapeHTML(video.title)}"><span class="video-badge">${label} · NBA</span><span class="play" aria-hidden="true">▶</span></button></div><div class="video-caption"><div><h3>${escapeHTML(title)}</h3><p>Official NBA · ${dateFormat(video.date,{day:"numeric",month:"short",year:"numeric"})}</p></div>${outbound(video.source,"YouTube ↗")}</div></article>`;
}

function playVideo(kind, seconds=0) {
  const video=state.day?.videos?.[kind];
  if (!video || !/^[\w-]{11}$/.test(video.id)) return;
  document.querySelectorAll(".video-frame iframe").forEach(frame => {
    if (frame.parentElement.id !== `player-${kind}`) {
      const other=frame.parentElement.id.replace("player-","");
      frame.parentElement.outerHTML = new DOMParser().parseFromString(videoCard(other,state.day.videos[other]),"text/html").querySelector(".video-frame").outerHTML;
    }
  });
  const frame=document.createElement("iframe");
  frame.src=`https://www.youtube-nocookie.com/embed/${video.id}?autoplay=1&rel=0&start=${Math.max(0,Math.floor(seconds))}`;
  frame.title=video.title; frame.allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"; frame.allowFullscreen=true;
  frame.referrerPolicy="strict-origin-when-cross-origin";
  $(`#player-${kind}`).replaceChildren(frame);
  if (kind==="recap" && seconds>=0) $(`#player-${kind}`).scrollIntoView({behavior:"auto",block:"center"});
  bindPlayers();
}
function bindPlayers() { document.querySelectorAll("[data-play]").forEach(b=>b.onclick=()=>playVideo(b.dataset.play)); }

function renderVideos() {
  $("#videos").innerHTML=videoCard("top_plays",state.day.videos?.top_plays)+videoCard("recap",state.day.videos?.recap);
  bindPlayers();
  const list=state.day.videos?.recap?.chapters || [];
  $("#recap-chapters").hidden=!list.length;
  $("#recap-chapters").innerHTML=`<span class="chapter-label">JUMP TO</span>`+list.map((c,i)=>`<button type="button" class="chapter" data-chapter="${i}"><span>${escapeHTML(c.time)}</span>${escapeHTML(c.label)}</button>`).join("");
  document.querySelectorAll("[data-chapter]").forEach(b=>b.onclick=()=>playVideo("recap",list[Number(b.dataset.chapter)].seconds));
}
function gameChapter(game) {
  return (state.day.videos?.recap?.chapters||[]).find(c=>{
    const label=c.label.toLowerCase();
    return [game.away,game.home].every(t=>label.includes(t.short_name.toLowerCase()));
  });
}
function periodTable(game) {
  const count=Math.max(game.away.periods.length,game.home.periods.length);
  if (!count) return "";
  return `<div class="table-scroll"><table class="period-table" aria-label="Quarter scores"><thead><tr><th>Team</th>${Array.from({length:count},(_,i)=>`<th>${i<4?`Q${i+1}`:`OT${i-3}`}</th>`).join("")}<th>T</th></tr></thead><tbody>${["away","home"].map(s=>`<tr><td>${escapeHTML(game[s].abbreviation)}</td>${Array.from({length:count},(_,i)=>`<td>${game[s].periods[i]??"–"}</td>`).join("")}<td>${game[s].score}</td></tr>`).join("")}</tbody></table></div>`;
}
function playerContext(game) {
  const date=state.selected;
  const fallback=Number(date.slice(0,4))+(Number(date.slice(5,7))>=7?1:0);
  return {year:game.season_year||fallback,type:game.season_type===3?3:2};
}
function teamTable(team,game) {
  const cols=["MIN","PTS","REB","AST","FG","3PT","FT","STL","BLK","TO","+/-"];
  const context=playerContext(game);
  if (!team.players?.length) return `<p class="muted">Player box score pending. Retried on the next update.</p>`;
  return `<div><h3 class="box-team-label">${escapeHTML(team.name)}</h3><div class="table-scroll"><table aria-label="${escapeHTML(team.name)} player box score"><thead><tr><th>Player</th>${cols.map(c=>`<th scope="col">${c}</th>`).join("")}</tr></thead><tbody>${team.players.map(p=>{
    const id=`player-${game.id}-${team.id}-${p.id}`;
    return `<tr class="${p.dnp?"dnp":""}"><td><button type="button" id="${escapeHTML(id)}" class="player-name" data-player-id="${escapeHTML(p.id)}" data-player-year="${context.year}" data-player-type="${context.type}" data-player-panel="${escapeHTML(id)}-season" aria-expanded="false" aria-label="Season stats for ${escapeHTML(p.name)}">${escapeHTML(p.short_name||p.name)}<span class="player-chevron" aria-hidden="true">+</span></button>${p.starter?' <span class="starter" title="Starter">*</span>':""}</td>${p.dnp?`<td colspan="${cols.length}">DNP${p.reason?`: ${escapeHTML(p.reason)}`:""}</td>`:cols.map(c=>`<td>${escapeHTML(p.stats[c]??"–")}</td>`).join("")}</tr>`;
  }).join("")}</tbody><tfoot><tr><td>TEAM</td>${cols.map(c=>`<td>${escapeHTML(team.totals[c]||"–")}</td>`).join("")}</tr></tfoot></table></div></div>`;
}
function gameCard(game) {
  const chapter=gameChapter(game);
  return `<article class="game" data-game="${escapeHTML(game.id)}"><div class="game-top"><span>${escapeHTML(game.status.toUpperCase())}</span>${chapter?`<button type="button" data-game-chapter="${chapter.seconds}" aria-label="Watch ${escapeHTML(game.name)} in nightly recap">Watch recap ${escapeHTML(chapter.time)} ↗</button>`:""}</div><div class="team-rows">${["away","home"].map(side=>{
    const t=game[side],other=game[side==="away"?"home":"away"];
    return `<div class="team-row ${t.score<other.score?"loser":""}">${t.logo?`<img class="team-logo" src="${safeURL(t.logo)}" alt="" loading="lazy">`:""}<div class="team-name">${escapeHTML(t.name)} <small>${escapeHTML(t.record)}</small></div><span class="score">${t.score}</span></div>`;
  }).join("")}</div><details><summary aria-label="Box score: ${escapeHTML(game.name)}">Box score</summary><div class="box-content">${periodTable(game)}<p class="table-hint">* Starter · Click a player for season stats · Scroll tables for all stats</p><div class="box-teams">${teamTable(game.away,game)}${teamTable(game.home,game)}</div><div class="box-actions">${outbound(game.source,"Full box score on ESPN ↗","box-source")}<button type="button" class="box-close" data-close-box>Close box score</button></div></div></details></article>`;
}
function renderGames() {
  playerSizes.disconnect();
  const games=state.day?.games||[];
  const filtered=games.filter(g=>!state.team || [g.home.id,g.away.id].includes(state.team));
  $("#games").classList.toggle("score-hidden",state.hidden);
  $("#games").innerHTML=filtered.length ? filtered.map(gameCard).join("") : `<div class="empty"><h3>${state.team?"No games for this team.":state.day.pending_games?"Games are not final yet.":"No completed games on this date."}</h3><p>${state.team?"Choose another team or date.":state.day.pending_games?"Results will appear after the next scheduled update.":"Choose another edition from the archive."}</p></div>`;
  $("#games").querySelectorAll("[data-game-chapter]").forEach(b=>b.onclick=()=>playVideo("recap",Number(b.dataset.gameChapter)));
  $("#edition-meta").textContent=`${games.length} final game${games.length===1?"":"s"} · ${state.index.days.find(d=>d.date===state.selected)?.season||""} season`;
  updateFloatingClose();
}

function updateFloatingClose() {
  floatingBox=null;
  if (!state.hidden) {
    for (const box of document.querySelectorAll("#games details[open]")) {
      const rect=box.getBoundingClientRect();
      if (rect.top<0 && rect.bottom>88) { floatingBox=box; break; }
    }
  }
  $("#floating-close").hidden=!floatingBox;
  if (floatingBox) $("#floating-close").setAttribute("aria-label",`Close ${floatingBox.querySelector("summary").getAttribute("aria-label")}`);
}
function closeBox(box) {
  if (!box) return;
  box.open=false;
  const summary=box.querySelector("summary");
  summary.focus({preventScroll:true});
  requestAnimationFrame(()=>{
    summary.scrollIntoView({block:"nearest",behavior:"auto"});
    updateFloatingClose();
  });
}
let closeFrame=0;
window.addEventListener("scroll",()=>{
  if (!closeFrame) closeFrame=requestAnimationFrame(()=>{closeFrame=0;updateFloatingClose();});
},{passive:true});
window.addEventListener("resize",updateFloatingClose);
$("#games").addEventListener("toggle",updateFloatingClose,true);
$("#games").addEventListener("click",e=>{
  const player=e.target.closest("[data-player-id]");
  if (player) { togglePlayer(player); return; }
  const action=e.target.closest("[data-close-player],[data-retry-player]");
  if (action) {
    const row=action.closest(".player-season-row");
    const trigger=document.getElementById(row.dataset.trigger);
    if (action.hasAttribute("data-close-player")) closePlayer(trigger);
    else loadPlayerRow(trigger,row);
    return;
  }
  if (e.target.closest("[data-close-box]")) closeBox(e.target.closest("details"));
});
$("#floating-close").onclick=()=>closeBox(floatingBox);
document.addEventListener("keydown",e=>{
  if (e.key==="Escape") {
    const row=e.target.closest?.(".player-season-row");
    const player=e.target.closest?.('[data-player-id][aria-expanded="true"]') ||
      (row?document.getElementById(row.dataset.trigger):null);
    if (player) { e.preventDefault(); closePlayer(player); return; }
    const box=e.target.closest?.("#games details[open]") || (e.target===$("#floating-close")?floatingBox:null);
    if (box) { e.preventDefault(); closeBox(box); }
  }
});

function sizePlayerPanels(wrapper) {
  const width=wrapper.clientWidth;
  if (width) wrapper.querySelectorAll(".player-season-panel").forEach(p=>p.style.width=`${width}px`);
}
function closePlayer(trigger) {
  const row=document.getElementById(trigger.getAttribute("aria-controls"));
  if (row) row.hidden=true;
  trigger.setAttribute("aria-expanded","false");
  trigger.focus({preventScroll:true});
  requestAnimationFrame(()=>{
    const rect=trigger.getBoundingClientRect();
    if (rect.top<0 || rect.bottom>innerHeight) trigger.scrollIntoView({block:"nearest"});
    updateFloatingClose();
  });
}
function togglePlayer(trigger) {
  if (trigger.getAttribute("aria-expanded")==="true") { closePlayer(trigger); return; }
  const id=trigger.dataset.playerPanel;
  let row=document.getElementById(id);
  if (!row) {
    row=document.createElement("tr");
    row.id=id;
    row.className="player-season-row";
    row.dataset.trigger=trigger.id;
    const columns=trigger.closest("table").tHead.rows[0].cells.length;
    row.innerHTML=`<td colspan="${columns}"><div class="player-season-panel" role="region" aria-label="${escapeHTML(trigger.getAttribute("aria-label"))}" aria-live="polite"></div></td>`;
    trigger.closest("tr").after(row);
  }
  row.hidden=false;
  trigger.setAttribute("aria-controls",id);
  trigger.setAttribute("aria-expanded","true");
  const wrapper=row.closest(".table-scroll");
  playerSizes.observe(wrapper);
  sizePlayerPanels(wrapper);
  loadPlayerRow(trigger,row);
}
async function readPlayer(trigger) {
  const {playerId:id,playerYear:year,playerType:type}=trigger.dataset;
  const key=`${year}/${type}/${id}`;
  if (!playerCache.has(key)) {
    const label=`${Number(year)-1}-${year.slice(-2)}`;
    const pending=readJSON(`./data/players/${label}/${type==="3"?"playoffs":"regular"}/${id}.json`).then(data=>{
      if (data.schema_version!==1 || data.id!==id || data.season?.year!==Number(year) ||
          data.season.type!==Number(type) || !["ok","stale","no_stats","unavailable"].includes(data.status) ||
          (["ok","stale"].includes(data.status) && !Number.isInteger(data.stats?.gp))) throw new Error("Invalid player snapshot");
      return data;
    }).catch(error=>{playerCache.delete(key);throw error;});
    playerCache.set(key,pending);
  }
  return playerCache.get(key);
}
async function loadPlayerRow(trigger,row) {
  const panel=row.querySelector(".player-season-panel");
  const playerName=trigger.getAttribute("aria-label").replace(/^Season stats for /,"");
  const close=`<button type="button" class="player-season-close" data-close-player aria-label="Close ${escapeHTML(playerName)} season stats">×</button>`;
  const label=`${Number(trigger.dataset.playerYear)-1}-${trigger.dataset.playerYear.slice(-2)} ${trigger.dataset.playerType==="3"?"playoff":"regular-season"} averages`;
  panel.innerHTML=`<div class="player-season-heading"><p>${escapeHTML(label)}</p>${close}</div><p class="muted">Loading season stats…</p>`;
  try {
    const data=await readPlayer(trigger);
    if (!row.isConnected) return;
    const heading=`<div class="player-season-heading"><div><strong>${escapeHTML(data.name)}</strong><p class="muted">${escapeHTML(label)}</p></div>${close}</div>`;
    if (!data.stats) {
      panel.innerHTML=heading+`<p class="player-season-note">${data.status==="no_stats"?"No statistics have been published for this player in this season and competition.":"Season stats could not be refreshed. The next daily update will retry."} ${outbound(data.source,"ESPN ↗")}</p>`;
    } else {
      const fields=[["GP","gp"],["MPG","mpg"],["PPG","ppg"],["RPG","rpg"],["APG","apg"],["SPG","spg"],["BPG","bpg"],["TOV","tov"],["FG%","fg_pct"],["3P%","three_pct"],["FT%","ft_pct"]];
      const stats=fields.map(([title,key])=>{
        const value=data.stats[key];
        const text=Number.isFinite(value)?(key==="gp"?String(value):value.toFixed(1))+(key.endsWith("_pct")?"%":""):'<span aria-label="Unavailable">–</span>';
        return `<div><dt>${title}</dt><dd>${text}</dd></div>`;
      }).join("");
      const checked=new Intl.DateTimeFormat("en-IE",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Dublin",timeZoneName:"short"}).format(new Date(data.checked_at));
      panel.innerHTML=heading+`<dl class="player-season-stats">${stats}</dl><p class="player-season-note">${data.status==="stale"?"Refresh failed; showing last-saved averages. ":""}All teams · Checked ${escapeHTML(checked)} · Season snapshot, not as of this game. ${outbound(data.source,"ESPN ↗")}</p>`;
    }
  } catch {
    if (row.isConnected) panel.innerHTML=`<div class="player-season-heading"><p>${escapeHTML(label)}</p>${close}</div><p class="player-season-note">Season stats could not be loaded. <button type="button" class="player-retry" data-retry-player>Try again</button></p>`;
  }
  if (row.isConnected) {
    sizePlayerPanels(row.closest(".table-scroll"));
    requestAnimationFrame(updateFloatingClose);
  }
}

function renderSchedule() {
  const data=scheduleState.data;
  const today=new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
  const stale=today!==data.from_date;
  const updated=new Intl.DateTimeFormat("en-IE",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Dublin",timeZoneName:"short"}).format(new Date(data.generated_at));
  $("#schedule-note").textContent=`${stale?"Saved schedule may be out of date. ":""}Updated ${updated} · Not live · Game dates: US Eastern`;
  $("#schedule-dates").innerHTML=data.days.map(d=>`<button type="button" class="date-button" data-schedule-date="${escapeHTML(d.date)}" aria-pressed="${d.date===scheduleState.selected}"><small>${d.date===today?"Today":dateFormat(d.date,{weekday:"short"})}</small>${dateFormat(d.date,{day:"numeric",month:"short"})}</button>`).join("");
  const day=data.days.find(d=>d.date===scheduleState.selected);
  const zone=$("#schedule-zone").value;
  const timeFormat=new Intl.DateTimeFormat("en-IE",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:zone,timeZoneName:"short"});
  const warning=day.status!=="ok"?`<p class="schedule-footer">${day.status==="stale"?`Latest refresh failed. Last-saved fixtures checked ${escapeHTML(timeFormat.format(new Date(day.checked_at)))}.`:"Fixtures for this date could not be refreshed. The next daily update will retry."}</p>`:"";
  $("#schedule-games").innerHTML=`<h3 class="schedule-day-heading">${formatFull(day.date)}</h3>`+(day.games?.length?`<ul class="schedule-list">${day.games.map(g=>{
    const status=g.completed?"Completed":g.state==="in"?"In progress at update":g.status_name==="STATUS_SCHEDULED"?"":g.status;
    return `<li class="schedule-game"><div class="schedule-matchup"><strong>${escapeHTML(g.away.name)}</strong><span>at</span><strong>${escapeHTML(g.home.name)}</strong></div><div class="schedule-time">${g.time_tbd?"Time TBD":`<time datetime="${escapeHTML(g.start_time)}">${escapeHTML(timeFormat.format(new Date(g.start_time)))}</time>`}${status?`<span>${escapeHTML(status)}</span>`:""}</div></li>`;
  }).join("")}</ul>`:`<p class="muted">${day.games===null?"Schedule unavailable for this date.":"No NBA games scheduled for this date."}</p>`)+warning+`<p class="schedule-footer">Tip-off dates and times shown in ${zone==="Europe/Dublin"?"Dublin":"US Eastern"} time. Subject to change. ${outbound(data.source,"ESPN schedule ↗")}</p>`;
}
async function loadSchedule() {
  if (scheduleState.data) { renderSchedule(); return; }
  if (scheduleState.pending) return scheduleState.pending;
  $("#schedule-games").innerHTML='<div class="loading">Loading upcoming games…</div>';
  scheduleState.pending=(async()=>{
    try {
      const data=await readJSON("./data/schedule.json");
      if (!Array.isArray(data.days) || !data.days.length) throw new Error("Invalid schedule");
      scheduleState.data=data;
      scheduleState.selected=data.days[0].date;
      renderSchedule();
    } catch {
      scheduleState.data=null;
      $("#schedule-games").innerHTML='<div class="empty"><h3>Upcoming games could not be loaded.</h3><p>The daily archive is still available below.</p><button type="button" data-retry-schedule>Try again</button></div>';
    } finally { scheduleState.pending=null; }
  })();
  return scheduleState.pending;
}
$("#schedule").addEventListener("toggle",()=>{if ($("#schedule").open) loadSchedule();});
$("#schedule-dates").addEventListener("click",e=>{
  const button=e.target.closest("[data-schedule-date]");
  if (button) { scheduleState.selected=button.dataset.scheduleDate; renderSchedule(); }
});
$("#schedule-games").addEventListener("click",e=>{if (e.target.closest("[data-retry-schedule]")) loadSchedule();});
$("#schedule-zone").onchange=()=>{if (scheduleState.data) renderSchedule();};

function syncStandingsSpoilers() {
  $("#standings-spoilers").hidden=!state.hidden;
  $("#standings-content").hidden=state.hidden;
  if (!state.hidden && $("#standings").open) loadStandings();
}
function renderStandings() {
  const data=standingsState.data;
  if (!data || data.status==="unavailable") {
    $("#standings-controls").hidden=true;
    $("#standings-note").textContent="Current standings unavailable · Daily archive unaffected";
    $("#standings-results").innerHTML='<div class="empty"><h3>Season standings are not available yet.</h3><p>The next daily update will retry.</p></div>';
    return;
  }
  const stamp=new Intl.DateTimeFormat("en-IE",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Dublin",timeZoneName:"short"}).format(new Date(data.checked_at));
  const old=Date.now()-Date.parse(data.checked_at)>36*3600*1000;
  $("#standings-note").textContent=`${data.season.label} regular season · Checked ${stamp} · Not live${data.status==="stale"?" · Refresh failed; last-saved standings":old?" · Saved standings may be out of date":""}. Latest season, independent of archive date.`;
  $("#standings-controls").hidden=false;
  const view=standingsState.view;
  $("#standings-views").querySelectorAll("button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.standingsView===view)));
  const groups=view==="league"?[]:data[view==="conference"?"conferences":"divisions"];
  if (groups.length && !groups.some(g=>g.id===standingsState.groups[view])) standingsState.groups[view]=groups[0].id;
  $("#standings-group-label").hidden=view==="league";
  $("#standings-group").innerHTML=groups.map(g=>`<option value="${escapeHTML(g.id)}">${escapeHTML(g.name)}</option>`).join("");
  if (groups.length) $("#standings-group").value=standingsState.groups[view];
  const group=groups.find(g=>g.id===standingsState.groups[view]);
  const name=view==="league"?"League comparison":group.name;
  const base=data.teams.filter(t=>view==="league" || t[`${view}_id`]===group.id);
  base.sort(view==="league"?(a,b)=>b.stats.win_pct-a.stats.win_pct || b.stats.wins-a.stats.wins || a.name.localeCompare(b.name):(a,b)=>a.stats.conference_rank-b.stats.conference_rank);
  const ranks=new Map(base.map((t,i)=>[t.id,view==="conference"?t.stats.conference_rank:i+1]));
  const leader=base[0];
  const query=$("#standings-search").value.trim().toLowerCase();
  const visible=base.filter(t=>`${t.name} ${t.abbreviation} ${t.short_name}`.toLowerCase().includes(query));
  const sort=$("#standings-sort").value;
  if (sort!=="rank") visible.sort((a,b)=>{
    const left=a.stats[sort],right=b.stats[sort];
    if (left===null && right===null) return ranks.get(a.id)-ranks.get(b.id);
    if (left===null) return 1;
    if (right===null) return -1;
    return (sort==="points_against"?left-right:right-left) || ranks.get(a.id)-ranks.get(b.id);
  });
  const missing='<span aria-label="Unavailable">–</span>';
  const number=(value,digits=1)=>Number.isFinite(value)?value.toFixed(digits):missing;
  const gb=t=>view==="conference"?t.stats.conference_gb:((leader.stats.wins-t.stats.wins)+(t.stats.losses-leader.stats.losses))/2;
  const headers=[["Team","Group rank and team"],["W-L","Wins and losses"],["PCT","Win percentage"],...(view==="league"?[]:[["GB",view==="conference"?"Games behind conference leader":"Games behind division leader"]]),["L10","Last ten games"],["STRK","Current streak"],["PF/G","Points scored per game"],["PA/G","Points conceded per game"],["DIFF","Points differential per game, not net rating"]];
  const table=visible.length?`<p class="standings-scroll-hint">Scroll the table horizontally for team stats.</p><div class="table-scroll" role="region" aria-label="${escapeHTML(name)} team statistics, scroll for all columns" tabindex="0"><table class="standings-table"><caption class="standings-caption">${escapeHTML(name)}<span class="standings-record-note">${visible.length} of ${base.length} teams</span></caption><thead><tr>${headers.map(([text,title])=>`<th scope="col" title="${title}">${text}</th>`).join("")}</tr></thead><tbody>${visible.map(t=>{
    const s=t.stats;
    const behind=view==="league"?null:gb(t);
    const text=value=>value?escapeHTML(value):missing;
    return `<tr data-standing-team="${escapeHTML(t.id)}"><th scope="row"><span class="standings-rank">${ranks.get(t.id)}</span><span class="standings-team-full">${escapeHTML(t.name)}</span><span class="standings-team-short" title="${escapeHTML(t.name)}">${escapeHTML(t.short_name)}</span></th><td>${s.wins}-${s.losses}</td><td>${s.win_pct.toFixed(3)}</td>${view==="league"?"":`<td>${behind===0?"–":number(behind,Number.isInteger(behind)?0:1)}</td>`}<td>${text(s.last_ten)}</td><td>${text(s.streak)}</td><td>${number(s.points_for)}</td><td>${number(s.points_against)}</td><td class="${s.point_diff>0?"standings-diff-positive":""}">${s.point_diff>0?"+":""}${number(s.point_diff)}</td></tr>`;
  }).join("")}</tbody></table></div>`:'<div class="empty"><h3>No matching teams in this group.</h3><p>Clear the team filter or choose another group.</p></div>';
  const order=view==="league"?"League order: win percentage, then wins, then team name. Comparison only, not official playoff seeding. Games behind is omitted across conferences.":view==="conference"?"Conference order and games behind follow ESPN’s conference standings.":"Division order follows the provider’s conference rankings within each division, including its tiebreaks. Games behind is calculated from this division’s leader.";
  $("#standings-results").innerHTML=table+`<div class="standings-footer"><p>${order}${sort!=="rank"?" Rows are sorted by the selected statistic; rank labels remain the original group ranks.":""}</p><p>PF/G and PA/G are points per game. DIFF is average point differential, not net rating. Scroll horizontally for all columns. ${outbound(data.source,"ESPN standings ↗")}</p></div>`;
}
async function loadStandings() {
  if (state.hidden) return;
  if (standingsState.data) { renderStandings(); return; }
  if (standingsState.pending) return standingsState.pending;
  $("#standings-results").innerHTML='<div class="loading">Loading standings…</div>';
  standingsState.pending=(async()=>{
    try {
      const data=await readJSON("./data/standings.json");
      if (data.schema_version!==1 || !["ok","stale","unavailable"].includes(data.status) ||
          !Array.isArray(data.teams) || (data.status!=="unavailable" && (data.teams.length!==30 || data.season?.type!==2))) throw new Error("Invalid standings");
      standingsState.data=data;
      renderStandings();
    } catch {
      standingsState.data=null;
      $("#standings-controls").hidden=true;
      $("#standings-results").innerHTML='<div class="empty"><h3>Standings could not be loaded.</h3><p>The daily archive is still available below.</p><button type="button" data-retry-standings>Try again</button></div>';
    } finally { standingsState.pending=null; }
  })();
  return standingsState.pending;
}
$("#standings").addEventListener("toggle",()=>{if ($("#standings").open) syncStandingsSpoilers();});
$("#standings-views").addEventListener("click",e=>{
  const button=e.target.closest("[data-standings-view]");
  if (button) { standingsState.view=button.dataset.standingsView; renderStandings(); }
});
$("#standings-group").onchange=e=>{standingsState.groups[standingsState.view]=e.target.value;renderStandings();};
$("#standings-sort").onchange=renderStandings;
$("#standings-search").oninput=renderStandings;
$("#standings-results").addEventListener("click",e=>{if (e.target.closest("[data-retry-standings]")) loadStandings();});

function renderTeamFilter() {
  const teams=[...new Map(state.day.games.flatMap(g=>[g.away,g.home]).map(t=>[t.id,t])).values()].sort((a,b)=>a.name.localeCompare(b.name));
  if (!teams.some(t=>t.id===state.team)) state.team="";
  $("#team-filter").innerHTML='<option value="">All teams</option>'+teams.map(t=>`<option value="${escapeHTML(t.id)}">${escapeHTML(t.name)}</option>`).join("");
  $("#team-filter").value=state.team;
}

async function selectDate(date) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return;
  const request=++state.request;
  state.selected=date;
  renderDates();
  $("#edition-date").textContent=formatFull(date);
  notify("");
  const exists=state.index.days.some(d=>d.date===date);
  if (!exists) {
    state.day={date,games:[],videos:{}};
    renderVideos(); renderTeamFilter(); renderGames();
    notify("This date is not in the archive. Choose a highlighted recent date or another archived date.");
    return;
  }
  try {
    const day=await readJSON(`./data/days/${date}.json`);
    if (request!==state.request) return;
    state.day=day;
    renderVideos(); renderTeamFilter(); renderGames();
    try { history.replaceState(null,"",`?date=${date}`); } catch { /* Embed may disallow history. */ }
    if (state.index.health.scores==="error" || state.index.health.videos==="error") notify("An upstream feed is unavailable. Showing the last saved data; the next update will retry.");
    else if (Date.now()-Date.parse(state.index.updated_at)>36*3600*1000) notify("The archive has not updated in over 36 hours. Check Update status below.");
  } catch {
    if (request!==state.request) return;
    $("#videos").innerHTML=""; $("#recap-chapters").hidden=true;
    $("#games").innerHTML='<div class="empty"><h3>This edition could not be loaded.</h3><p>Please refresh, or try another date.</p></div>';
    notify("There was a problem reading this archive file.");
  }
}

$("#calendar").onchange=e=>selectDate(e.target.value);
$("#team-filter").onchange=e=>{state.team=e.target.value;renderGames();};
$("#spoilers").onclick=()=>{
  state.hidden=!state.hidden;
  $("#spoilers").setAttribute("aria-pressed",String(state.hidden));
  $("#spoilers").textContent=state.hidden?"Show scores":"Hide scores";
  renderGames();
  syncStandingsSpoilers();
};
async function init() {
  try {
    state.index=await readJSON("./data/index.json");
    if (!state.index.days.length) throw new Error("Empty archive");
    const updated=new Date(state.index.updated_at);
    $("#updated").textContent=`Updated ${new Intl.DateTimeFormat("en-IE",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Dublin",timeZoneName:"short"}).format(updated)} · Daily archive`;
    const requested=new URLSearchParams(location.search).get("date");
    const latest=state.index.days.find(d=>d.games && (d.top_plays||d.recap)) || state.index.days.find(d=>d.games) || state.index.days[0];
    await selectDate(requested && /^\d{4}-\d{2}-\d{2}$/.test(requested) ? requested : latest.date);
  } catch {
    $("#updated").textContent="Archive unavailable";
    $("#videos").innerHTML="";
    $("#games").innerHTML='<div class="empty"><h3>The archive could not be loaded.</h3><p>Please refresh in a moment.</p><button type="button" id="retry">Try again</button></div>';
    $("#retry").onclick=init;
    notify("Unable to load saved data. Check your connection and try again.");
  }
}
init();

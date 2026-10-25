"use strict";
const $ = s => document.querySelector(s);
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeURL = value => { try { const u = new URL(value); return u.protocol === "https:" ? escapeHTML(u.href) : ""; } catch { return ""; } };
const state = {index:null, day:null, selected:null, hidden:false, team:"", request:0};
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
function teamTable(team) {
  const cols=["MIN","PTS","REB","AST","FG","3PT","FT","STL","BLK","TO","+/-"];
  if (!team.players.length) return `<p class="muted">Player box score pending. Retried on the next update.</p>`;
  return `<div><h3 class="box-team-label">${escapeHTML(team.name)}</h3><div class="table-scroll"><table aria-label="${escapeHTML(team.name)} player box score"><thead><tr><th>Player</th>${cols.map(c=>`<th scope="col">${c}</th>`).join("")}</tr></thead><tbody>${team.players.map(p=>`<tr class="${p.dnp?"dnp":""}"><td>${escapeHTML(p.short_name)}${p.starter?' <span class="starter" title="Starter">*</span>':""}</td>${p.dnp?`<td colspan="${cols.length}">DNP${p.reason?`: ${escapeHTML(p.reason)}`:""}</td>`:cols.map(c=>`<td>${escapeHTML(p.stats[c]??"–")}</td>`).join("")}</tr>`).join("")}</tbody><tfoot><tr><td>TEAM</td>${cols.map(c=>`<td>${escapeHTML(team.totals[c]||"–")}</td>`).join("")}</tr></tfoot></table></div></div>`;
}
function gameCard(game) {
  const chapter=gameChapter(game);
  return `<article class="game" data-game="${escapeHTML(game.id)}"><div class="game-top"><span>${escapeHTML(game.status.toUpperCase())}</span>${chapter?`<button type="button" data-game-chapter="${chapter.seconds}" aria-label="Watch ${escapeHTML(game.name)} in nightly recap">Watch recap ${escapeHTML(chapter.time)} ↗</button>`:""}</div><div class="team-rows">${["away","home"].map(side=>{
    const t=game[side],other=game[side==="away"?"home":"away"];
    return `<div class="team-row ${t.score<other.score?"loser":""}">${t.logo?`<img class="team-logo" src="${safeURL(t.logo)}" alt="" loading="lazy">`:""}<div class="team-name">${escapeHTML(t.name)} <small>${escapeHTML(t.record)}</small></div><span class="score">${t.score}</span></div>`;
  }).join("")}</div><details><summary>Box score</summary><div class="box-content">${periodTable(game)}<p class="table-hint">* Starter · Scroll tables for all stats</p><div class="box-teams">${teamTable(game.away)}${teamTable(game.home)}</div>${outbound(game.source,"Full box score on ESPN ↗","box-source")}</div></details></article>`;
}
function renderGames() {
  const games=state.day?.games||[];
  const filtered=games.filter(g=>!state.team || [g.home.id,g.away.id].includes(state.team));
  $("#games").classList.toggle("score-hidden",state.hidden);
  $("#games").innerHTML=filtered.length ? filtered.map(gameCard).join("") : `<div class="empty"><h3>${state.team?"No games for this team.":state.day.pending_games?"Games are not final yet.":"No completed games on this date."}</h3><p>${state.team?"Choose another team or date.":state.day.pending_games?"Results will appear after the next scheduled update.":"Choose another edition from the archive."}</p></div>`;
  $("#games").querySelectorAll("[data-game-chapter]").forEach(b=>b.onclick=()=>playVideo("recap",Number(b.dataset.gameChapter)));
  $("#edition-meta").textContent=`${games.length} final game${games.length===1?"":"s"} · ${state.index.days.find(d=>d.date===state.selected)?.season||""} season`;
}
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

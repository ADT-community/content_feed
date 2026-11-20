/* content_feed: short video feed where fans tip creators by mobile money. */
(() => {
  "use strict";
  const CFG = window.FEED_CONFIG;
  const DATA = window.FEED_DATA;
  const $ = (s, el = document) => el.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const money = (n) => "₦" + Math.round(n).toLocaleString(CFG.locale);
  const short = (n) => n >= 1e6 ? (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M" : n >= 1e3 ? (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K" : String(n);
  const initials = (name) => name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
  const creatorShare = 1 - CFG.platformFee;

  const ICON = {
    heart: '<svg viewBox="0 0 24 24"><path d="M12 21.4 10.6 20C5.4 15.4 2 12.3 2 8.5 2 5.4 4.4 3 7.5 3c1.7 0 3.4.8 4.5 2.1A6 6 0 0 1 16.5 3C19.6 3 22 5.4 22 8.5c0 3.8-3.4 6.9-8.6 11.5L12 21.4Z"/></svg>',
    comment: '<svg viewBox="0 0 24 24"><path d="M21 6h-2v9H6v2a1 1 0 0 0 1 1h11l4 4V7a1 1 0 0 0-1-1Zm-4 6V3a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v14l4-4h10a1 1 0 0 0 1-1Z"/></svg>',
    gift: '<svg viewBox="0 0 24 24"><path d="M20 7h-2.2A3 3 0 0 0 12 3.8 3 3 0 0 0 6.2 7H4a2 2 0 0 0-2 2v2a1 1 0 0 0 1 1h8V7h2v5h8a1 1 0 0 0 1-1V9a2 2 0 0 0-2-2ZM9 7a1 1 0 1 1 1-1v1H9Zm6 0h-1V6a1 1 0 1 1 1 1ZM4 14v6a1 1 0 0 0 1 1h6v-7H4Zm9 7h6a1 1 0 0 0 1-1v-6h-7v7Z"/></svg>',
    share: '<svg viewBox="0 0 24 24"><path d="M14 9V5l7 7-7 7v-4.1c-5 0-8.5 1.6-11 5.1 1-5 4-10 11-11Z"/></svg>',
    more: '<svg viewBox="0 0 24 24"><path d="M6 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm12 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm-6 0a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/></svg>',
    play: '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7L8 5Z"/></svg>'
  };

  const state = {
    posts: DATA.posts.map((p) => ({ ...p, liked: false, comments: [...p.comments] })),
    following: new Set(),
    hidden: new Set(),
    muted: true,
    me: { ...DATA.me, supporters: [...DATA.me.supporters], posts: [] }
  };
  const creatorOf = (p) => p.creator === "me" ? { handle: state.me.handle, name: state.me.name, color: "#e8a33d", city: "", followers: 0, bio: "" } : DATA.creators[p.creator];

  /* ---------- shared UI ---------- */
  let toastTimer;
  function toast(msg) {
    const t = $("#toast");
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
  }
  function openSheet(title, html, onReady) {
    $("#sheetTitle").textContent = title;
    $("#sheetBody").innerHTML = html;
    $("#sheetBg").hidden = false;
    onReady && onReady($("#sheetBody"));
  }
  function closeSheet() { $("#sheetBg").hidden = true; }
  $("#sheetBg").addEventListener("click", (e) => { if (e.target.id === "sheetBg" || e.target.closest("[data-close]")) closeSheet(); });

  /* ---------- tabs ---------- */
  function showView(name) {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.view === name));
    document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + name));
    if (name === "feed") playVisible(); else pauseAll();
    if (name === "earn") renderEarnings();
  }
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showView(t.dataset.view)));

  /* =====================================================================
   * FEED
   * ===================================================================== */
  const feed = $("#feed");
  let observer;

  function postHTML(p) {
    const c = creatorOf(p);
    const following = state.following.has(p.creator);
    return `
      <article class="post" data-id="${p.id}">
        <video src="${esc(p.video)}" loop playsinline muted preload="metadata"></video>
        <div class="shade"></div>
        <div class="paused-icon">${ICON.play}</div>
        <div class="meta">
          <div class="who">@${esc(c.handle)}${c.city ? `<small>${esc(c.city)}</small>` : ""}</div>
          <div class="cap">${esc(p.caption)}</div>
          <div class="sound">♪ ${esc(p.sound || "Original sound")}</div>
        </div>
        <div class="rail">
          <button data-act="profile" aria-label="Open @${esc(c.handle)}'s profile">
            <span class="avatar${following ? " following" : ""}" style="--c:${c.color}">${esc(initials(c.name))}<span class="plus">${following ? "✓" : "+"}</span></span>
          </button>
          <button data-act="like" class="${p.liked ? "liked" : ""}" aria-label="Like">${ICON.heart}<span>${short(p.likes)}</span></button>
          <button data-act="comments" aria-label="Comments">${ICON.comment}<span>${short(p.comments.length)}</span></button>
          <button data-act="tip" class="tip-btn" aria-label="Tip @${esc(c.handle)}"><span class="tip-circle">${ICON.gift}</span><span>Tip</span></button>
          <button data-act="share" aria-label="Share">${ICON.share}<span>Share</span></button>
          <button data-act="more" aria-label="More options">${ICON.more}</button>
        </div>
      </article>`;
  }

  function renderFeed() {
    pauseAll();
    feed.innerHTML = state.posts.filter((p) => !state.hidden.has(p.id)).map(postHTML).join("");
    observer && observer.disconnect();
    observer = new IntersectionObserver((entries) => {
      for (const e of entries) {
        const v = e.target.querySelector("video");
        if (e.isIntersecting && e.intersectionRatio > 0.6 && $("#view-feed").classList.contains("active")) {
          v.muted = state.muted;
          v.play().then(() => e.target.classList.remove("paused")).catch(() => e.target.classList.add("paused"));
        } else {
          v.pause();
        }
      }
    }, { threshold: [0, 0.6, 1] });
    feed.querySelectorAll(".post").forEach((el) => observer.observe(el));
  }
  function pauseAll() { feed.querySelectorAll("video").forEach((v) => v.pause()); }
  function playVisible() {
    const r = feed.getBoundingClientRect();
    feed.querySelectorAll(".post").forEach((el) => {
      const b = el.getBoundingClientRect();
      const v = el.querySelector("video");
      if (Math.abs(b.top - r.top) < r.height * 0.4) { v.muted = state.muted; v.play().catch(() => el.classList.add("paused")); }
    });
  }
  const postById = (id) => state.posts.find((p) => p.id === id);
  const rerenderRail = (el, p) => {
    const fresh = document.createElement("div");
    fresh.innerHTML = postHTML(p);
    el.querySelector(".rail").replaceWith(fresh.querySelector(".rail"));
  };

  // Tap to pause/play, double-tap to like
  let lastTap = 0, tapTimer;
  feed.addEventListener("click", (e) => {
    const el = e.target.closest(".post");
    if (!el) return;
    const p = postById(el.dataset.id);
    const btn = e.target.closest("[data-act]");
    if (btn) return handleAction(btn.dataset.act, p, el);
    const now = Date.now();
    if (now - lastTap < 280) {
      clearTimeout(tapTimer);
      if (!p.liked) { p.liked = true; p.likes++; rerenderRail(el, p); }
      const h = document.createElement("div");
      h.className = "heart-burst"; h.textContent = "❤️";
      const r = el.getBoundingClientRect();
      h.style.left = (e.clientX - r.left) + "px"; h.style.top = (e.clientY - r.top) + "px";
      el.append(h); setTimeout(() => h.remove(), 800);
    } else {
      tapTimer = setTimeout(() => {
        const v = el.querySelector("video");
        if (v.paused) { v.muted = state.muted; v.play(); el.classList.remove("paused"); } else { v.pause(); el.classList.add("paused"); }
      }, 280);
    }
    lastTap = now;
  });

  $("#soundBtn").addEventListener("click", () => {
    state.muted = !state.muted;
    $("#soundBtn").setAttribute("aria-pressed", String(!state.muted));
    $("#soundBtn").setAttribute("aria-label", state.muted ? "Turn sound on" : "Turn sound off");
    feed.querySelectorAll("video").forEach((v) => (v.muted = state.muted));
  });

  function handleAction(act, p, el) {
    const c = creatorOf(p);
    if (act === "like") { p.liked = !p.liked; p.likes += p.liked ? 1 : -1; rerenderRail(el, p); }
    if (act === "comments") openComments(p, el);
    if (act === "tip") openTip(p, el);
    if (act === "profile") openProfile(p.creator);
    if (act === "share") sharePost(p, c);
    if (act === "more") openReport(p);
  }

  /* ---------- comments ---------- */
  function openComments(p, el) {
    const draw = () => p.comments.map(([who, text]) => `
      <div class="comment"><span class="avatar" style="--c:#4a4038;color:var(--text)">${esc(who[0].toUpperCase())}</span>
      <div><b>@${esc(who)}</b><div>${esc(text)}</div></div></div>`).join("") || `<p>No comments yet. Be the first!</p>`;
    openSheet(`${p.comments.length} comments`, `
      <div id="commentList">${draw()}</div>
      <form class="comment-form" id="commentForm">
        <input id="commentInput" maxlength="200" placeholder="Add a comment…" autocomplete="off">
        <button class="btn primary" type="submit">Send</button>
      </form>`, (body) => {
      $("#commentForm", body).addEventListener("submit", (e) => {
        e.preventDefault();
        const text = $("#commentInput", body).value.trim();
        if (!text) return;
        p.comments.push([state.me.handle, text]);
        $("#commentList", body).innerHTML = draw();
        $("#sheetTitle").textContent = `${p.comments.length} comments`;
        $("#commentInput", body).value = "";
        rerenderRail(el, p);
      });
    });
  }

  /* ---------- tipping ---------- */
  function openTip(p, el) {
    const c = creatorOf(p);
    if (p.creator === "me") return toast("You can't tip yourself 😄");
    let choice = DATA.gifts[1];
    const tips = [100, 200, 500, 1000];
    openSheet(`Support @${c.handle}`, `
      <p>Send a gift or a tip. ${Math.round(creatorShare * 100)}% goes straight to ${esc(c.name.split(" ")[0])}.</p>
      <div class="chips" id="giftChips">${DATA.gifts.map((g) => `
        <button class="chip${g.id === choice.id ? " sel" : ""}" data-gift="${g.id}"><span class="e">${g.emoji}</span>${esc(g.name)}<small>${money(g.amount)}</small></button>`).join("")}</div>
      <label>Or a plain tip</label>
      <div class="chips" id="tipChips">${tips.map((t) => `<button class="chip" data-tip="${t}">${money(t)}</button>`).join("")}</div>
      <label for="tipPhone">Pay from mobile money</label>
      <input id="tipPhone" type="tel" inputmode="tel" placeholder="Your mobile money number" autocomplete="tel">
      <select id="tipProvider" style="margin-top:8px">${CFG.payProviders.map((x) => `<option>${esc(x)}</option>`).join("")}</select>
      <div class="split"><span>${esc(c.name.split(" ")[0])} gets</span><b id="tipShare"></b></div>
      <div class="actions">
        <button class="btn" data-close>Cancel</button>
        <button class="btn primary" id="sendTip"></button>
      </div>
      <p class="small" style="margin:10px 0 0">Demo mode: no money moves.</p>`, (body) => {
      const update = () => {
        $("#tipShare", body).textContent = money(choice.amount * creatorShare);
        $("#sendTip", body).textContent = choice.id === "tip" ? `Send ${money(choice.amount)}` : `Send ${choice.emoji} ${money(choice.amount)}`;
        body.querySelectorAll(".chip").forEach((x) => x.classList.toggle("sel",
          (x.dataset.gift && x.dataset.gift === choice.id) || (x.dataset.tip && choice.id === "tip" && +x.dataset.tip === choice.amount)));
      };
      body.querySelectorAll("[data-gift]").forEach((b) => b.addEventListener("click", () => { choice = DATA.gifts.find((g) => g.id === b.dataset.gift); update(); }));
      body.querySelectorAll("[data-tip]").forEach((b) => b.addEventListener("click", () => { choice = { id: "tip", emoji: "tip", name: "Tip", amount: +b.dataset.tip }; update(); }));
      $("#sendTip", body).addEventListener("click", () => {
        const phone = $("#tipPhone", body).value.replace(/\D/g, "");
        if (phone.length < 9) { $("#tipPhone", body).focus(); return toast("Enter your mobile money number"); }
        p.tips += 1;
        closeSheet();
        const fly = document.createElement("div");
        fly.className = "gift-fly"; fly.textContent = choice.emoji === "tip" ? "💸" : choice.emoji;
        el.append(fly); setTimeout(() => fly.remove(), 1400);
        toast(`Sent ${money(choice.amount)} to @${c.handle}. Thank you for supporting creators!`);
      });
      update();
    });
  }

  /* ---------- profile ---------- */
  function openProfile(key) {
    if (key === "me") return showView("earn");
    const c = DATA.creators[key];
    const posts = state.posts.filter((p) => p.creator === key);
    const following = state.following.has(key);
    const supporters = posts.reduce((a, p) => a + p.tips, 0);
    openSheet(c.name, `
      <div class="profile-head">
        <span class="avatar" style="--c:${c.color}">${esc(initials(c.name))}</span>
        <div><b>@${esc(c.handle)}</b><div class="muted small">${esc(c.city)}</div></div>
      </div>
      <p>${esc(c.bio)}</p>
      <div class="stats-row">
        <div><b>${short(c.followers + (following ? 1 : 0))}</b><span>followers</span></div>
        <div><b>${short(posts.reduce((a, p) => a + p.likes, 0))}</b><span>likes</span></div>
        <div><b>${short(supporters)}</b><span>tips received</span></div>
      </div>
      <div class="actions" style="grid-template-columns:1fr 1fr;margin-bottom:14px">
        <button class="btn${following ? "" : " primary"}" id="followBtn">${following ? "Following" : "Follow"}</button>
        <button class="btn" id="profileTip">Tip</button>
      </div>
      <div class="grid">${posts.map((p) => `<button class="cell" data-goto="${p.id}"><video src="${esc(p.video)}#t=2" muted playsinline preload="metadata"></video><span>♥ ${short(p.likes)}</span></button>`).join("")}</div>`, (body) => {
      $("#followBtn", body).addEventListener("click", () => {
        if (state.following.has(key)) state.following.delete(key); else { state.following.add(key); toast(`Following @${c.handle}`); }
        feed.querySelectorAll(".post").forEach((el) => { const p = postById(el.dataset.id); if (p.creator === key) rerenderRail(el, p); });
        openProfile(key);
      });
      $("#profileTip", body).addEventListener("click", () => {
        const p = posts[0];
        const el = feed.querySelector(`[data-id="${p.id}"]`);
        closeSheet(); el.scrollIntoView(); openTip(p, el);
      });
      body.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => {
        closeSheet(); feed.querySelector(`[data-id="${b.dataset.goto}"]`)?.scrollIntoView({ behavior: "smooth" });
      }));
    });
  }

  /* ---------- share + report ---------- */
  async function sharePost(p, c) {
    const url = location.href.split("#")[0] + "#post=" + p.id;
    const text = `Watch @${c.handle} on content_feed`;
    try {
      if (navigator.share) await navigator.share({ title: "content_feed", text, url });
      else { await navigator.clipboard.writeText(`${text}: ${url}`); toast("Link copied"); }
    } catch { /* cancelled */ }
  }

  function openReport(p) {
    const reasons = ["Spam or scam", "Nudity or sexual content", "Violence or dangerous acts", "Hate or harassment",
                     "Child safety concern", "False information", "Something else"];
    openSheet("Report this video", `
      <p>Reports are private. Our moderators review every one.</p>
      <div class="reasons">${reasons.map((r) => `<button data-reason="${esc(r)}">${esc(r)}</button>`).join("")}</div>`, (body) => {
      body.querySelectorAll("[data-reason]").forEach((b) => b.addEventListener("click", () => {
        state.hidden.add(p.id);
        if (CFG.apiUrl) fetch(CFG.apiUrl.replace(/\/$/, "") + "/reports", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ postId: p.id, reason: b.dataset.reason, ts: Date.now() }) }).catch(() => {});
        closeSheet(); renderFeed(); toast("Thanks. We've hidden this video while we review it.");
      }));
    });
  }

  /* =====================================================================
   * CREATE
   * ===================================================================== */
  let picked = null;
  $("#maxSec").textContent = CFG.maxVideoSeconds;
  $("#fileInput").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    if (!f.type.startsWith("video/")) return toast("Please choose a video");
    if (f.size > CFG.maxUploadMB * 1024 * 1024) return toast(`Videos must be under ${CFG.maxUploadMB} MB`);
    const url = URL.createObjectURL(f);
    const v = $("#preview");
    v.onloadedmetadata = () => {
      if (v.duration > CFG.maxVideoSeconds + 0.5) {
        URL.revokeObjectURL(url); picked = null; v.hidden = true; $("#pickerEmpty").hidden = false; $("#postBtn").disabled = true;
        return toast(`Videos can be up to ${CFG.maxVideoSeconds} seconds`);
      }
      picked = url; v.hidden = false; $("#pickerEmpty").hidden = true; $("#postBtn").disabled = false; v.play().catch(() => {});
    };
    v.onerror = () => toast("This video format isn't supported on this phone");
    v.src = url;
  });
  $("#postBtn").addEventListener("click", () => {
    if (!picked) return;
    const post = { id: "m" + Date.now(), creator: "me", video: picked, caption: $("#caption").value.trim() || "New video",
                   sound: "Original sound · you", likes: 0, comments: [], tips: 0, liked: false };
    state.posts.unshift(post);
    state.me.posts.unshift(post);
    picked = null; $("#preview").pause(); $("#preview").hidden = true; $("#preview").removeAttribute("src");
    $("#pickerEmpty").hidden = false; $("#caption").value = ""; $("#postBtn").disabled = true; $("#fileInput").value = "";
    renderFeed(); showView("feed"); feed.scrollTop = 0;
    toast("Posted! Fans can now tip you.");
  });

  /* =====================================================================
   * EARNINGS
   * ===================================================================== */
  function renderEarnings() {
    const me = state.me;
    $("#balance").textContent = money(me.balance);
    $("#creatorShare").textContent = Math.round(creatorShare * 100) + "%";
    $("#weekTotal").textContent = money(me.supporters.reduce((a, s) => a + s[1], 0));
    $("#supporterCount").textContent = me.supporters.length;
    $("#supporters").innerHTML = me.supporters.map(([who, amt, kind]) => `
      <div class="row"><span class="avatar" style="--c:#4a4038;color:var(--text)">${esc(who[0].toUpperCase())}</span>
        <span class="main"><b>@${esc(who)}</b><span>${kind === "tip" ? "Sent a tip" : `Sent a gift ${kind}`}</span></span>
        <span class="amt">+${money(amt * creatorShare)}</span></div>`).join("");
    $("#myPosts").innerHTML = me.posts.length ? me.posts.map((p) => `
      <div class="cell"><video src="${esc(p.video)}#t=0.5" muted playsinline preload="metadata"></video><span>♥ ${short(p.likes)}</span></div>`).join("")
      : `<p class="empty">No posts yet. Tap + to post your first video.</p>`;
  }

  $("#payoutBtn").addEventListener("click", () => {
    const me = state.me;
    if (me.balance < CFG.minPayout) return toast(`You can cash out from ${money(CFG.minPayout)}`);
    openSheet("Cash out", `
      <p>Send your earnings to your mobile money wallet.</p>
      <label for="poAmount">Amount</label>
      <input id="poAmount" type="number" inputmode="numeric" min="${CFG.minPayout}" max="${me.balance}" value="${me.balance}">
      <label for="poPhone">Mobile money number</label>
      <input id="poPhone" type="tel" inputmode="tel" placeholder="Your number" autocomplete="tel">
      <label for="poProvider">Wallet</label>
      <select id="poProvider">${CFG.payProviders.map((x) => `<option>${esc(x)}</option>`).join("")}</select>
      <div class="actions"><button class="btn" data-close>Cancel</button><button class="btn primary" id="poGo">Cash out</button></div>
      <p class="small" style="margin:10px 0 0">Demo mode: no money moves.</p>`, (body) => {
      $("#poGo", body).addEventListener("click", () => {
        const amt = Math.floor(+$("#poAmount", body).value);
        const phone = $("#poPhone", body).value.replace(/\D/g, "");
        if (!(amt >= CFG.minPayout && amt <= me.balance)) return toast(`Enter between ${money(CFG.minPayout)} and ${money(me.balance)}`);
        if (phone.length < 9) return toast("Enter your mobile money number");
        me.balance -= amt; closeSheet(); renderEarnings();
        toast(`${money(amt)} is on its way to your ${$("#poProvider", body).value} wallet`);
      });
    });
  });

  /* ---------- start ---------- */
  renderFeed();
  const deep = location.hash.match(/post=(\w+)/);
  if (deep) setTimeout(() => feed.querySelector(`[data-id="${deep[1]}"]`)?.scrollIntoView(), 50);
})();

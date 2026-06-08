/* Story 4.9 — offline POD queue.
 *
 * Interim before Story 7.1 (full PWA + IndexedDB). The goal is to keep
 * Sarah's hand happy when she's on a 3-bar 4G connection at Margaret's
 * gate: if the mark-delivered POST fails (offline, 5xx, 8s timeout)
 * the photo + lat/lng get parked in localStorage, the stop card shows
 * a "queued — will retry" badge, and a `window.online` listener
 * replays the queue in order.
 *
 * Why localStorage and not IndexedDB:
 *   - Single-thread, no schema, no version migrations.
 *   - We cap the queue at 20 items + drop oldest to stay well clear
 *     of the 5 MB origin quota even with full-res iPhone JPEGs.
 *   - Story 7.1 will graduate this to IndexedDB + a real PWA so the
 *     queue survives a hard refresh of the tab.
 */
(function () {
  "use strict";

  var KEY = "merrymeal_pod_queue";
  var MAX_QUEUE = 20;
  var REQUEST_TIMEOUT_MS = 8000;

  function load() {
    try {
      return JSON.parse(localStorage.getItem(KEY) || "[]");
    } catch (_e) {
      return [];
    }
  }

  function save(queue) {
    try {
      localStorage.setItem(KEY, JSON.stringify(queue));
    } catch (_e) {
      // Quota exhausted — drop the oldest half rather than refusing
      // new entries. Worst case we lose the earliest queued photo on
      // a phone that's been offline for hours; better than blocking
      // the volunteer's flow entirely.
      try {
        localStorage.setItem(
          KEY,
          JSON.stringify(queue.slice(Math.floor(queue.length / 2)))
        );
      } catch (_e2) {
        localStorage.removeItem(KEY);
      }
    }
  }

  // ---- Geolocation hidden-input population -------------------------
  // Called once per page load. If the user denies the prompt, leave
  // the inputs blank — the server tolerates null lat/lng.
  function populateGeo() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        var lat = pos.coords.latitude.toFixed(7);
        var lng = pos.coords.longitude.toFixed(7);
        document
          .querySelectorAll("[data-geo='lat']")
          .forEach(function (el) {
            el.value = lat;
          });
        document
          .querySelectorAll("[data-geo='lng']")
          .forEach(function (el) {
            el.value = lng;
          });
      },
      function () {
        // Permission denied or unavailable — silently leave blank.
      },
      { timeout: 4000, maximumAge: 30000 }
    );
  }

  // ---- Queue badge rendering ---------------------------------------
  function badgeFor(card) {
    var badge = card.querySelector("[data-testid='queue-badge']");
    if (!badge) {
      badge = document.createElement("span");
      badge.setAttribute("data-testid", "queue-badge");
      badge.className =
        "inline-block px-2 py-1 text-[14px] rounded text-white";
      card.prepend(badge);
    }
    return badge;
  }

  function markBadge(card, state) {
    if (!card) return;
    var badge = badgeFor(card);
    if (state === "queued") {
      badge.textContent = "queued — will retry";
      badge.classList.remove("bg-brand-green");
      badge.classList.add("bg-brand-orange");
    } else {
      badge.textContent = "✓ synced";
      badge.classList.remove("bg-brand-orange");
      badge.classList.add("bg-brand-green");
    }
  }

  // ---- Enqueue a failed submission ---------------------------------
  function enqueue(form, file) {
    var card = form.closest("[data-testid='stop-card']");
    var reader = new FileReader();
    reader.onload = function () {
      var queue = load();
      if (queue.length >= MAX_QUEUE) {
        console.warn(
          "merrymeal: POD queue full (" +
            MAX_QUEUE +
            "), dropping oldest entry"
        );
        queue.shift();
      }
      queue.push({
        delivery_id: form.dataset.deliveryId,
        url: form.action,
        photo: reader.result,
        lat: form.querySelector("[data-geo='lat']")
          ? form.querySelector("[data-geo='lat']").value
          : "",
        lng: form.querySelector("[data-geo='lng']")
          ? form.querySelector("[data-geo='lng']").value
          : "",
        csrf: (form.querySelector("[name='csrfmiddlewaretoken']") || {})
          .value,
        queued_at: Date.now(),
      });
      save(queue);
      markBadge(card, "queued");
    };
    reader.readAsDataURL(file);
  }

  // ---- Replay the queue --------------------------------------------
  function fetchWithTimeout(url, opts, timeoutMs) {
    return new Promise(function (resolve, reject) {
      var controller =
        typeof AbortController !== "undefined" ? new AbortController() : null;
      if (controller) opts.signal = controller.signal;
      var timer = setTimeout(function () {
        if (controller) controller.abort();
        reject(new Error("timeout"));
      }, timeoutMs);
      fetch(url, opts).then(
        function (r) {
          clearTimeout(timer);
          resolve(r);
        },
        function (e) {
          clearTimeout(timer);
          reject(e);
        }
      );
    });
  }

  function dataUrlToBlob(dataUrl) {
    return fetch(dataUrl).then(function (r) {
      return r.blob();
    });
  }

  function flush() {
    var queue = load();
    if (queue.length === 0) return Promise.resolve();
    var remaining = [];
    return queue
      .reduce(function (chain, item) {
        return chain.then(function () {
          return dataUrlToBlob(item.photo)
            .then(function (blob) {
              var fd = new FormData();
              fd.append("photo", blob, "pod.jpg");
              fd.append("latitude", item.lat || "");
              fd.append("longitude", item.lng || "");
              if (item.csrf) fd.append("csrfmiddlewaretoken", item.csrf);
              return fetchWithTimeout(
                item.url,
                { method: "POST", body: fd, credentials: "same-origin" },
                REQUEST_TIMEOUT_MS
              );
            })
            .then(function (resp) {
              if (!resp.ok) {
                throw new Error("server " + resp.status);
              }
              // Mark the matching card as synced if it's still on screen.
              var card = document.querySelector(
                "[data-testid='stop-card'] form[data-delivery-id='" +
                  item.delivery_id +
                  "']"
              );
              if (card)
                markBadge(
                  card.closest("[data-testid='stop-card']"),
                  "synced"
                );
            })
            .catch(function () {
              remaining.push(item);
            });
        });
      }, Promise.resolve())
      .then(function () {
        save(remaining);
      });
  }

  // ---- Wire-up -----------------------------------------------------
  document.addEventListener("htmx:responseError", function (e) {
    var form = e.detail && e.detail.elt
      ? e.detail.elt.closest("[data-pod-form='1']")
      : null;
    if (!form) return;
    var input = form.querySelector("input[type=file]");
    if (input && input.files && input.files[0]) enqueue(form, input.files[0]);
  });

  document.addEventListener("htmx:sendError", function (e) {
    var form = e.detail && e.detail.elt
      ? e.detail.elt.closest("[data-pod-form='1']")
      : null;
    if (!form) return;
    var input = form.querySelector("input[type=file]");
    if (input && input.files && input.files[0]) enqueue(form, input.files[0]);
  });

  window.addEventListener("online", flush);

  document.addEventListener("DOMContentLoaded", function () {
    populateGeo();
    if (navigator.onLine !== false) flush();
  });
})();

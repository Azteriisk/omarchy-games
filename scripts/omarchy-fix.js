// Omarchy Gamepad Steward & Pointer Lock Capture
// Fixes Linux drawing tablet pad interference (Huion, Wacom, XP-Pen)
// and handles seamless stream focus, ad/splash transitions, and cursor capture.

(function() {
  'use strict';
  console.log("%c[Omarchy-xCloud]", "color:#52b052;font-weight:bold;", "Initializing Gamepad Steward, Focus Steward & Ad Handler...");

  // 0. Pre-seed Better xCloud preferences to skip splash video and auto-hide cursor
  try {
    let globalPrefs = {};
    const raw = localStorage.getItem("BetterXcloud.Global");
    if (raw) {
      try { globalPrefs = JSON.parse(raw); } catch (_) {}
    }
    let modified = false;
    if (globalPrefs["ui.splashVideo.skip"] !== true) {
      globalPrefs["ui.splashVideo.skip"] = true;
      modified = true;
    }
    if (globalPrefs["mkb.cursor.hideIdle"] !== true) {
      globalPrefs["mkb.cursor.hideIdle"] = true;
      modified = true;
    }
    if (modified) {
      localStorage.setItem("BetterXcloud.Global", JSON.stringify(globalPrefs));
      console.log("%c[Omarchy-xCloud]", "color:#52b052;", "Pre-seeded Better xCloud preferences (skip splash video, hide idle cursor).");
    }
  } catch (e) {
    console.warn("[Omarchy-xCloud] Could not pre-seed preferences:", e);
  }

  // 1. Identification helpers
  function isTabletOrNonGamepad(id) {
    if (!id) return false;
    return /tablet|monitor pad|touch strip|dial|stylus|pen|huion|wacom|xp-pen/i.test(id);
  }

  function isRealGamepad(id) {
    if (!id) return false;
    return /xbox|controller|gamepad|dualshock|dualsense|powera|8bitdo|logitech|standard gamepad|xinput/i.test(id);
  }

  // Intercept navigator.getGamepads to guarantee real gaming controllers take Slot 0 (Player 1)
  const nativeGetGamepads = navigator.getGamepads.bind(navigator);

  navigator.getGamepads = function() {
    const raw = nativeGetGamepads();
    if (!raw) return raw;

    const realControllers = [];
    for (let i = 0; i < raw.length; i++) {
      const gp = raw[i];
      if (!gp || !gp.connected) continue;
      // Completely strip out tablet monitors, pads, dials, and touch strips
      if (isTabletOrNonGamepad(gp.id)) continue;
      realControllers.push(gp);
    }

    // If no dedicated gaming controllers are detected, fallback to raw devices
    if (realControllers.length === 0) {
      return raw;
    }

    const result = new Array(4).fill(null);
    for (let i = 0; i < realControllers.length; i++) {
      const original = realControllers[i];
      const targetIndex = i;
      try {
        result[i] = new Proxy(original, {
          get(target, prop) {
            if (prop === 'index') return targetIndex;
            const val = target[prop];
            return typeof val === 'function' ? val.bind(target) : val;
          }
        });
      } catch (e) {
        result[i] = original;
      }
    }

    return result;
  };

  // Periodically ensure Xbox's header component receives a gamepadconnected event
  let lastAnnouncedConnected = false;
  function ensureGamepadEventDispatched() {
    const pads = navigator.getGamepads();
    if (pads && pads[0] && pads[0].connected) {
      if (!lastAnnouncedConnected) {
        lastAnnouncedConnected = true;
        try {
          window.dispatchEvent(new GamepadEvent("gamepadconnected", { gamepad: pads[0] }));
        } catch (_) {}
      }
    } else {
      lastAnnouncedConnected = false;
    }
  }
  setInterval(ensureGamepadEventDispatched, 1000);

  // 2. Stream Target & Focus Steward
  function getStreamTarget() {
    return document.querySelector(
      "div[data-testid=media-container] canvas, " +
      "div[data-testid=media-container] video, " +
      "#game-stream canvas, " +
      "#game-stream video, " +
      ".game-stream-container canvas, " +
      ".game-stream-container video, " +
      "video[src*='blob']"
    );
  }

  function isMenuOrDialogOpen() {
    // Check if Guide menu, dialog, or settings modal is visible
    return !!(
      document.querySelector("[data-testid=guide-menu], [role=dialog]:not([aria-hidden=true]), .bx-dialog, .bx-menu-open") ||
      document.body.classList.contains("bx-menu-open") ||
      document.body.classList.contains("bx-dialog-open")
    );
  }

  function ensureStreamFocus(forcePointerLock = false) {
    if (isMenuOrDialogOpen()) {
      return null;
    }

    const target = getStreamTarget();
    if (target) {
      if (target.getAttribute("tabindex") !== "0") {
        target.setAttribute("tabindex", "0");
      }
      if (document.activeElement !== target) {
        target.focus();
      }

      if (forcePointerLock && !document.pointerLockElement) {
        try {
          const lockEl = target.closest("canvas, video") || target;
          if (lockEl.requestPointerLock) {
            lockEl.requestPointerLock();
          }
        } catch (_) {}
      }
      return target;
    }
    return null;
  }

  // 3. Cursor Visibility Management
  let isStreamActive = false;
  let idleTimer = null;

  function hideCursor() {
    if (isStreamActive && !isMenuOrDialogOpen()) {
      document.documentElement.style.cursor = "none";
      const target = getStreamTarget();
      if (target) target.style.cursor = "none";
    }
  }

  function showCursor() {
    document.documentElement.style.cursor = "auto";
    const target = getStreamTarget();
    if (target) target.style.cursor = "auto";
    clearTimeout(idleTimer);
    if (isStreamActive) {
      idleTimer = setTimeout(hideCursor, 2000);
    }
  }

  window.addEventListener("mousemove", showCursor, { passive: true });
  window.addEventListener("mousedown", showCursor, { passive: true });

  // 4. Ad / Splash Video Transition Observer
  // When an ad, splash video, or interstitial finishes, instantly refocus the stream!
  document.addEventListener("ended", function(e) {
    if (e.target && e.target.tagName === "VIDEO") {
      console.log("%c[Omarchy-xCloud]", "color:#52b052;", "Video ended (ad/splash). Re-arming stream focus...");
      setTimeout(() => {
        isStreamActive = true;
        ensureStreamFocus(false);
        showStreamReadyPrompt();
      }, 300);
    }
  }, true);

  // Monitor DOM for stream appearance or ad removal
  let lastTargetFound = false;
  const observer = new MutationObserver(() => {
    const target = getStreamTarget();
    if (target && !lastTargetFound) {
      lastTargetFound = true;
      isStreamActive = true;
      console.log("%c[Omarchy-xCloud]", "color:#52b052;", "Stream element mounted. Attaching focus listeners...");
      ensureStreamFocus(false);
      showStreamReadyPrompt();
    } else if (!target) {
      lastTargetFound = false;
    }
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  // 5. Sleek "Stream Ready" HUD prompt to capture user gesture
  let promptElement = null;
  function showStreamReadyPrompt() {
    if (promptElement || document.pointerLockElement) return;

    promptElement = document.createElement("div");
    promptElement.id = "omarchy-stream-ready-hud";
    promptElement.style.cssText = `
      position: fixed;
      top: 24px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(16, 124, 16, 0.92);
      color: #ffffff;
      padding: 10px 22px;
      border-radius: 24px;
      font-family: 'Segoe UI', system-ui, sans-serif;
      font-size: 14px;
      font-weight: 600;
      letter-spacing: 0.5px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.6);
      z-index: 999999;
      pointer-events: none;
      transition: opacity 0.3s ease, transform 0.3s ease;
      display: flex;
      align-items: center;
      gap: 10px;
    `;
    promptElement.innerHTML = `
      <span style="font-size: 18px;">🎮</span>
      <span>Game Stream Active — Click screen or press any controller button</span>
    `;
    document.body.appendChild(promptElement);

    setTimeout(dismissStreamReadyPrompt, 6000);
  }

  function dismissStreamReadyPrompt() {
    if (promptElement) {
      promptElement.style.opacity = "0";
      promptElement.style.transform = "translateX(-50%) translateY(-10px)";
      setTimeout(() => {
        if (promptElement && promptElement.parentNode) {
          promptElement.parentNode.removeChild(promptElement);
        }
        promptElement = null;
      }, 300);
    }
  }

  // 6. User Click / Tap to Capture
  document.addEventListener("click", function(e) {
    dismissStreamReadyPrompt();
    const target = e.target;
    // Ignore clicks inside menus or dialogs
    if (target.closest("[role=dialog], [data-testid=guide-menu], .bx-dialog, .bx-menu-open")) {
      return;
    }

    isStreamActive = true;
    ensureStreamFocus(true);
    hideCursor();
  }, true);

  // 7. Controller Button Poller: Automatically refocus stream and hide cursor when controller is touched
  function pollGamepadActivity() {
    const pads = navigator.getGamepads();
    if (pads && pads[0]) {
      const p = pads[0];
      let active = false;
      if (p.buttons) {
        for (let i = 0; i < p.buttons.length; i++) {
          if (p.buttons[i].pressed) { active = true; break; }
        }
      }
      if (!active && p.axes) {
        for (let i = 0; i < p.axes.length; i++) {
          if (Math.abs(p.axes[i]) > 0.15) { active = true; break; }
        }
      }

      if (active) {
        dismissStreamReadyPrompt();
        if (isStreamActive && !isMenuOrDialogOpen()) {
          // If controller touched, ensure stream is focused
          const target = getStreamTarget();
          if (target && document.activeElement !== target) {
            target.focus();
          }
          hideCursor();
        }
      }
    }
    requestAnimationFrame(pollGamepadActivity);
  }
  requestAnimationFrame(pollGamepadActivity);

  window.addEventListener("pointerlockchange", function() {
    if (document.pointerLockElement) {
      isStreamActive = true;
      dismissStreamReadyPrompt();
      hideCursor();
    } else {
      showCursor();
    }
  });

  console.log("%c[Omarchy-xCloud]", "color:#52b052;font-weight:bold;", "Gamepad Steward & Focus Enforcer active.");
})();

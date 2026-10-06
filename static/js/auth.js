// Clerk is the identity provider; Flask (services/auth.py) decides where a session goes.
// Flow: sign in with Clerk -> navigate to /auth -> the server validates the session and redirects
// (dashboard, /contexto/) or renders the "no access" state. Never wait for a manual step.
window.addEventListener('load', async () => {
  const AUTH_PATH = '/auth';
  const GUARD_KEY = 'amon-auth-verify';
  const GUARD_WINDOW_MS = 30000;

  const panel = document.querySelector('[data-auth-panel]');
  const menu = document.querySelector('[data-account-menu]');
  const signInButtons = document.querySelectorAll('[data-auth-sign-in]');
  const signOutButtons = document.querySelectorAll('[data-auth-sign-out]');
  const accountButtons = document.querySelectorAll('[data-auth-account]');
  const retryButtons = document.querySelectorAll('[data-auth-retry]');
  if (!panel && !menu && !signInButtons.length && !signOutButtons.length && !accountButtons.length) return;

  const statuses = document.querySelectorAll('[data-auth-status]');
  const setStatus = (text) => statuses.forEach((node) => { node.textContent = text; });
  const showView = (name) => {
    if (!panel) return;
    panel.querySelectorAll('[data-auth-view]').forEach((view) => { view.hidden = view.dataset.authView !== name; });
  };

  // Loop guard: one automatic re-check per window; afterwards show a clear error state instead of reloading.
  const guard = {
    recent() {
      try { return Date.now() - Number(sessionStorage.getItem(GUARD_KEY) || 0) < GUARD_WINDOW_MS; } catch { return false; }
    },
    mark() { try { sessionStorage.setItem(GUARD_KEY, String(Date.now())); } catch { /* guard is best effort */ } },
    clear() { try { sessionStorage.removeItem(GUARD_KEY); } catch { /* nothing to clear */ } },
  };

  if (menu) {
    document.addEventListener('click', (event) => {
      const details = menu.querySelector('details');
      if (details?.open && !menu.contains(event.target)) details.open = false;
    });
    document.addEventListener('keydown', (event) => {
      const details = menu.querySelector('details');
      if (event.key === 'Escape' && details?.open) { details.open = false; details.querySelector('summary')?.focus(); }
    });
  }

  retryButtons.forEach((button) => button.addEventListener('click', () => { guard.clear(); window.location.assign(AUTH_PATH); }));

  try {
    await window.Clerk.load({
      ui: { ClerkUI: window.__internal_ClerkUICtor },
      signInForceRedirectUrl: AUTH_PATH,
      signUpForceRedirectUrl: AUTH_PATH,
    });
    const clerk = window.Clerk;

    // Make sure the __session cookie carries a fresh token before the server is asked to validate it.
    const goToAuth = async () => {
      try { await clerk.session?.getToken({ skipCache: true }); } catch { /* the server decides */ }
      window.location.assign(AUTH_PATH);
    };

    signInButtons.forEach((button) => {
      button.disabled = false;
      button.addEventListener('click', () => clerk.openSignIn({ forceRedirectUrl: AUTH_PATH, signUpForceRedirectUrl: AUTH_PATH }));
    });

    if (panel?.dataset.authState === 'anonymous') {
      if (clerk.isSignedIn) {
        // Clerk knows the user but this server response did not: verify once, never loop.
        if (guard.recent()) {
          showView('verify-failed');
        } else {
          guard.mark();
          showView('verifying');
          await goToAuth();
          return;
        }
      } else {
        guard.clear();
        showView('signed-out');
      }
    }

    if (menu && clerk.user) {
      const name = clerk.user.fullName || clerk.user.username || 'Mi cuenta';
      const email = clerk.user.primaryEmailAddress?.emailAddress || '';
      menu.querySelectorAll('[data-account-name], [data-account-name-full]').forEach((node) => { node.textContent = name; });
      menu.querySelector('[data-account-email]').textContent = email;
      if (clerk.user.hasImage && clerk.user.imageUrl) {
        const avatar = menu.querySelector('[data-account-avatar]');
        const image = document.createElement('img');
        image.src = clerk.user.imageUrl;
        image.alt = '';
        image.referrerPolicy = 'no-referrer';
        avatar.replaceChildren(image);
      }
    }
    accountButtons.forEach((button) => button.addEventListener('click', () => clerk.openUserProfile()));
    signOutButtons.forEach((button) => button.addEventListener('click', async () => {
      button.disabled = true;
      guard.clear();
      try {
        await clerk.signOut({ redirectUrl: AUTH_PATH });
      } catch {
        button.disabled = false;
        setStatus('No se pudo cerrar la sesión. Intenta nuevamente.');
      }
    }));

    // Keep every page in sync with account changes. On /auth a completed sign-in continues automatically.
    const initialUser = clerk.user?.id || null;
    let navigating = false;
    clerk.addListener(({ user: currentUser }) => {
      const currentId = currentUser?.id || null;
      if (currentId === initialUser || navigating) return;
      navigating = true;
      if (currentId && panel) {
        showView('verifying');
        goToAuth();
      } else {
        window.location.assign(AUTH_PATH);
      }
    });
  } catch {
    showView('signed-out');
    setStatus('No se pudo cargar el acceso seguro. Recarga la página para volver a intentar.');
  }
});

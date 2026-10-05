window.addEventListener('load', async () => {
  const controls = document.querySelector('[data-auth-controls]');
  const menu = document.querySelector('[data-account-menu]');
  const signOutButtons = document.querySelectorAll('[data-auth-sign-out]');
  const accountButtons = document.querySelectorAll('[data-auth-account]');
  if (!controls && !menu && !signOutButtons.length) return;
  const statuses = document.querySelectorAll('[data-auth-status]');
  const setStatus = (text) => statuses.forEach((node) => { node.textContent = text; });
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
  try {
    await window.Clerk.load({
      ui: { ClerkUI: window.__internal_ClerkUICtor },
      signInForceRedirectUrl: '/auth',
    });
    const clerk = window.Clerk;
    if (controls) {
      const user = controls.querySelector('[data-auth-user]');
      controls.querySelector('[data-auth-signed-out]').hidden = clerk.isSignedIn;
      user.hidden = !clerk.isSignedIn;
      if (clerk.isSignedIn) {
        clerk.mountUserButton(user);
        setStatus('Sesión iniciada');
      } else {
        setStatus('');
      }
      const signIn = controls.querySelector('[data-auth-sign-in]');
      signIn.disabled = false;
      signIn.addEventListener('click', () => clerk.openSignIn());
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
      try {
        await clerk.signOut({ redirectUrl: '/auth' });
      } catch {
        button.disabled = false;
        setStatus('No se pudo cerrar la sesión. Intenta nuevamente.');
      }
    }));
    const initialUser = clerk.user?.id || null;
    clerk.addListener(({ user: currentUser }) => {
      if ((currentUser?.id || null) !== initialUser) window.location.assign('/auth');
    });
  } catch {
    setStatus('No se pudo cargar el acceso seguro. Recarga la página para volver a intentar.');
  }
});

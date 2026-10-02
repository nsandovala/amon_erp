window.addEventListener('load', async () => {
  const controls = document.querySelector('[data-auth-controls]');
  if (!controls) return;
  const status = controls.querySelector('[data-auth-status]');
  try {
    await window.Clerk.load({
      ui: { ClerkUI: window.__internal_ClerkUICtor },
      signInForceRedirectUrl: '/auth',
    });
    const clerk = window.Clerk;
    const user = controls.querySelector('[data-auth-user]');
    controls.querySelector('[data-auth-signed-out]').hidden = clerk.isSignedIn;
    user.hidden = !clerk.isSignedIn;
    if (clerk.isSignedIn) {
      clerk.mountUserButton(user);
      status.textContent = 'Sesión iniciada';
    } else {
      status.textContent = '';
    }
    const signIn = controls.querySelector('[data-auth-sign-in]');
    signIn.disabled = false;
    signIn.addEventListener('click', () => clerk.openSignIn());
    const initialUser = clerk.user?.id || null;
    clerk.addListener(({ user: currentUser }) => {
      if ((currentUser?.id || null) !== initialUser) window.location.assign('/auth');
    });
  } catch {
    status.textContent = 'No se pudo cargar el acceso seguro. Recarga la página para volver a intentar.';
  }
});

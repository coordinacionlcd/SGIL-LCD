document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Verificar sesión con el backend
        const response = await fetch('/api/session');
        if (!response.ok) {
            if (window.location.pathname !== '/login') window.location.href = '/login';
            return;
        }

        const data = await response.json();
        const profile = data.profile;

        // Actualizar datos en sidebar y header
        const sidebarName = document.getElementById('user-fullname');
        const sidebarRole = document.getElementById('user-role-badge');
        const headerName = document.getElementById('header-user-fullname');

        if (sidebarName) sidebarName.textContent = profile.full_name;
        if (sidebarRole) sidebarRole.textContent = profile.role;
        if (headerName) headerName.textContent = profile.full_name;

        // Disparar evento para que otros scripts (dashboard.js) sepan que ya cargó
        const event = new CustomEvent('sessionReady', { detail: { profile: profile } });
        document.dispatchEvent(event);

    } catch (error) {
        console.error("Error sesión:", error);
    }
});
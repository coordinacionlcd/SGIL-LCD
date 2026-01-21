document.addEventListener('sessionReady', async (event) => {
    const { profile } = event.detail;
    
    if (!profile) return;

    const loader = document.getElementById('dashboard-loader');
    const content = document.getElementById('dashboard-content');
    
    updateDashboardVisibility(profile.role);
    
    // Ocultar loader y mostrar contenido
    if (loader) loader.style.display = 'none';
    if (content) content.style.display = 'block';
});

function updateDashboardVisibility(role) {
    // Definimos qué módulos ve cada rol
    // IMPORTANTE: Los nombres deben coincidir con los IDs del HTML (module-X)
    const permissions = {
        operario: ['despacho', 'perfil'],
        tecnico: ['despacho', 'calibracion', 'perfil'],
        administracion: ['despacho', 'gestion_usuarios', 'calibracion', 'clientes', 'perfil'],
        coordinacion: ['despacho', 'gestion_usuarios', 'calibracion', 'perfil']
    };

    const allowedModules = permissions[role] || ['perfil'];
    
    document.querySelectorAll('.module-card').forEach(card => {
        const cardId = card.id.replace('module-', '');
        if (allowedModules.includes(cardId)) {
            card.style.display = 'flex'; // Mostrar (flex para centrar contenido)
        } else {
            card.style.display = 'none'; // Ocultar
        }
    });
}
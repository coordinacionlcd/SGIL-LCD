document.addEventListener('DOMContentLoaded', async () => {
    // 1. Cargar datos iniciales
    try {
        const response = await fetch('/api/profile');
        if (response.ok) {
            const profile = await response.json();
            // Llenar campos si existen en el HTML
            const nameInput = document.getElementById('full_name');
            const emailInput = document.getElementById('email');
            const roleInput = document.getElementById('role');

            if(nameInput) nameInput.value = profile.full_name || '';
            if(emailInput) emailInput.value = profile.email || '';
            if(roleInput) roleInput.value = profile.role || '';
        }
    } catch (error) {
        console.error('Error cargando perfil:', error);
    }

    // 2. Manejar actualización de NOMBRE
    const nameForm = document.getElementById('profile-update-form');
    if (nameForm) {
        nameForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = nameForm.querySelector('button[type="submit"]');
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Guardando...';
            btn.disabled = true;

            try {
                const fullName = document.getElementById('full_name').value;
                const response = await fetch('/api/profile/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ full_name: fullName })
                });

                const result = await response.json();
                
                if (response.ok) {
                    Swal.fire('¡Actualizado!', 'Tu nombre ha sido modificado.', 'success');
                    // Actualizar nombre en la barra superior en tiempo real
                    const headerName = document.getElementById('header-user-fullname');
                    if(headerName) headerName.textContent = fullName;
                } else {
                    throw new Error(result.error || 'Error desconocido');
                }
            } catch (err) {
                Swal.fire('Error', err.message, 'error');
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });
    }

    // 3. Manejar cambio de CONTRASEÑA
    const passForm = document.getElementById('password-change-form');
    if (passForm) {
        passForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = passForm.querySelector('button[type="submit"]');
            const originalText = btn.innerHTML;
            
            // Validar coincidencia
            const newPass = document.getElementById('new_password').value;
            const confirmPass = document.getElementById('confirm_password').value;

            if (newPass !== confirmPass) {
                Swal.fire('Error', 'Las nuevas contraseñas no coinciden.', 'warning');
                return;
            }
            
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Actualizando...';
            btn.disabled = true;

            try {
                const response = await fetch('/api/profile/change-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ new_password: newPass })
                });

                const result = await response.json();

                if (response.ok) {
                    Swal.fire('¡Éxito!', 'Tu contraseña ha sido actualizada.', 'success');
                    passForm.reset();
                } else {
                    throw new Error(result.error || 'No se pudo actualizar la contraseña.');
                }
            } catch (err) {
                Swal.fire('Error', err.message, 'error');
            } finally {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        });
    }
});
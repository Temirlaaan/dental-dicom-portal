export default function LoginPage() {
  const handleLogin = () => {
    // TODO: Redirect to Keycloak OIDC login
    window.location.href = '/api/auth/login';
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <div style={{ textAlign: 'center' }}>
        <h1>Dental DICOM Portal</h1>
        <p>Session management for DTX Studio</p>
        <button onClick={handleLogin}>Sign in with Keycloak</button>
      </div>
    </div>
  );
}

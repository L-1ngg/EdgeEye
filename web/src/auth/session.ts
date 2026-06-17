const SESSION_KEY = "edgeeye.demoAdminSession";

export const DEMO_ADMIN_USERNAME = "admin";
export const DEMO_ADMIN_PASSWORD = "edgeeye-admin";

export function hasDemoAdminSession(): boolean {
  return window.localStorage.getItem(SESSION_KEY) === "active";
}

export function authenticateDemoAdmin(username: string, password: string): boolean {
  const isValid = username.trim() === DEMO_ADMIN_USERNAME && password === DEMO_ADMIN_PASSWORD;

  if (isValid) {
    window.localStorage.setItem(SESSION_KEY, "active");
  }

  return isValid;
}

export function clearDemoAdminSession() {
  window.localStorage.removeItem(SESSION_KEY);
}

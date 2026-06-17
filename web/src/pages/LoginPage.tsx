import { FormEvent, useState } from "react";

import { DEMO_ADMIN_PASSWORD, DEMO_ADMIN_USERNAME, authenticateDemoAdmin } from "../auth/session";
import { Icon } from "../components/Icon";

interface LoginPageProps {
  onAuthenticated: () => void;
}

export function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [username, setUsername] = useState(DEMO_ADMIN_USERNAME);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!authenticateDemoAdmin(username, password)) {
      setError("管理员账号或密码不正确。");
      return;
    }

    setError(null);
    onAuthenticated();
  }

  return (
    <main className="login-shell">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-brand">
          <span className="login-logo" aria-hidden="true">
            <Icon name="shield" size={22} />
          </span>
          <span>EdgeEye</span>
          <strong id="login-title">管理员登录</strong>
          <p>进入电力设备智能巡检工作台。</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            <span>管理员账号</span>
            <input
              autoComplete="username"
              onChange={(event) => setUsername(event.target.value)}
              type="text"
              value={username}
            />
          </label>
          <label>
            <span>密码</span>
            <input
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              placeholder={DEMO_ADMIN_PASSWORD}
              type="password"
              value={password}
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button className="primary-button" type="submit">
            登录
          </button>
        </form>

        <p className="login-note">演示账号：{DEMO_ADMIN_USERNAME} / {DEMO_ADMIN_PASSWORD}</p>
      </section>
    </main>
  );
}

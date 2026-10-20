import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "../api/client";
import { useAuth } from "../store/auth";

const schema = z.object({
  name: z.string().min(2),
  email: z.string().email(),
  password: z.string().min(8),
  organization_name: z.string().min(2),
});

type FormValues = z.infer<typeof schema>;

export function RegisterPage() {
  const navigate = useNavigate();
  const setSession = useAuth((state) => state.setSession);
  const [error, setError] = useState("");
  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setError("");
    try {
      await api.post("/auth/register/", values);
      const token = await api.post("/auth/token/", { email: values.email, password: values.password });
      setSession(token.data.access, values.name, values.organization_name);
      navigate("/app");
    } catch {
      setError("Could not open the books. Check the email and try again.");
    }
  }

  return (
    <form className="card auth" onSubmit={form.handleSubmit(onSubmit)}>
      <p className="tag">New books</p>
      <h2>Open a Cinderwell ledger</h2>
      <div className="grid">
        <input placeholder="Your name" {...form.register("name")} />
        <input placeholder="Email" {...form.register("email")} />
        <input placeholder="Password" type="password" {...form.register("password")} />
        <input placeholder="Company name" {...form.register("organization_name")} />
        {error && <p className="error">{error}</p>}
        <button className="btn" type="submit">Create books</button>
        <Link to="/">I already have books</Link>
      </div>
    </form>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuth((state) => state.setSession);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError("");
    try {
      const token = await api.post("/auth/token/", {
        email: data.get("email"),
        password: data.get("password"),
      });
      const me = await api.get("/auth/me/", { headers: { Authorization: `Bearer ${token.data.access}` } });
      setSession(token.data.access, me.data.name, me.data.organization_name);
      navigate("/app");
    } catch {
      setError("Those details did not match an account.");
    }
  }

  return (
    <form className="card auth" onSubmit={onSubmit}>
      <p className="tag">Cinderwell</p>
      <h2>Sign in to your books</h2>
      <div className="grid">
        <input name="email" placeholder="Email" />
        <input name="password" type="password" placeholder="Password" />
        {error && <p className="error">{error}</p>}
        <button className="btn" type="submit">Sign in</button>
        <Link to="/register">Open a new ledger</Link>
      </div>
    </form>
  );
}
